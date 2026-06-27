"""Orquestador del flujo de nueva producción.

Contiene la clase `NuevoProduccionFlow` que gestiona la navegación entre
subvistas, el estado de la selección y la lógica de saltar pasos según
el tipo de producto (requiere_talla, requiere_color).

Flujo:
1. Menú (producto) → 1b. Tipos (si el menú tiene +1 tipo) → 2. Variante (si tiene)
→ 3. Color (si requiere_color) → 4. Talla (si requiere_talla)
→ 5. Diseño → 6. Cantidad → 7. Resumen

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
from kool_tpv.modulos.produccion.services.produccion_generos_tallas_service import ProduccionTallasService
from kool_tpv.modulos.produccion.services.produccion_colores_service import ProduccionColoresService
from kool_tpv.modulos.produccion.services.produccion_menu_service import ProduccionMenuService
from kool_tpv.modulos.produccion.services.produccion_ordenes_service import ProduccionOrdenesService, ItemProduccion
from kool_tpv.modulos.produccion.ui.subvistas.produccion_nueva_produccion_origen import NuevaProduccionOrigenView
from kool_tpv.modulos.produccion.ui.subvistas.produccion_nueva_produccion import NuevaProduccionView
from kool_tpv.modulos.produccion.ui.subvistas.produccion_nueva_produccion_tipos import NuevaProduccionTiposView
from kool_tpv.modulos.produccion.ui.subvistas.produccion_nueva_produccion_variante import NuevaProduccionVarianteView
from kool_tpv.modulos.produccion.ui.subvistas.produccion_nueva_produccion_talla import NuevaProduccionTallaView
from kool_tpv.modulos.produccion.ui.subvistas.produccion_nueva_produccion_color import NuevaProduccionColorView
from kool_tpv.modulos.produccion.ui.subvistas.produccion_nueva_produccion_diseno import NuevaProduccionDisenoView
from kool_tpv.modulos.produccion.ui.subvistas.produccion_nueva_produccion_cantidad import NuevaProduccionCantidadView, CantidadSeleccion
from kool_tpv.modulos.produccion.ui.subvistas.produccion_nueva_produccion_resumen import NuevaProduccionResumenView

# Pasos del flujo
PASO_ORIGEN = 0
PASO_MENU = 1
PASO_TIPOS = 2
PASO_VARIANTE = 8
PASO_COLOR = 4
PASO_TALLA = 5
PASO_DISENO = 6
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
                 usuario_id: Optional[int] = None, usuario_nombre: str = ''):
        self.parent = parent
        self.db = db
        self.keyboard_mgr = keyboard_mgr
        self.on_cerrar = on_cerrar
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

        # Estado del flujo
        self._paso_actual = PASO_ORIGEN
        self._paso_anterior = PASO_ORIGEN
        self._menu: Optional[ProduccionMenuItem] = None
        self._tipo: Optional[ProduccionTipo] = None
        self._variante: Optional[ProduccionTipoVariante] = None
        self._talla: Optional[str] = None
        self._color: Optional[ProduccionColor] = None
        self._diseno: Optional[ProduccionDiseno] = None
        self._cantidad: Optional[CantidadSeleccion] = None
        self._items: List[ItemProduccion] = []
        self._origen: str = 'KOOL'

        # Vista activa
        self._vista_actual = None

        # Frame contenedor
        self.frame = tk.Frame(parent, bg="#2c3e50")
        self.frame.pack(fill=tk.BOTH, expand=True)

        # Label de cajero arriba del todo
        if usuario_nombre:
            import customtkinter as ctk
            self._lbl_cajero = ctk.CTkLabel(
                self.frame,
                text=f"Cajero: {usuario_nombre}",
                font=("Courier New", 14, "bold"),
                text_color="#C77BFF",
                anchor="e"
            )
            self._lbl_cajero.pack(fill="x", padx=20, pady=(4, 0))

        # Iniciar en el primer paso
        self._mostrar_paso(PASO_ORIGEN)

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

        if paso == PASO_ORIGEN:
            self._vista_actual = NuevaProduccionOrigenView(
                self.frame,
                on_siguiente=self._on_origen_siguiente,
                on_volver=self._on_volver_flow
            )

        elif paso == PASO_MENU:
            self._vista_actual = NuevaProduccionView(
                self.frame,
                db=self.db,
                keyboard_mgr=self.keyboard_mgr,
                on_siguiente=self._on_menu_siguiente,
                on_volver=self._on_volver_flow
            )

        elif paso == PASO_TIPOS:
            menu_id = self._menu.id if self._menu else 0
            self._vista_actual = NuevaProduccionTiposView(
                self.frame,
                db=self.db,
                menu_id=menu_id,
                on_siguiente=self._on_tipos_siguiente,
                on_volver=lambda: self._mostrar_paso(PASO_MENU)
            )

        elif paso == PASO_VARIANTE:
            self._vista_actual = NuevaProduccionVarianteView(
                self.frame,
                db=self.db,
                tipo_id=self._tipo.id if self._tipo else 0,
                on_siguiente=self._on_variante_siguiente,
                on_volver=self._on_variante_volver
            )

        elif paso == PASO_COLOR:
            tipo_id = self._tipo.id if self._tipo else 0
            variante_id = self._variante.id if self._variante else None
            self._vista_actual = NuevaProduccionColorView(
                self.frame,
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
                self.frame,
                on_siguiente=self._on_talla_siguiente,
                on_volver=self._on_talla_volver,
                tallas_disponibles=tallas_data,
                tipo_nombre=tipo_label,
                color_nombre=color_nombre
            )

        elif paso == PASO_DISENO:
            self._vista_actual = NuevaProduccionDisenoView(
                self.frame,
                db=self.db,
                keyboard_mgr=self.keyboard_mgr,
                on_siguiente=self._on_diseno_siguiente,
                on_volver=self._on_diseno_volver
            )

        elif paso == PASO_CANTIDAD:
            mostrar_mixta = self._es_tipo_camiseta()

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
                self.frame,
                on_siguiente=self._on_cantidad_siguiente,
                on_volver=self._on_cantidad_volver,
                on_anadir=self._on_cantidad_anadir,
                on_origen=self._on_cantidad_origen,
                mostrar_mixta=mostrar_mixta,
                diseno_nombre=resumen_completo
            )

        elif paso == PASO_RESUMEN:
            self._vista_actual = NuevaProduccionResumenView(
                self.frame,
                on_anadir=self._on_resumen_anadir,
                on_confirmar=self._on_resumen_confirmar,
                on_volver=lambda: self._mostrar_paso(PASO_CANTIDAD)
            )
            # Si ya hay items (venimos de AÑADIR), cargarlos
            for item in self._items:
                self._vista_actual.anadir_item(item)

    # --- Callbacks de cada paso ---

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
        if tipo.requiere_color == 1:
            self._mostrar_paso(PASO_COLOR)
        elif tipo.requiere_talla == 1:
            self._mostrar_paso(PASO_TALLA)
        else:
            self._mostrar_paso(PASO_DISENO)

    def _on_variante_siguiente(self, variante: ProduccionTipoVariante):
        """Variante seleccionada → seguir con filtros (Color...)."""
        self._variante = variante
        tipo = self._tipo
        
        # Un paso se muestra si el Tipo lo requiere O si la Variante lo requiere
        req_color = (tipo.requiere_color == 1) or (variante.requiere_color == 1)
        req_talla = (tipo.requiere_talla == 1) or (variante.requiere_talla == 1)

        if req_color:
            self._mostrar_paso(PASO_COLOR)
        elif req_talla:
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
        
        req_talla = (tipo.requiere_talla == 1) or (variante and variante.requiere_talla == 1)

        if req_talla:
            self._mostrar_paso(PASO_TALLA)
        else:
            self._mostrar_paso(PASO_DISENO)

    def _on_talla_volver(self):
        """Volver desde talla → ir a color o variante o tipos/menú."""
        tipo = self._tipo
        variante = self._variante
        
        req_color = (tipo.requiere_color == 1) or (variante and variante.requiere_color == 1)

        if req_color:
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
        
        req_talla = (tipo.requiere_talla == 1) or (variante and variante.requiere_talla == 1)
        req_color = (tipo.requiere_color == 1) or (variante and variante.requiere_color == 1)

        if req_talla:
            self._mostrar_paso(PASO_TALLA)
        elif req_color:
            self._mostrar_paso(PASO_COLOR)
        elif self._variante:
            self._mostrar_paso(PASO_VARIANTE)
        elif self._menu:
            self._mostrar_paso(PASO_TIPOS)
        else:
            self._mostrar_paso(PASO_MENU)

    def _on_diseno_siguiente(self, diseno: ProduccionDiseno):
        """Diseño seleccionado → ir a cantidad."""
        self._diseno = diseno
        self._mostrar_paso(PASO_CANTIDAD)

    def _on_cantidad_volver(self):
        """Volver desde cantidad → ir a diseño."""
        self._mostrar_paso(PASO_DISENO)

    def _on_cantidad_anadir(self, cantidad: CantidadSeleccion):
        """AÑADIR desde cantidad → crear ítem, resetear selección y volver al paso 1."""
        self._cantidad = cantidad
        self._crear_item()
        self._menu = None
        self._tipo = None
        self._variante = None
        self._talla = None
        self._color = None
        self._diseno = None
        self._cantidad = None
        self._mostrar_paso(PASO_MENU)

    def _on_cantidad_origen(self, cantidad: CantidadSeleccion):
        """ORIGEN desde cantidad → crear ítem, resetear selección y volver al paso origen."""
        self._cantidad = cantidad
        self._crear_item()
        self._menu = None
        self._tipo = None
        self._variante = None
        self._talla = None
        self._color = None
        self._diseno = None
        self._cantidad = None
        self._mostrar_paso(PASO_ORIGEN)

    def _on_cantidad_siguiente(self, cantidad: CantidadSeleccion):
        """Cantidad seleccionada → crear ítem y ir a resumen."""
        self._cantidad = cantidad
        self._crear_item()
        self._mostrar_paso(PASO_RESUMEN)

    def _on_resumen_anadir(self):
        """AÑADIR desde resumen → resetear selección y volver al paso 1."""
        self._menu = None
        self._tipo = None
        self._variante = None
        self._talla = None
        self._color = None
        self._diseno = None
        self._cantidad = None
        self._mostrar_paso(PASO_MENU)

    def _on_resumen_confirmar(self, items: List[ItemProduccion]):
        """CONFIRMAR desde resumen → guardar orden y cerrar flujo."""
        self._items = items

        # Guardar la orden en BD
        ok = self._ordenes_service.guardar_orden(items, usuario_id=self._usuario_id)

        if ok:
            # Mostrar mensaje de éxito
            total_uds = sum(item.cantidad for item in items)
            from kool_tpv.utils.widgets.notificaciones.toast_widget import ToastWidget
            ToastWidget.show(self.parent, f"Guardada Producción de {total_uds} artículos", tipo="success")

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

    def _crear_item(self):
        """Crear un ItemProduccion con los datos acumulados y calcular costes."""
        if not self._tipo:
            return

        # 1. Coste base (de la variante si existe, si no del tipo)
        if self._variante:
            coste_base = self._variante.coste_base / 100.0
        else:
            coste_base = self._tipo.coste_base or 0.0

        # 2. Coste del diseño para este tipo (en céntimos → euros)
        coste_diseno = 0.0
        if self._diseno:
            coste_diseno_cent = self._disenos_service.obtener_coste_por_tipo(
                self._diseno.codigo, self._tipo.nombre
            )
            coste_diseno = coste_diseno_cent / 100.0

        coste_unitario = coste_base + coste_diseno
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
            diseno_coleccion=self._diseno.coleccion if self._diseno else None,
            cantidad=cantidad,
            produccion_mixta=self._cantidad.produccion_mixta if self._cantidad else False,
            coste_unitario=coste_unitario,
            coste_total=coste_total,
            origen=self._origen
        )
        self._items.append(item)

    # --- Utilidades ---

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
