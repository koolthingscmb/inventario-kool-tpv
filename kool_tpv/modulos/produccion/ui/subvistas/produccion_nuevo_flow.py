"""Orquestador del flujo de nueva producción.

Contiene la clase `NuevoProduccionFlow` que gestiona la navegación entre
subvistas, el estado de la selección y la lógica de saltar pasos según
lo que haya disponible en el stock (colores, tallas).

Flujo:
1. Menú (producto) → 1b. Tipos (si el menú tiene +1 tipo) → 2. Variante (si tiene)
→ 3. Color (si hay colores en stock) → 4. Talla (si hay tallas en stock)
→ 5. Diseño → 6. Método → 7. Cantidad → 8. Resumen

Desde Resumen: AÑADIR vuelve al paso 1, CONFIRMAR guarda la orden.
"""
import tkinter as tk
from typing import Callable, List, Optional

from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.produccion.models.produccion_tipos_model import ProduccionTipo
from kool_tpv.modulos.produccion.models.produccion_tipo_variante_model import ProduccionTipoVariante
from kool_tpv.modulos.produccion.models.produccion_color_model import ProduccionColor
from kool_tpv.modulos.produccion.models.produccion_diseno_model import ProduccionDiseno
from kool_tpv.modulos.produccion.models.produccion_menu_model import ProduccionMenuItem
from kool_tpv.modulos.produccion.services.produccion_disenos_service import ProduccionDisenosService
from kool_tpv.modulos.produccion.services.produccion_tipos_service import ProduccionTiposService
from kool_tpv.modulos.produccion.services.produccion_tipos_variantes_service import ProduccionTiposVariantesService
from kool_tpv.modulos.produccion.services.produccion_tallas_service import ProduccionTallasService
from kool_tpv.modulos.produccion.services.produccion_colores_service import ProduccionColoresService
from kool_tpv.modulos.produccion.services.produccion_menu_service import ProduccionMenuService
from kool_tpv.modulos.produccion.services.produccion_ordenes_service import ProduccionOrdenesService, ItemProduccion
from kool_tpv.modulos.produccion.repositories.produccion_colecciones_repository import ProduccionColeccionesRepository
from kool_tpv.modulos.produccion.repositories.produccion_sufijos_repository import ProduccionSufijosRepository
from kool_tpv.base_datos.money_adapter import read_from_db
from kool_tpv.modulos.produccion.ui.subvistas.produccion_cajero_auth import CajeroAuthView
from kool_tpv.modulos.produccion.ui.subvistas.produccion_nueva_produccion_origen import NuevaProduccionOrigenView
from kool_tpv.modulos.produccion.ui.subvistas.produccion_nueva_produccion import NuevaProduccionView
from kool_tpv.modulos.produccion.ui.subvistas.produccion_nueva_produccion_tipos import NuevaProduccionTiposView
from kool_tpv.modulos.produccion.ui.subvistas.produccion_nueva_produccion_variante import NuevaProduccionVarianteView
from kool_tpv.modulos.produccion.ui.subvistas.produccion_nueva_produccion_talla import NuevaProduccionTallaView
from kool_tpv.modulos.produccion.ui.subvistas.produccion_nueva_produccion_color import NuevaProduccionColorView
from kool_tpv.modulos.produccion.ui.subvistas.produccion_nueva_produccion_diseno import NuevaProduccionDisenoView
from kool_tpv.modulos.produccion.services.tipos_variantes_metodos_service import TiposVariantesMetodosService
from kool_tpv.modulos.produccion.ui.subvistas.produccion_nueva_produccion_metodo import NuevaProduccionMetodoView, MetodoSeleccion
from kool_tpv.modulos.produccion.ui.subvistas.produccion_nueva_produccion_cantidad import NuevaProduccionCantidadView, CantidadSeleccion
from kool_tpv.modulos.produccion.ui.subvistas.produccion_nueva_produccion_resumen import NuevaProduccionResumenView

# Pasos del flujo
PASO_CAJERO = -1
PASO_ORIGEN = 0
PASO_MENU = 1
PASO_TIPOS = 2
PASO_VARIANTE = 8
PASO_COLOR = 4
PASO_TALLA = 5
PASO_DISENO = 6
PASO_METODO = 10
PASO_CANTIDAD = 7
PASO_RESUMEN = 9


class NuevoProduccionFlow:
    """Orquestador del flujo de nueva producción.

    Args:
        parent: Widget padre donde se mostrará el flujo.
        db: Instancia de `Database` ya conectada.
        on_cerrar: Callback cuando se cierra el flujo (al confirmar o cancelar).
    """

    def __init__(self, parent, db: Database, keyboard_mgr=None, on_cerrar: Optional[Callable] = None,
                 usuario_id: Optional[int] = None, usuario_nombre: str = '',
                 on_cajero_auth: Optional[Callable[[int, str], None]] = None):
        self.parent = parent
        self.db = db
        self.keyboard_mgr = keyboard_mgr
        self.on_cerrar = on_cerrar
        self.on_cajero_auth = on_cajero_auth
        self._usuario_id = usuario_id
        self._usuario_nombre = usuario_nombre

        # Servicios
        self._tipos_service = ProduccionTiposService(db)
        self._variantes_service = ProduccionTiposVariantesService(db)
        self._disenos_service = ProduccionDisenosService(db)
        self._tallas_service = ProduccionTallasService(db)
        self._colores_service = ProduccionColoresService(db)
        self._menu_service = ProduccionMenuService(db)
        self._ordenes_service = ProduccionOrdenesService(db)
        self._metodos_service = TiposVariantesMetodosService(db)
        self._colecciones_repo = ProduccionColeccionesRepository(db)
        self._sufijos_repo = ProduccionSufijosRepository(db)

        # Estado del flujo
        self._paso_actual = PASO_CAJERO if not usuario_id else PASO_ORIGEN
        self._paso_anterior = self._paso_actual
        self._menu: Optional[ProduccionMenuItem] = None
        self._tipo: Optional[ProduccionTipo] = None
        self._variante: Optional[ProduccionTipoVariante] = None
        self._talla: Optional[str] = None
        self._talla_auto_asignada: bool = False
        self._color: Optional[ProduccionColor] = None
        self._diseno: Optional[ProduccionDiseno] = None
        self._metodo: Optional[MetodoSeleccion] = None
        self._cantidad: Optional[CantidadSeleccion] = None
        self._items: List[ItemProduccion] = []
        self._origen: str = 'KOOL'

        # Vista activa
        self._vista_actual = None

        # Frame contenedor
        self.frame = tk.Frame(parent, bg="#2c3e50")
        self.frame.pack(fill=tk.BOTH, expand=True)

        # Header para info de cajero
        self._header = tk.Frame(self.frame, bg="#2c3e50")
        self._header.pack(fill="x", side=tk.TOP)

        # Label de cajero arriba a la derecha (siempre creado, se actualiza tras auth)
        import customtkinter as ctk
        self._lbl_cajero = ctk.CTkLabel(
            self._header,
            text=f"Cajero: {usuario_nombre}" if usuario_nombre else "",
            font=("Courier New", 14, "bold"),
            text_color="#C77BFF",
            anchor="e"
        )
        self._lbl_cajero.pack(side=tk.RIGHT, padx=20, pady=(4, 0))

        # El contenido de los pasos irá en este frame
        self._content_frame = tk.Frame(self.frame, bg="#2c3e50")
        self._content_frame.pack(fill=tk.BOTH, expand=True)

        # Iniciar en el primer paso
        self._mostrar_paso(self._paso_actual)

    # --- Navegación entre pasos ---

    def _mostrar_paso(self, paso: int):
        """Mostrar la subvista correspondiente al paso."""
        # Destruir vista anterior
        if self._vista_actual is not None:
            try:
                self._vista_actual.destruir()
            except Exception:
                pass
            self._vista_actual = None

        self._paso_anterior = self._paso_actual
        self._paso_actual = paso

        if paso == PASO_CAJERO:
            self._vista_actual = CajeroAuthView(
                self._content_frame,
                db=self.db,
                on_success=self._on_cajero_auth_success,
                on_cancel=self._on_volver_flow
            )

        elif paso == PASO_ORIGEN:
            self._vista_actual = NuevaProduccionOrigenView(
                self._content_frame,
                on_siguiente=self._on_origen_siguiente,
                on_volver=lambda: self._mostrar_paso(PASO_CAJERO)
            )

        elif paso == PASO_MENU:
            self._vista_actual = NuevaProduccionView(
                self._content_frame,
                db=self.db,
                keyboard_mgr=self.keyboard_mgr,
                on_siguiente=self._on_menu_siguiente,
                on_volver=lambda: self._mostrar_paso(PASO_ORIGEN)
            )

        elif paso == PASO_TIPOS:
            menu_id = self._menu.id if self._menu else 0
            self._vista_actual = NuevaProduccionTiposView(
                self._content_frame,
                db=self.db,
                menu_id=menu_id,
                on_siguiente=self._on_tipos_siguiente,
                on_volver=lambda: self._mostrar_paso(PASO_MENU)
            )

        elif paso == PASO_VARIANTE:
            self._vista_actual = NuevaProduccionVarianteView(
                self._content_frame,
                db=self.db,
                tipo_id=self._tipo.id if self._tipo else 0,
                on_siguiente=self._on_variante_siguiente,
                on_volver=self._on_variante_volver
            )

        elif paso == PASO_COLOR:
            tipo_id = self._tipo.id if self._tipo else 0
            variante_id = self._variante.id if self._variante else None
            self._vista_actual = NuevaProduccionColorView(
                self._content_frame,
                db=self.db,
                tipo_id=tipo_id,
                variante_id=variante_id,
                on_siguiente=self._on_color_siguiente,
                on_volver=self._on_color_volver
            )

        elif paso == PASO_TALLA:
            tallas = []
            color_nombre = self._color.nombre if self._color else None
            
            if self._tipo and self._color:
                tipo_id = self._tipo.id
                variante_id = self._variante.id if self._variante else None
                tallas = self._tallas_service.obtener_por_tipo_color_3d(
                    tipo_id, self._color.id, variante_id)

            tipo_nombre = self._tipo.nombre if self._tipo else ""
            var_nombre = f" / {self._variante.nombre}" if self._variante else ""
            tipo_label = f"{tipo_nombre}{var_nombre}" if tipo_nombre else None

            tallas_data = [{"codigo": t.nombre, "nombre": t.nombre} for t in tallas]
            self._vista_actual = NuevaProduccionTallaView(
                self._content_frame,
                on_siguiente=self._on_talla_siguiente,
                on_volver=self._on_talla_volver,
                tallas_disponibles=tallas_data,
                tipo_nombre=tipo_label,
                color_nombre=color_nombre
            )

        elif paso == PASO_DISENO:
            self._vista_actual = NuevaProduccionDisenoView(
                self._content_frame,
                db=self.db,
                keyboard_mgr=self.keyboard_mgr,
                on_siguiente=self._on_diseno_siguiente,
                on_volver=self._on_diseno_volver
            )

        elif paso == PASO_METODO:
            self._vista_actual = NuevaProduccionMetodoView(
                self._content_frame,
                db=self.db,
                variante_id=self._variante.id if self._variante else 0,
                on_siguiente=self._on_metodo_siguiente,
                on_volver=self._on_metodo_volver
            )

        elif paso == PASO_CANTIDAD:
            mostrar_mixta = self._es_tipo_camiseta()

            # Consultar stock disponible para esta combinación
            stock_disponible = 0
            if self._tipo and self._color and self._talla:
                try:
                    from kool_tpv.modulos.produccion.repositories.produccion_stock_base_repository import ProduccionStockBaseRepository
                    stock_repo = ProduccionStockBaseRepository(self.db)
                    variante_id = self._variante.id if self._variante else None
                    stock_disponible = stock_repo.obtener_cantidad(
                        self._tipo.id, self._color.id, self._talla, variante_id
                    )
                except Exception:
                    pass

            # Construir frase resumen: Producto + Variante + Color + Talla + Diseño
            partes = []
            if self._tipo:
                partes.append(self._tipo.nombre)
            if self._variante:
                partes.append(self._variante.nombre)
            if self._color:
                partes.append(self._color.nombre)
            if self._talla:
                partes.append(self._talla)
            if self._diseno:
                partes.append(f"'{self._diseno.nombre}'")

            resumen_completo = " ".join(partes)

            self._vista_actual = NuevaProduccionCantidadView(
                self._content_frame,
                db=self.db,
                on_siguiente=self._on_cantidad_siguiente,
                on_volver=self._on_cantidad_volver,
                on_anadir=self._on_cantidad_anadir,
                on_lote=self._on_cantidad_lote,
                on_origen=self._on_cantidad_origen,
                mostrar_mixta=mostrar_mixta,
                diseno_nombre=resumen_completo,
                stock_disponible=stock_disponible
            )

        elif paso == PASO_RESUMEN:
            self._vista_actual = NuevaProduccionResumenView(
                self._content_frame,
                on_anadir=self._on_resumen_anadir,
                on_confirmar=self._on_resumen_confirmar,
                on_volver=lambda: self._mostrar_paso(PASO_CANTIDAD)
            )
            # 1. Cargar ítems ya confirmados (si existen)
            for item in self._items:
                self._vista_actual.anadir_item(item)
            
            # 2. Cargar el ítem que se acaba de configurar (el "pendiente")
            item_actual = self._crear_item()
            if item_actual:
                self._vista_actual.anadir_item(item_actual)

    # --- Callbacks de cada paso ---

    def _on_cajero_auth_success(self, usuario_id: int, nombre: str):
        """Cajero autenticado -> ir a origen."""
        self._usuario_id = usuario_id
        self._usuario_nombre = nombre
        # Actualizar label si existe
        if hasattr(self, '_lbl_cajero'):
            self._lbl_cajero.configure(text=f"Cajero: {nombre}")
        # Notificar a ProduccionView para que persista el cajero
        if self.on_cajero_auth:
            self.on_cajero_auth(usuario_id, nombre)
        self._mostrar_paso(PASO_ORIGEN)

    def _on_origen_siguiente(self, origen: str):
        """Origen seleccionado (KOOL / CUSTOM) → ir al menú de producto."""
        self._origen = origen
        self._mostrar_paso(PASO_MENU)

    def _on_menu_siguiente(self, menu_item: ProduccionMenuItem):
        """Menú seleccionado → decidir si hay que mostrar tipos o ir directo."""
        self._menu = menu_item
        tipos = self._menu_service.obtener_tipos_por_menu(menu_item.id)

        if len(tipos) == 1:
            # Un solo tipo → usarlo directo, saltar PASO_TIPOS
            self._tipo = tipos[0]
            self._ir_desde_tipo()
        elif len(tipos) > 1:
            # Varios tipos → mostrar paso de selección
            self._mostrar_paso(PASO_TIPOS)
        else:
            # Sin tipos asociados → intentar compat 1:1 con tipo_id
            tipo = self._menu_service.obtener_tipo_asociado(menu_item)
            if tipo:
                self._tipo = tipo
                self._ir_desde_tipo()
            else:
                # Sin tipo → ir a diseño directamente
                self._mostrar_paso(PASO_DISENO)

    def _on_tipos_siguiente(self, tipo: ProduccionTipo):
        """Tipo seleccionado → decidir siguiente paso según requiere_*."""
        self._tipo = tipo
        self._ir_desde_tipo()

    def _ir_desde_tipo(self):
        """Lógica común: desde un tipo, decidir el siguiente paso (Variantes o filtros)."""
        tipo = self._tipo
        # 1. ¿Tiene variantes?
        variantes = self._variantes_service.obtener_por_tipo(tipo.id, solo_activos=True)
        if variantes:
            self._mostrar_paso(PASO_VARIANTE)
            return

        # 2. Si no hay variantes, seguir flujo normal
        #    Decidir si mostrar color/talla según lo que haya en el stock
        if self._hay_colores_disponibles(tipo.id, None):
            self._mostrar_paso(PASO_COLOR)
        elif self._hay_tallas_disponibles(tipo.id, None, None):
            self._mostrar_paso(PASO_TALLA)
        else:
            self._mostrar_paso(PASO_DISENO)

    def _on_variante_siguiente(self, variante: ProduccionTipoVariante):
        """Variante seleccionada → seguir con filtros (Color...)."""
        self._variante = variante
        tipo = self._tipo
        variante_id = variante.id if variante else None

        # Decidir si mostrar color/talla según lo que haya en el stock
        if self._hay_colores_disponibles(tipo.id, variante_id):
            self._mostrar_paso(PASO_COLOR)
        elif self._hay_tallas_disponibles(tipo.id, variante_id, None):
            self._mostrar_paso(PASO_TALLA)
        else:
            self._mostrar_paso(PASO_DISENO)

    def _on_variante_volver(self):
        """Volver desde variante → volver a TIPOS o MENU."""
        if self._paso_anterior == PASO_TIPOS or self._menu:
            self._mostrar_paso(PASO_TIPOS)
        else:
            self._mostrar_paso(PASO_MENU)

    def _on_color_volver(self):
        """Volver desde color → ir a variante o tipos/menú."""
        if self._variante:
            self._mostrar_paso(PASO_VARIANTE)
        elif self._paso_anterior == PASO_TIPOS or self._menu:
            self._mostrar_paso(PASO_TIPOS)
        else:
            self._mostrar_paso(PASO_MENU)

    def _on_color_siguiente(self, color: ProduccionColor):
        """Color seleccionado → decidir siguiente paso."""
        self._color = color
        tipo = self._tipo
        variante = self._variante
        variante_id = variante.id if variante else None

        # Si hay tallas disponibles, comprobar si solo hay una → auto-asignar
        if self._hay_tallas_disponibles(tipo.id, variante_id, color.id):
            tallas = self._tallas_service.obtener_por_tipo_color_3d(tipo.id, color.id, variante_id)
            if len(tallas) == 1:
                self._talla = tallas[0].nombre
                self._talla_auto_asignada = True
                self._mostrar_paso(PASO_DISENO)
            else:
                self._talla_auto_asignada = False
                self._mostrar_paso(PASO_TALLA)
        else:
            self._talla_auto_asignada = False
            self._mostrar_paso(PASO_DISENO)

    def _on_talla_volver(self):
        """Volver desde talla → ir a color o variante o tipos/menú."""
        tipo = self._tipo
        variante = self._variante
        variante_id = variante.id if variante else None

        # Volver a color si había colores disponibles
        if self._hay_colores_disponibles(tipo.id, variante_id):
            self._mostrar_paso(PASO_COLOR)
        elif self._variante:
            self._mostrar_paso(PASO_VARIANTE)
        elif self._menu:
            self._mostrar_paso(PASO_TIPOS)
        else:
            self._mostrar_paso(PASO_MENU)

    def _on_talla_siguiente(self, talla: str):
        """Talla seleccionada → ir a diseño."""
        self._talla = talla
        self._mostrar_paso(PASO_DISENO)

    def _on_diseno_volver(self):
        """Volver desde diseño → talla, color, variante o tipos/menú."""
        tipo = self._tipo
        variante = self._variante
        variante_id = variante.id if variante else None
        color_id = self._color.id if self._color else None

        # Volver a talla si se mostró el paso (no auto-asignada)
        if not self._talla_auto_asignada and self._hay_tallas_disponibles(tipo.id, variante_id, color_id):
            self._mostrar_paso(PASO_TALLA)
        elif self._hay_colores_disponibles(tipo.id, variante_id):
            self._mostrar_paso(PASO_COLOR)
        elif self._variante:
            self._mostrar_paso(PASO_VARIANTE)
        elif self._menu:
            self._mostrar_paso(PASO_TIPOS)
        else:
            self._mostrar_paso(PASO_MENU)

    def _on_diseno_siguiente(self, diseno: ProduccionDiseno):
        """Diseño seleccionado → ir a método (si hay variante) o cantidad."""
        self._diseno = diseno
        if self._variante:
            # Comprobar cuántos métodos tiene la variante
            metodos = self._metodos_service.obtener_metodos_por_variante(self._variante.id)
            if len(metodos) == 1:
                # Solo uno -> auto-seleccionar y saltar al siguiente paso
                m = metodos[0]
                self._metodo = MetodoSeleccion(id=m['id'], nombre=m['nombre'])
                self._mostrar_paso(PASO_CANTIDAD)
            elif len(metodos) > 1:
                self._mostrar_paso(PASO_METODO)
            else:
                # Sin métodos configurados -> ir a cantidad (coste método será 0)
                self._metodo = None
                self._mostrar_paso(PASO_CANTIDAD)
        else:
            self._mostrar_paso(PASO_CANTIDAD)

    def _on_metodo_siguiente(self, metodo: MetodoSeleccion):
        """Método seleccionado → ir a cantidad."""
        self._metodo = metodo
        self._mostrar_paso(PASO_CANTIDAD)

    def _on_metodo_volver(self):
        """Volver desde método → ir a diseño."""
        self._mostrar_paso(PASO_DISENO)

    def _on_cantidad_lote(self, seleccion: CantidadSeleccion):
        """AÑADIR LOTE desde cantidad → guardar el actual y volver al paso de diseño."""
        self._cantidad = seleccion
        item_actual = self._crear_item()
        if item_actual:
            self._items.append(item_actual)
            
        # Limpiar solo lo específico del diseño para permitir elegir otro para la misma prenda
        self._diseno = None
        self._metodo = None
        self._cantidad = None
        self._mostrar_paso(PASO_DISENO)

    def _on_cantidad_volver(self):
        """Volver desde cantidad → ir a método o diseño."""
        if self._metodo:
            # Comprobar si el método fue auto-seleccionado (solo había uno)
            metodos = self._metodos_service.obtener_metodos_por_variante(self._variante.id) if self._variante else []
            if len(metodos) == 1:
                self._mostrar_paso(PASO_DISENO)
            else:
                self._mostrar_paso(PASO_METODO)
        else:
            self._mostrar_paso(PASO_DISENO)

    def _on_cantidad_siguiente(self, cantidad: CantidadSeleccion):
        """Cantidad seleccionada → ir a resumen."""
        self._cantidad = cantidad
        self._mostrar_paso(PASO_RESUMEN)

    def _on_cantidad_anadir(self, cantidad: CantidadSeleccion):
        """AÑADIR desde cantidad → crear ítem, resetear selección y volver al paso 1."""
        self._cantidad = cantidad
        item = self._crear_item()
        if item:
            self._items.append(item)
        self._menu = None
        self._tipo = None
        self._variante = None
        self._talla = None
        self._talla_auto_asignada = False
        self._color = None
        self._diseno = None
        self._metodo = None
        self._cantidad = None
        self._mostrar_paso(PASO_MENU)

    def _on_cantidad_origen(self, cantidad: CantidadSeleccion):
        """ORIGEN desde cantidad → crear ítem, resetear selección y volver al paso origen."""
        self._cantidad = cantidad
        item = self._crear_item()
        if item:
            self._items.append(item)
        self._menu = None
        self._tipo = None
        self._variante = None
        self._talla = None
        self._talla_auto_asignada = False
        self._color = None
        self._diseno = None
        self._metodo = None
        self._cantidad = None
        self._mostrar_paso(PASO_ORIGEN)

    def _on_resumen_anadir(self):
        """AÑADIR desde resumen → guardar el actual en la lista y volver al paso 1."""
        item_actual = self._crear_item()
        if item_actual:
            self._items.append(item_actual)
            
        self._menu = None
        self._tipo = None
        self._variante = None
        self._talla = None
        self._talla_auto_asignada = False
        self._color = None
        self._diseno = None
        self._metodo = None
        self._cantidad = None
        self._mostrar_paso(PASO_MENU)

    def _on_resumen_confirmar(self, items_resumen: List[ItemProduccion]):
        """CONFIRMAR desde resumen → guardar orden y cerrar flujo."""
        # Nota: items_resumen ya incluye el ítem actual que se estaba configurando
        # porque lo añadimos al mostrar el paso.
        self._items = items_resumen

        # Guardar la orden en BD
        result = self._ordenes_service.guardar_orden(self._items, usuario_id=self._usuario_id)

        if result >= 0:
            # Mostrar mensaje de éxito
            total_uds = sum(item.cantidad for item in self._items)
            from kool_tpv.utils.widgets.notificaciones.toast_widget import ToastWidget
            ToastWidget.show(self.parent, f"Guardada Producción de {total_uds} artículos", tipo="success")

            if result > 0:
                ToastWidget.show(self.parent, f"Se han borrado {result} líneas de la Reposición", tipo="success")

            # Cerramos el flujo
            self._cerrar_flow()
        else:
            # Mostrar error (el servicio ya lo loguea)
            from kool_tpv.utils.widgets.notificaciones.toast_widget import ToastWidget
            ToastWidget.show(self.frame, "Error al guardar la producción", tipo="error")

    def _on_volver_flow(self):
        """VOLVER desde el paso 1 → cerrar flujo."""
        self._cerrar_flow()

    # --- Lógica de costes ---

    def _crear_item(self) -> Optional[ItemProduccion]:
        """Crear un ItemProduccion con los datos acumulados y calcular costes."""
        if not self._tipo:
            return None

        # 1. Coste base (coste medio del material en blanco)
        coste_base = 0.0
        # Intentar obtener coste_medio de produccion_stock_colores_tallas
        try:
            query = """
                SELECT coste_medio 
                FROM produccion_stock_colores_tallas 
                WHERE tipo_id = ? AND color_id IS ? AND talla IS ?
            """
            params = [self._tipo.id, self._color.id if self._color else None, self._talla]
            if self._variante:
                query += " AND variante_id = ?"
                params.append(self._variante.id)
            else:
                query += " AND variante_id IS NULL"
            
            row = self.db.fetch_one(query, tuple(params))
            if row:
                coste_base = float(read_from_db(row[0]))
        except Exception:
            # Fallback al coste_base de la variante si falla la consulta
            if self._variante:
                coste_base = float(read_from_db(self._variante.coste_base))
            else:
                coste_base = float(read_from_db(self._tipo.coste_base or 0))

        # 2. Coste del método de impresión (desde produccion_disenos_metodos)
        coste_metodo = 0.0
        if self._diseno and self._metodo:
            try:
                query = "SELECT coste FROM produccion_disenos_metodos WHERE diseno_codigo = ? AND metodo_id = ?"
                row = self.db.fetch_one(query, (self._diseno.codigo, self._metodo.id))
                if row:
                    coste_metodo = float(read_from_db(row[0]))
            except Exception:
                pass

        # 3. Coste del Extra
        coste_extra = self._cantidad.extra_coste if self._cantidad else 0.0

        coste_unitario = coste_base + coste_metodo + coste_extra
        cantidad = self._cantidad.cantidad if self._cantidad else 0
        coste_total = coste_unitario * cantidad

        item = ItemProduccion(
            tipo_nombre=self._tipo.nombre,
            tipo_id=self._tipo.id,
            variante_nombre=self._variante.nombre if self._variante else None,
            variante_id=self._variante.id if self._variante else None,
            talla=self._talla,
            color_nombre=self._color.nombre if self._color else None,
            color_id=self._color.id if self._color else None,
            diseno_codigo=self._diseno.codigo if self._diseno else None,
            diseno_nombre=self._diseno.nombre if self._diseno else None,
            diseno_coleccion=self._get_coleccion_nombre(self._diseno.coleccion_id) if self._diseno else None,
            coleccion_id=self._diseno.coleccion_id if self._diseno else None,
            diseno_sufijo=self._get_sufijo_nombre(self._diseno.sufijo_id) if self._diseno else None,
            cantidad=cantidad,
            produccion_mixta=self._cantidad.produccion_mixta if self._cantidad else False,
            extra_id=self._cantidad.extra_id if self._cantidad else None,
            extra_coste=self._cantidad.extra_coste if self._cantidad else 0.0,
            extra_nombre=self._cantidad.extra_nombre if self._cantidad else None,
            coste_unitario=coste_unitario,
            coste_total=coste_total,
            metodo_id=self._metodo.id if self._metodo else None,
            metodo_nombre=self._metodo.nombre if self._metodo else None,
            origen=self._origen,
            usuario_nombre=self._usuario_nombre
        )
        return item

    # --- Utilidades ---

    def _hay_colores_disponibles(self, tipo_id: int, variante_id: Optional[int]) -> bool:
        """Comprobar si hay colores asignados en el stock para este tipo/variante."""
        try:
            colores = self._colores_service.obtener_por_tipo_3d(tipo_id, variante_id)
            return len(colores) > 0
        except Exception:
            return False

    def _hay_tallas_disponibles(self, tipo_id: int, variante_id: Optional[int],
                                color_id: Optional[int]) -> bool:
        """Comprobar si hay tallas asignadas en el stock para esta combinación."""
        try:
            if not color_id:
                return False
            tallas = self._tallas_service.obtener_por_tipo_color_3d(tipo_id, color_id, variante_id)
            return len(tallas) > 0
        except Exception:
            return False

    def _get_coleccion_nombre(self, coleccion_id: int) -> str:
        """Resolver nombre de colección desde ID."""
        c = self._colecciones_repo.get_por_id(coleccion_id)
        return c.nombre if c else ""

    def _get_sufijo_nombre(self, sufijo_id) -> str:
        """Resolver nombre de sufijo desde ID."""
        if not sufijo_id:
            return ""
        s = self._sufijos_repo.get_por_id(sufijo_id)
        return s.nombre if s else ""

    def _es_tipo_camiseta(self) -> bool:
        """Comprobar si el tipo seleccionado es camiseta (para producción mixta)."""
        if not self._tipo:
            return False
        return self._tipo.nombre.lower() in ("camiseta", "camisetas")

    def _cerrar_flow(self):
        """Cerrar el flujo y notificar al callback."""
        try:
            if self._vista_actual:
                self._vista_actual.destruir()
        except Exception:
            pass
        self.frame.destroy()
        if self.on_cerrar:
            self.on_cerrar()

    def destruir(self):
        """Destruir el flujo y limpiar recursos."""
        try:
            if self._vista_actual:
                self._vista_actual.destruir()
        except Exception:
            pass
        self.frame.destroy()
