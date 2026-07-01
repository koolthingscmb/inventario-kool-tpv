"""Servicio para la configuración del taller (Backoffice).

Coordina la gestión de Colores, Tallas y sus relaciones.
"""
from typing import List, Set, Optional
from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.produccion.models.produccion_color_model import ProduccionColor
from kool_tpv.modulos.produccion.models.produccion_talla_model import ProduccionTalla
from kool_tpv.modulos.produccion.repositories.produccion_colores_repository import ProduccionColoresRepository
from kool_tpv.modulos.produccion.repositories.produccion_tallas_repository import ProduccionTallasRepository
from kool_tpv.modulos.produccion.repositories.produccion_relaciones_repository import ProduccionRelacionesRepository
from kool_tpv.modulos.produccion.repositories.produccion_tipos_repository import ProduccionTiposRepository
from kool_tpv.modulos.produccion.repositories.produccion_menu_repository import ProduccionMenuRepository
from kool_tpv.modulos.produccion.repositories.produccion_menu_tipos_repository import ProduccionMenuTiposRepository
from kool_tpv.modulos.produccion.repositories.produccion_colecciones_repository import ProduccionColeccionesRepository, ProduccionColeccion
from kool_tpv.modulos.produccion.repositories.produccion_sufijos_repository import ProduccionSufijosRepository, ProduccionSufijo
from kool_tpv.modulos.produccion.models.produccion_menu_model import ProduccionMenuItem
from kool_tpv.modulos.produccion.models.produccion_tipo_variante_model import ProduccionTipoVariante
from kool_tpv.modulos.produccion.models.produccion_tipos_model import ProduccionTipo
from kool_tpv.modulos.produccion.services.produccion_stock_base_service import ProduccionStockBaseService

class ProduccionConfigService:
    def __init__(self, db: Database):
        self.db = db
        self.colores_repo = ProduccionColoresRepository(db)
        self.tallas_repo = ProduccionTallasRepository(db)
        self.relaciones_repo = ProduccionRelacionesRepository(db)
        self.tipos_repo = ProduccionTiposRepository(db)
        self.menu_repo = ProduccionMenuRepository(db)
        self.menu_tipos_repo = ProduccionMenuTiposRepository(db)
        self.colecciones_repo = ProduccionColeccionesRepository(db)
        self.sufijos_repo = ProduccionSufijosRepository(db)
        self._stock_service = ProduccionStockBaseService(db)

    # --- Gestión de Colores ---
    def obtener_todos_colores(self) -> List[ProduccionColor]:
        return self.colores_repo.get_todos()

    def guardar_color(self, nombre: str, hex_code: str, color_id: Optional[int] = None) -> bool:
        color = ProduccionColor(id=color_id, nombre=nombre, codigo_hex=hex_code)
        if color_id:
            return self.colores_repo.actualizar(color)
        return self.colores_repo.crear(color)

    def eliminar_color(self, color_id: int) -> bool:
        return self.colores_repo.eliminar(color_id)

    # --- Gestión de Tallas ---
    def obtener_todas_tallas(self) -> List[ProduccionTalla]:
        return self.tallas_repo.get_todas()

    def guardar_talla(self, nombre: str, orden: int, activo: int = 1, talla_id: Optional[int] = None) -> bool:
        talla = ProduccionTalla(id=talla_id, nombre=nombre, orden=orden, activo=activo)
        if talla_id:
            return self.tallas_repo.actualizar(talla)
        return self.tallas_repo.crear(talla) is not None

    def mover_talla(self, talla_id: int, direccion: int) -> bool:
        """Intercambiar el orden de una talla con su vecina.
        
        Args:
            talla_id: ID de la talla a mover.
            direccion: -1 para subir, +1 para bajar.
        """
        tallas = self.tallas_repo.get_todas()
        idx = None
        for i, t in enumerate(tallas):
            if t.id == talla_id:
                idx = i
                break
        if idx is None:
            return False
        nuevo_idx = idx + direccion
        if nuevo_idx < 0 or nuevo_idx >= len(tallas):
            return False
        t_actual = tallas[idx]
        t_vecina = tallas[nuevo_idx]
        self.tallas_repo.actualizar_orden(t_actual.id, t_vecina.orden)
        self.tallas_repo.actualizar_orden(t_vecina.id, t_actual.orden)
        return True

    def obtener_por_id(self, tipo_id: int) -> Optional[ProduccionTipo]:
        """Obtener un tipo por su ID."""
        return self.tipos_repo.get_por_id(tipo_id)

    def obtener_variantes_por_tipo(self, tipo_id: int, solo_matriz: bool = False) -> List[ProduccionTipoVariante]:
        """Obtener variantes de un tipo. 
        Si solo_matriz es True, solo devuelve las que requieren color o talla.
        """
        vars = self.relaciones_repo.db.fetch_all(
            "SELECT id, tipo_id, nombre, coste_base, precio_recomendado, activo, shopify_variant_id, created_at, updated_at, requiere_talla, requiere_color FROM tipos_variantes WHERE tipo_id = ? AND activo = 1",
            (tipo_id,)
        )
        from datetime import datetime
        results = []
        for r in vars:
            v = ProduccionTipoVariante(
                id=r[0], tipo_id=r[1], nombre=r[2], coste_base=r[3], precio_recomendado=r[4],
                activo=r[5], shopify_variant_id=r[6], 
                created_at=datetime.fromisoformat(r[7]) if r[7] else None,
                updated_at=datetime.fromisoformat(r[8]) if r[8] else None,
                requiere_talla=r[9] or 0, requiere_color=r[10] or 0
            )
            if solo_matriz:
                if v.requiere_color == 1 or v.requiere_talla == 1:
                    results.append(v)
            else:
                results.append(v)
        return results

    # --- Matriz 3D para TIPOS y VARIANTES ---

    def obtener_tipos_para_matriz(self) -> List[ProduccionTipo]:
        """Obtener tipos que requieren color o talla o tienen variantes que lo requieren."""
        todos = self.tipos_repo.get_activos()
        # Un tipo aparece si él requiere algo O si alguna de sus variantes activas requiere algo
        results = []
        for t in todos:
            if t.requiere_color == 1 or t.requiere_talla == 1:
                results.append(t)
                continue
            
            # Comprobar variantes
            vars = self.obtener_variantes_por_tipo(t.id, solo_matriz=True)
            if vars:
                results.append(t)
        return results

    def obtener_colores_tipo_3d(self, tipo_id: int, variante_id: Optional[int] = None) -> Set[int]:
        """IDs de colores asignados a un tipo o variante (stock base)."""
        return self.relaciones_repo.get_colores_id_por_tipo_3d(tipo_id, variante_id)

    def obtener_tallas_tipo_color_3d(self, tipo_id: int, color_id: int, variante_id: Optional[int] = None) -> Set[int]:
        """IDs de tallas disponibles para una combinación tipo+color o variante+color."""
        return self.relaciones_repo.get_tallas_id_por_tipo_color_3d(tipo_id, color_id, variante_id)

    def guardar_tallas_tipo_color_3d(self, tipo_id: int, color_id: int, tallas_ids: List[int], variante_id: Optional[int] = None):
        """Sincronizar tallas para una combinación tipo+color o variante+color."""
        self.relaciones_repo.actualizar_tallas_tipo_color_3d(tipo_id, color_id, tallas_ids, variante_id)
        return True

    def eliminar_color_tipo_3d(self, tipo_id: int, color_id: int, variante_id: Optional[int] = None):
        """Eliminar un color y todas sus tallas de un tipo o variante en el stock base."""
        self.relaciones_repo.remove_color_de_tipo_3d(tipo_id, color_id, variante_id)
        return True

    # --- Gestión del Menú ---

    def obtener_todos_menu(self):
        """Obtener todos los elementos del menú."""
        return self.menu_repo.get_todos()

    def obtener_tipos_de_menus_ordenados(self, solo_con_stock: bool = True) -> List[ProduccionTipo]:
        """Obtener tipos asociados a cualquier menú, ordenados por menú y tipo."""
        return self.menu_tipos_repo.get_tipos_todos_menus_ordenados(solo_con_stock=solo_con_stock)

    def obtener_coste_medio_variante(self, tipo_id: int, variante_id: Optional[int] = None) -> float:
        """Obtener coste medio ponderado de una variante desde el stock."""
        return self._stock_service.obtener_coste_medio_variante(tipo_id, variante_id)

    def mover_menu(self, menu_id: int, direccion: int) -> bool:
        """Intercambiar el orden de un menú con su vecino.
        
        Args:
            menu_id: ID del menú a mover.
            direccion: -1 para subir, +1 para bajar.
        """
        menus = self.menu_repo.get_todos()
        idx = None
        for i, m in enumerate(menus):
            if m.id == menu_id:
                idx = i
                break
        if idx is None:
            return False
        nuevo_idx = idx + direccion
        if nuevo_idx < 0 or nuevo_idx >= len(menus):
            return False
        m_actual = menus[idx]
        m_vecino = menus[nuevo_idx]
        self.menu_repo.actualizar_orden(m_actual.id, m_vecino.orden)
        self.menu_repo.actualizar_orden(m_vecino.id, m_actual.orden)
        return True

    def guardar_menu(self, nombre: str, sistema_produccion: str, orden: int,
                     activo: int, tipo_id: int, menu_id: Optional[int] = None) -> bool:
        """Crear o actualizar un elemento del menú."""
        item = ProduccionMenuItem(
            id=menu_id or 0,
            nombre=nombre,
            sistema_produccion=sistema_produccion or None,
            orden=orden,
            activo=activo,
            tipo_id=tipo_id or None
        )
        if menu_id:
            return self.menu_repo.actualizar(item)
        return self.menu_repo.crear(item) is not None

    def eliminar_menu(self, menu_id: int) -> bool:
        """Eliminar un elemento del menú y sus relaciones de tipos."""
        self.menu_tipos_repo.eliminar_tipos_menu(menu_id)
        return self.menu_repo.eliminar(menu_id)

    # --- Relación Menú <-> Tipos (N:M) ---

    def obtener_tipos_por_menu(self, menu_id: int):
        """Obtener los tipos asignados a un menú."""
        return self.menu_tipos_repo.get_tipos_por_menu(menu_id)

    def obtener_tipos_id_por_menu(self, menu_id: int) -> set:
        """Obtener solo los IDs de tipos asignados a un menú."""
        return self.menu_tipos_repo.get_tipos_id_por_menu(menu_id)

    def actualizar_tipos_menu(self, menu_id: int, tipos_ids: List[int]):
        """Sincronizar los tipos asignados a un menú."""
        self.menu_tipos_repo.actualizar_tipos_menu(menu_id, tipos_ids)
        return True

    # --- Gestión de Colecciones ---

    def obtener_colecciones(self) -> List[ProduccionColeccion]:
        return self.colecciones_repo.get_activas()

    def guardar_coleccion(self, nombre: str, coleccion_id: Optional[int] = None) -> bool:
        if coleccion_id:
            return self.colecciones_repo.actualizar(coleccion_id, nombre, 1)
        return self.colecciones_repo.crear(nombre) is not None

    def eliminar_coleccion(self, coleccion_id: int) -> bool:
        return self.colecciones_repo.eliminar(coleccion_id)

    # --- Gestión de Sufijos ---

    def obtener_sufijos(self) -> List[ProduccionSufijo]:
        return self.sufijos_repo.get_activos()

    def guardar_sufijo(self, nombre: str, sufijo_id: Optional[int] = None) -> bool:
        if sufijo_id:
            return self.sufijos_repo.actualizar(sufijo_id, nombre, 1)
        return self.sufijos_repo.crear(nombre) is not None

    def eliminar_sufijo(self, sufijo_id: int) -> bool:
        return self.sufijos_repo.eliminar(sufijo_id)
