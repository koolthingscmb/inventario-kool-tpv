"""
ARCHIVO ACTIVO DEL TPV.
Cualquier desarrollo debe realizarse aquí.
tpv_view_old.py está archivado en /archive.
"""

import customtkinter as ctk
import json
from pathlib import Path

# 1. SERVICIO CARRITO
from kool_tpv.modulos.tpv.carrito.carrito_service import CarritoService

# 2. IMPORTACIÓN EXACTA (SOLUCIÓN)
from kool_tpv.modulos.tpv.actions.buscar_articulo import BuscarArticuloPanel

# --- RUTA CONFIG ---
BASE_DIR = Path(__file__).resolve().parents[2] 
CONFIG_DIR = BASE_DIR / "config"

# Central ButtonFactory
from kool_tpv.utils.factories.button_factory import ButtonFactory

def load_config(filename: str) -> dict:
    try:
        with open(CONFIG_DIR / filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

class ClickableBreadcrumb(ctk.CTkFrame):
    def __init__(self, parent, font=None, text_color="white", bg_color="transparent", **kwargs):
        super().__init__(parent, fg_color=bg_color, **kwargs)
        self.custom_font = font
        self.text_color = text_color

    def update_parts(self, parts: list):
        for widget in self.winfo_children(): widget.destroy()
        for i, (text, callback) in enumerate(parts):
            if i > 0:
                ctk.CTkLabel(self, text='/', text_color=self.text_color, font=self.custom_font).pack(side='left', padx=4)
            if callback is None:
                ctk.CTkLabel(self, text=text, text_color=self.text_color, font=self.custom_font).pack(side='left', padx=2)
            else:
                btn = ctk.CTkButton(self, text=text, text_color=self.text_color, fg_color='transparent', hover_color='#333333', font=self.custom_font, command=callback, width=len(text) * 12, height=28, corner_radius=4, cursor='hand2')
                btn.pack(side='left', padx=2)

# use central ButtonFactory (imported above)

class TpvView(ctk.CTkFrame):
    def __init__(self, parent, db=None):
        super().__init__(parent)
        self.db = db

        # Referencia al contenedor para diálogos (requerido por TpvController)
        self.container = self

        # INICIALIZAR EL SERVICIO
        self.carrito_service = CarritoService()

        # Configs
        self.layout_cfg = load_config("layout_config.json")
        self.font_cfg = load_config("font_config.json")

        # PANEL DERECHO (TICKET)
        self.right_container = ctk.CTkFrame(self, width=520, corner_radius=0, fg_color="#1a1a1a")
        self.right_container.pack(side="right", fill="y")
        self.right_container.pack_propagate(False)

        try:
            from kool_tpv.utils.widgets.ticket_carrito import TicketCarrito
            # Pasamos el servicio al ticket
            self.ticket_widget = TicketCarrito(self.right_container, carrito_service=self.carrito_service)
            self.ticket_widget.pack(fill="both", expand=True)

            # Alias para compatibilidad con TpvController
            self.ticket_carrito = self.ticket_widget
        except ImportError:
            ctk.CTkLabel(self.right_container, text="[ ERROR TICKET ]", text_color="red").pack()

        # PANEL CENTRAL
        self.center_area = ctk.CTkFrame(self, corner_radius=0, fg_color="#222831")
        self.center_area.pack(side="left", fill="both", expand=True)

        bread_cfg = self.font_cfg.get("breadcrumb", {})
        bread_font = (bread_cfg.get("family", "Courier New"), bread_cfg.get("size", 20), "bold")

        self.breadcrumb = ClickableBreadcrumb(self.center_area, font=bread_font, text_color="#00FF00", height=50)
        self.breadcrumb.pack(side="top", fill="x", padx=20, pady=10)
        self.breadcrumb.update_parts([("INICIO", None), ("VENTAS", None), ("TPV", None)])

        self.grid_frame = ctk.CTkFrame(self.center_area, fg_color="transparent")
        self.grid_frame.pack(side="top", fill="both", expand=True, padx=20, pady=20)

        # Lista para referencias a botones del grid (requerido por button_action_mapper)
        self.grid_buttons = []
        # Stack para sub-vistas dinámicas (push/pop views)
        self._subview_stack = []

        # PANEL DE BÚSQUEDA (Con los datos pasados explícitamente)
        self.panel_buscar = BuscarArticuloPanel(
            self, 
            db=self.db, 
            carrito_service=self.carrito_service
        )

        self._build_grid_buttons()
        # Instanciar controlador (gestiona payment controllers, acciones y rebind de botones)
        try:
            from kool_tpv.modulos.tpv.tpv_controller import TpvController
            self.controller = TpvController(self, db=self.db)
        except Exception:
            # No queremos que la vista deje de inicializarse si el controlador falla
            self.controller = None

        # Registrar handler de power del TPV (prioriza pop de subviews)
        try:
            root = self.winfo_toplevel()
            if hasattr(root, "register_power_handler"):
                root.register_power_handler(self._handle_power, owner=self)
        except Exception:
            pass

        # Crear controlador (gestiona payment controllers, acciones y rebind)

    def _build_grid_buttons(self):
        cols = 4
        rows = 4
        for i in range(cols): self.grid_frame.grid_columnconfigure(i, weight=1)
        for i in range(rows): self.grid_frame.grid_rowconfigure(i, weight=1)

        # Read buttons from layout_config.json -> modules.tpv.center.grid.buttons
        buttons = self.layout_cfg.get("modules", {}).get("tpv", {}).get("center", {}).get("grid", {}).get("buttons", [])

        for index, btn_data in enumerate(buttons):
            row = btn_data.get("row")
            col = btn_data.get("col")
            columnspan = btn_data.get("colspan", 1)
            rowspan = btn_data.get("rowspan", 1)

            # preserve command mapping for buscar_articulo
            cmd_name = btn_data.get("command")
            cmd = self.panel_buscar.show if cmd_name == "buscar_articulo" else None
            btn = ButtonFactory.create_button(
                parent=self.grid_frame,
                text=btn_data.get("label", "???"),
                command=cmd,
                style_key=btn_data.get("style_key")
            )

            btn.grid(row=row, column=col, columnspan=columnspan, rowspan=rowspan, padx=10, pady=10, sticky="nsew")
            # Guardar referencia para mapper (lista de widgets, como espera el mapper)
            self.grid_buttons.append(btn)

    

    def teardown(self):
        pass

    def clear_grid(self):
        """Eliminar todos los widgets del grid y resetear referencias."""
        try:
            if hasattr(self, 'grid_frame') and self.grid_frame is not None:
                for widget in list(self.grid_frame.winfo_children()):
                    try:
                        widget.destroy()
                    except Exception:
                        try:
                            widget.grid_forget()
                        except Exception:
                            pass

            # Reset referencias a botones
            try:
                self.grid_buttons = []
            except Exception:
                pass
        except Exception:
            # No queremos que limpiar el grid lance excepciones
            try:
                import logging
                logging.exception('Error en clear_grid')
            except Exception:
                pass

    def push_subview(self, view_instance, title: str):
        """Mostrar una sub-vista encima del grid (guardando en stack)."""
        try:
            # Ocultar vista actual si existe
            if self._subview_stack:
                current_view = self._subview_stack[-1]["view"]
                try:
                    current_view.pack_forget()
                except Exception:
                    pass
            else:
                # Si estamos en el grid base, ocultar el frame del grid completamente
                try:
                    self.grid_frame.pack_forget()
                except Exception:
                    pass

            # Mostrar nueva vista
            try:
                view_instance.pack(fill="both", expand=True)
            except Exception:
                pass

            self._subview_stack.append({"view": view_instance, "title": title})
            try:
                self._update_breadcrumb()
            except Exception:
                pass
        except Exception:
            try:
                import logging
                logging.exception('Error en push_subview')
            except Exception:
                pass

    def pop_subview(self):
        """Cerrar la sub-vista actual y mostrar la anterior (o el grid base)."""
        try:
            if not self._subview_stack:
                return

            # Destruir vista actual
            current = self._subview_stack.pop()
            try:
                current["view"].destroy()
            except Exception:
                try:
                    current["view"].pack_forget()
                except Exception:
                    pass

            # Mostrar anterior
            if self._subview_stack:
                previous = self._subview_stack[-1]["view"]
                try:
                    previous.pack(fill="both", expand=True)
                except Exception:
                    pass
            else:
                # Volver al grid base: volver a mostrar el frame del grid y reconstruir botones
                try:
                    self.grid_frame.pack(side="top", fill="both", expand=True, padx=20, pady=20)
                    self.clear_grid()
                    self._build_grid_buttons()
                    if hasattr(self, "controller") and self.controller:
                        self.controller.rebind_buttons()
                except Exception:
                    pass

            try:
                self._update_breadcrumb()
            except Exception:
                pass
        except Exception:
            try:
                import logging
                logging.exception('Error en pop_subview')
            except Exception:
                pass

    def _update_breadcrumb(self):
        """Actualizar breadcrumb reflejando stack de sub-vistas."""
        try:
            parts = [("TPV", None)]
            for item in self._subview_stack:
                try:
                    parts.append((item.get("title", ""), None))
                except Exception:
                    parts.append(("?", None))

            try:
                self.breadcrumb.update_parts(parts)
            except Exception:
                pass
        except Exception:
            try:
                import logging
                logging.exception('Error en _update_breadcrumb')
            except Exception:
                pass

    def _on_power(self):
        """Handler de power específico para TPV.

        Prioriza cerrar sub-vistas apiladas (`_subview_stack`) llamando a
        `pop_subview()` si existe alguna. Si no hay sub-vistas, intenta
        limpiar `center_area` como comportamiento de fallback.
        """
        try:
            # Si hay sub-vistas en el stack, cerramos la última y retornamos
            if hasattr(self, '_subview_stack') and self._subview_stack:
                try:
                    self.pop_subview()
                except Exception:
                    pass
                return True

            # Fallback: si el área central tiene widgets, los removemos
            if hasattr(self, 'center_area') and self.center_area.winfo_children():
                try:
                    for w in list(self.center_area.winfo_children()):
                        try:
                            w.destroy()
                        except Exception:
                            try:
                                w.pack_forget()
                            except Exception:
                                pass
                except Exception:
                    pass

                try:
                    # Actualizar breadcrumb si procede
                    if hasattr(self, '_update_breadcrumb'):
                        self._update_breadcrumb()
                except Exception:
                    pass

                return True

            return False
        except Exception:
            try:
                import logging
                logging.exception('Error en _on_power (TPV)')
            except Exception:
                pass
            return False

    def _handle_power(self):
        if hasattr(self, "_subview_stack") and self._subview_stack:
            try:
                self.pop_subview()
            except Exception:
                pass
            return True
        return False