"""Servicio para la configuración del taller (Backoffice).

Coordina la gestión de Colores, Tallas, Géneros y sus relaciones.
"""
from typing import List, Set, Optional
from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.produccion.models.produccion_color_model import ProduccionColor
from kool_tpv.modulos.produccion.models.produccion_talla_model import ProduccionTalla
from kool_tpv.modulos.produccion.models.produccion_genero_model import ProduccionGenero
from kool_tpv.modulos.produccion.repositories.produccion_colores_repository import ProduccionColoresRepository
from kool_tpv.modulos.produccion.repositories.produccion_generos_tallas_repository import ProduccionGenerosRepository, ProduccionTallasRepository
from kool_tpv.modulos.produccion.repositories.produccion_relaciones_repository import ProduccionRelacionesRepository
from kool_tpv.modulos.produccion.repositories.produccion_tipos_repository import ProduccionTiposRepository
from kool_tpv.modulos.produccion.repositories.produccion_menu_repository import ProduccionMenuRepository
from kool_tpv.modulos.produccion.repositories.produccion_menu_tipos_repository import ProduccionMenuTiposRepository
from kool_tpv.modulos.produccion.models.produccion_menu_model import ProduccionMenuItem

class ProduccionConfigService:
    def __init__(self, db: Database):
        self.db = db
        self.colores_repo = ProduccionColoresRepository(db)
        self.generos_repo = ProduccionGenerosRepository(db)
        self.tallas_repo = ProduccionTallasRepository(db)
        self.relaciones_repo = ProduccionRelacionesRepository(db)
        self.tipos_repo = ProduccionTiposRepository(db)
        self.menu_repo = ProduccionMenuRepository(db)
        self.menu_tipos_repo = ProduccionMenuTiposRepository(db)

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

    # --- Gestión de Géneros ---
    def obtener_todos_generos(self) -> List[ProduccionGenero]:
        return self.generos_repo.get_todos()

    def guardar_genero(self, nombre: str, orden: int, activo: int = 1, genero_id: Optional[int] = None) -> bool:
        genero = ProduccionGenero(id=genero_id, nombre=nombre, orden=orden, activo=activo)
        if genero_id:
            return self.generos_repo.actualizar(genero)
        return self.generos_repo.crear(genero) is not None

    # --- Gestión de la Matriz (Relaciones) ---
    def obtener_relaciones_genero(self, genero_id: int):
        """Obtener tallas y colores asociados a un género."""
        return {
            "tallas": self.relaciones_repo.get_tallas_id_por_genero(genero_id),
            "colores": self.relaciones_repo.get_colores_id_por_genero(genero_id)
        }

    def actualizar_relaciones_genero(self, genero_id: int, tallas_ids: List[int], colores_ids: List[int]):
        """Actualizar qué tallas y colores están disponibles para un género."""
        self.relaciones_repo.actualizar_tallas_genero(genero_id, tallas_ids)
        self.relaciones_repo.actualizar_colores_genero(genero_id, colores_ids)
        return True

    def obtener_generos_por_tipo(self, tipo_id: int) -> Set[int]:
        return self.relaciones_repo.get_generos_id_por_tipo(tipo_id)

    def actualizar_generos_tipo(self, tipo_id: int, generos_ids: List[int]):
        return self.relaciones_repo.actualizar_generos_tipo(tipo_id, generos_ids)

    # --- Matriz 3D: Género <-> Color <-> Talla ---

    def obtener_colores_genero_3d(self, genero_id: int) -> Set[int]:
        """IDs de colores asignados a un género (tabla 3D)."""
        return self.relaciones_repo.get_colores_id_por_genero_3d(genero_id)

    def obtener_tallas_genero_color_3d(self, genero_id: int, color_id: int) -> Set[int]:
        """IDs de tallas disponibles para una combinación género+color."""
        return self.relaciones_repo.get_tallas_id_por_genero_color_3d(genero_id, color_id)

    def guardar_tallas_genero_color_3d(self, genero_id: int, color_id: int, tallas_ids: List[int]):
        """Sincronizar tallas para una combinación género+color."""
        self.relaciones_repo.actualizar_tallas_genero_color_3d(genero_id, color_id, tallas_ids)
        return True

    def eliminar_color_genero_3d(self, genero_id: int, color_id: int):
        """Eliminar un color y todas sus tallas de un género."""
        self.relaciones_repo.remove_color_de_genero_3d(genero_id, color_id)
        return True

    # --- Gestión del Menú ---

    def obtener_todos_menu(self):
        """Obtener todos los elementos del menú."""
        return self.menu_repo.get_todos()

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
