"""Orquestador del flujo de entrada de stock base.

Contiene la clase `StockBaseFlow` que gestiona la navegación entre
subvistas con chips para dar de alta stock de materiales en blanco.

Flujo:
1. Menú (Textil, Sublimación...) → 2. Tipo (Camiseta, Taza...)
→ 3. Color (Negro, Blanco...) → 4. Talla (XL, L, M...) → 5. Final (SKU + Cantidad + GUARDAR)
"""
import tkinter as tk
from typing import Callable, List, Optional

from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.produccion.models.produccion_tipos_model import ProduccionTipo
from kool_tpv.modulos.produccion.models.produccion_tipo_variante_model import ProduccionTipoVariante
from kool_tpv.modulos.produccion.models.produccion_color_model import ProduccionColor
from kool_tpv.modulos.produccion.models.produccion_menu_model import ProduccionMenuItem
from kool_tpv.modulos.produccion.services.produccion_menu_service import ProduccionMenuService
from kool_tpv.modulos.produccion.services.produccion_colores_service import ProduccionColoresService
from kool_tpv.modulos.produccion.services.produccion_generos_tallas_service import ProduccionTallasService
from kool_tpv.modulos.produccion.services.produccion_stock_base_service import ProduccionStockBaseService
from kool_tpv.modulos.produccion.services.produccion_tipos_service import ProduccionTiposService
from kool_tpv.modulos.produccion.services.produccion_tipos_variantes_service import ProduccionTiposVariantesService

from kool_tpv.modulos.produccion.ui.subvistas.stock_base.stock_base_step_menu import StockBaseStepMenu
from kool_tpv.modulos.produccion.ui.subvistas.stock_base.stock_base_step_tipo import StockBaseStepTipo
from kool_tpv.modulos.produccion.ui.subvistas.produccion_nueva_produccion_variante import NuevaProduccionVarianteView
from kool_tpv.modulos.produccion.ui.subvistas.stock_base.stock_base_step_color import StockBaseStepColor
from kool_tpv.modulos.produccion.ui.subvistas.stock_base.stock_base_step_talla import StockBaseStepTalla
from kool_tpv.modulos.produccion.ui.subvistas.stock_base.stock_base_step_final import StockBaseStepFinal

# Pasos del flujo
PASO_MENU = 0
PASO_TIPO = 1
PASO_VARIANTE = 2
PASO_COLOR = 3
PASO_TALLA = 4
PASO_FINAL = 5


class StockBaseFlow:
    """Orquestador del flujo de entrada de stock base.

    Args:
        parent: Widget padre donde se mostrará el flujo.
        db: Instancia de `Database` ya conectada.
        on_cerrar: Callback cuando se cierra el flujo.
        on_guardado: Callback cuando se guarda una variante (para refrescar lista).
    """

    def __init__(self, parent, db: Database,
                 on_cerrar: Optional[Callable] = None,
                 on_guardado: Optional[Callable] = None,
                 item_data: Optional[dict] = None):
        self.parent = parent
        self.db = db
        self.on_cerrar = on_cerrar
        self.on_guardado = on_guardado

        # Servicios
        self._menu_service = ProduccionMenuService(db)
        self._colores_service = ProduccionColoresService(db)
        self._tallas_service = ProduccionTallasService(db)
        self._stock_service = ProduccionStockBaseService(db)
        self._tipos_service = ProduccionTiposService(db)
        self._variantes_service = ProduccionTiposVariantesService(db)

        # Estado del flujo
        self._paso_actual = PASO_MENU
        self._paso_anterior = PASO_MENU
        self._menu: Optional[ProduccionMenuItem] = None
        self._tipo: Optional[ProduccionTipo] = None
        self._variante: Optional[ProduccionTipoVariante] = None
        self._color: Optional[ProduccionColor] = None
        self._talla: Optional[str] = None
        self._sku_edit: Optional[str] = None
        self._cantidad_edit: Optional[int] = None
        self._modo_edicion = False

        # Vista activa
        self._vista_actual = None

        # Frame contenedor
        self.frame = tk.Frame(parent, bg="#2c3e50")
        self.frame.pack(fill=tk.BOTH, expand=True)

        # Si hay item_data (edición), cargar objetos y saltar al final
        if item_data:
            self._cargar_item(item_data)
            self._modo_edicion = True
            self._mostrar_paso(PASO_FINAL)
        else:
            self._mostrar_paso(PASO_MENU)

    def _cargar_item(self, item: dict):
        """Cargar datos de una fila existente para edición."""
        tipo_id = item.get("tipo_id")
        variante_id = item.get("variante_id")
        color_id = item.get("color_id")
        self._talla = item.get("talla") or ""
        self._sku_edit = item.get("sku") or ""
        self._cantidad_edit = item.get("cantidad") or 0

        if tipo_id:
            self._tipo = self._tipos_service.obtener_por_id(tipo_id)
        if variante_id:
            self._variante = self._variantes_service.obtener_por_id(variante_id)
        if color_id:
            self._color = self._colores_service.obtener_por_id(color_id)

    # --- Navegación entre pasos ---

    def _mostrar_paso(self, paso: int):
        """Mostrar la subvista correspondiente al paso."""
        if self._vista_actual is not None:
            try:
                self._vista_actual.destruir()
            except Exception:
                pass
            self._vista_actual = None

        self._paso_anterior = self._paso_actual
        self._paso_actual = paso

        if paso == PASO_MENU:
            self._vista_actual = StockBaseStepMenu(
                self.frame,
                db=self.db,
                on_siguiente=self._on_menu_siguiente,
                on_volver=self._on_volver_flow
            )

        elif paso == PASO_TIPO:
            menu_id = self._menu.id if self._menu else 0
            self._vista_actual = StockBaseStepTipo(
                self.frame,
                db=self.db,
                menu_id=menu_id,
                on_siguiente=self._on_tipo_siguiente,
                on_volver=lambda: self._mostrar_paso(PASO_MENU)
            )

        elif paso == PASO_VARIANTE:
            tipo_id = self._tipo.id if self._tipo else 0
            self._vista_actual = NuevaProduccionVarianteView(
                self.frame,
                db=self.db,
                tipo_id=tipo_id,
                on_siguiente=self._on_variante_siguiente,
                on_volver=self._on_variante_volver
            )

        elif paso == PASO_COLOR:
            tipo_id = self._tipo.id if self._tipo else 0
            variante_id = self._variante.id if self._variante else None
            self._vista_actual = StockBaseStepColor(
                self.frame,
                db=self.db,
                tipo_id=tipo_id,
                variante_id=variante_id,
                on_siguiente=self._on_color_siguiente,
                on_volver=self._on_color_volver
            )

        elif paso == PASO_TALLA:
            tallas = []
            if self._tipo and self._color:
                variante_id = self._variante.id if self._variante else None
                tallas = self._tallas_service.obtener_por_tipo_color_3d(
                    self._tipo.id, self._color.id, variante_id)
            tallas_data = [{"codigo": t.nombre, "nombre": t.nombre} for t in tallas]
            self._vista_actual = StockBaseStepTalla(
                self.frame,
                on_siguiente=self._on_talla_siguiente,
                on_volver=self._on_talla_volver,
                tallas_disponibles=tallas_data
            )

        elif paso == PASO_FINAL:
            # Construir resumen de selección
            partes = []
            if self._tipo:
                partes.append(self._tipo.nombre)
            if self._color:
                partes.append(self._color.nombre)
            if self._talla:
                partes.append(self._talla)
            resumen = " ".join(partes)

            self._vista_actual = StockBaseStepFinal(
                self.frame,
                resumen=resumen,
                on_guardar=self._on_final_guardar,
                on_volver=self._on_final_volver,
                on_otro=self._on_final_otro,
                sku_inicial=self._sku_edit,
                cantidad_inicial=self._cantidad_edit
            )

    # --- Callbacks de cada paso ---

    def _on_final_volver(self):
        """VOLVER desde el paso final."""
        if self._modo_edicion:
            self._cerrar_flow()
        else:
            tipo = self._tipo
            variante = self._variante
            if tipo and tipo.requiere_talla == 1:
                self._mostrar_paso(PASO_TALLA)
            elif tipo and tipo.requiere_color == 1:
                self._mostrar_paso(PASO_COLOR)
            elif variante and variante.requiere_talla == 1:
                self._mostrar_paso(PASO_TALLA)
            elif variante and variante.requiere_color == 1:
                self._mostrar_paso(PASO_COLOR)
            else:
                self._cerrar_flow()

    def _on_menu_siguiente(self, menu_item: ProduccionMenuItem):
        """Menú seleccionado → decidir si hay que mostrar tipos o ir directo a género."""
        self._menu = menu_item
        tipos = self._menu_service.obtener_tipos_por_menu(menu_item.id)

        if len(tipos) == 1:
            # Un solo tipo → usarlo directo, saltar PASO_TIPO
            self._tipo = tipos[0]
            self._ir_desde_tipo()
        elif len(tipos) > 1:
            # Varios tipos → mostrar paso de selección
            self._mostrar_paso(PASO_TIPO)
        else:
            # Sin tipos asociados → intentar compat 1:1 con tipo_id
            tipo = self._menu_service.obtener_tipo_asociado(menu_item)
            if tipo:
                self._tipo = tipo
                self._ir_desde_tipo()
            else:
                # Sin tipo → ir directo al final
                self._mostrar_paso(PASO_FINAL)

    def _ir_desde_tipo(self):
        """Lógica común: desde un tipo, decidir el siguiente paso según requiere_* y variantes."""
        tipo = self._tipo
        if tipo:
            variantes = self._variantes_service.obtener_por_tipo(tipo.id, solo_activos=True)
            if variantes:
                self._mostrar_paso(PASO_VARIANTE)
                return
        if tipo and tipo.requiere_color == 1:
            self._mostrar_paso(PASO_COLOR)
        elif tipo and tipo.requiere_talla == 1:
            self._mostrar_paso(PASO_TALLA)
        else:
            self._mostrar_paso(PASO_FINAL)

    def _on_tipo_siguiente(self, tipo: ProduccionTipo):
        """Tipo seleccionado → decidir siguiente paso según requiere_*."""
        self._tipo = tipo
        self._variante = None
        self._ir_desde_tipo()

    def _on_variante_siguiente(self, variante: ProduccionTipoVariante):
        """Variante seleccionada → decidir siguiente paso según requiere_*."""
        self._variante = variante
        tipo = self._tipo
        if tipo and tipo.requiere_color == 1:
            self._mostrar_paso(PASO_COLOR)
        elif variante and variante.requiere_color == 1:
            self._mostrar_paso(PASO_COLOR)
        elif tipo and tipo.requiere_talla == 1:
            self._mostrar_paso(PASO_TALLA)
        elif variante and variante.requiere_talla == 1:
            self._mostrar_paso(PASO_TALLA)
        else:
            self._mostrar_paso(PASO_FINAL)

    def _on_variante_volver(self):
        """Volver desde variante → tipo/menú."""
        if self._menu:
            self._mostrar_paso(PASO_TIPO)
        else:
            self._mostrar_paso(PASO_MENU)

    def _on_color_volver(self):
        """Volver desde color → variante, tipo o menú."""
        if self._variante:
            self._mostrar_paso(PASO_VARIANTE)
        elif self._menu:
            self._mostrar_paso(PASO_TIPO)
        else:
            self._mostrar_paso(PASO_MENU)

    def _on_color_siguiente(self, color: ProduccionColor):
        """Color seleccionado → decidir siguiente paso."""
        self._color = color
        tipo = self._tipo
        variante = self._variante
        if tipo and tipo.requiere_talla == 1:
            self._mostrar_paso(PASO_TALLA)
        elif variante and variante.requiere_talla == 1:
            self._mostrar_paso(PASO_TALLA)
        else:
            self._mostrar_paso(PASO_FINAL)

    def _on_talla_volver(self):
        """Volver desde talla → color si existe, variante si existe, si no tipo/menú."""
        tipo = self._tipo
        variante = self._variante
        if tipo and tipo.requiere_color == 1:
            self._mostrar_paso(PASO_COLOR)
        elif variante and variante.requiere_color == 1:
            self._mostrar_paso(PASO_COLOR)
        elif self._variante:
            self._mostrar_paso(PASO_VARIANTE)
        elif self._menu:
            self._mostrar_paso(PASO_TIPO)
        else:
            self._mostrar_paso(PASO_MENU)

    def _on_talla_siguiente(self, talla: str):
        """Talla seleccionada → ir a final."""
        self._talla = talla
        self._mostrar_paso(PASO_FINAL)

    def _on_final_guardar(self, sku: str, cantidad: int):
        """GUARDAR desde final → guardar variante en BD."""
        tipo_id = self._tipo.id if self._tipo else 0
        variante_id = self._variante.id if self._variante else None
        color_id = self._color.id if self._color else None
        talla = self._talla or ""

        ok = self._stock_service.guardar_variante(
            tipo_id=tipo_id,
            color_id=color_id,
            talla=talla,
            sku=sku,
            cantidad=cantidad,
            variante_id=variante_id
        )

        if ok:
            if self.on_guardado:
                self.on_guardado()
            self._cerrar_flow()
            from kool_tpv.utils.widgets.notificaciones.toast_widget import ToastWidget
            ToastWidget.show(self.parent, "Variante guardada con éxito", tipo="success")
        else:
            from kool_tpv.utils.widgets.notificaciones.toast_widget import ToastWidget
            ToastWidget.show(self.frame, "Error al guardar la variante", tipo="error")

    def _on_final_otro(self):
        """OTRA VARIANTE desde final → resetear y volver al paso 1."""
        self._menu = None
        self._tipo = None
        self._variante = None
        self._color = None
        self._talla = None
        self._sku_edit = None
        self._cantidad_edit = None
        self._mostrar_paso(PASO_MENU)

    def _on_volver_flow(self):
        """VOLVER desde el paso 1 → cerrar flujo."""
        self._cerrar_flow()

    # --- Utilidades ---

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
