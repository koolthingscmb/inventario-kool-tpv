import customtkinter as ctk
import logging
import importlib
from typing import Optional

logger = logging.getLogger(__name__)


# Intentar importar el widget desde posibles rutas conocidas en orden
BuscarArticuloWidget = None
for module_path in (
    "kool_tpv.modulos.tpv.actions.buscar_articulo_widget",
    "kool_tpv.modulos.tpv.tpv_actions.buscar_articulo_widget",
):
    try:
        mod = importlib.import_module(module_path)
        BuscarArticuloWidget = getattr(mod, "BuscarArticuloWidget", None)
        if BuscarArticuloWidget:
            break
    except (ImportError, AttributeError):
        continue


class BuscarArticuloPanel:
    """Wrapper/controller for the BuscarArticuloWidget.

    Signature accepts optional `db` and `carrito_service` and prefers those
    explicit values over automatic resolution from the provided view object.
    """

    def __init__(self, view_or_action_panel, db: Optional[object] = None, carrito_service: Optional[object] = None, on_close=None, ui_config=None):
        self.on_close = on_close
        self._visible = False
        self.widget = None

        # Resolve root/view
        if hasattr(view_or_action_panel, "winfo_toplevel"):
            self.root = view_or_action_panel.winfo_toplevel()
            self.view = view_or_action_panel
        else:
            # view_or_action_panel may already be the app/view
            self.view = view_or_action_panel
            self.root = getattr(self.view, 'root', None) or self.view

        # Prefer explicit args; otherwise try to find on the view/root
        self.db = db or getattr(self.view, 'db', None)
        self.carrito_service = carrito_service or getattr(self.view, 'carrito_service', None)

        # If carrito_service still not found, try ticket child
        if not self.carrito_service:
            ticket = getattr(self.view, 'ticket_carrito', None) or getattr(self.view, 'ticket', None)
            if ticket:
                self.carrito_service = getattr(ticket, 'carrito_service', None)

        # Create overlay frame (use self.root as parent)
        try:
            self.overlay = ctk.CTkFrame(self.root, width=0, height=0, fg_color="#000000", corner_radius=0)
        except Exception:
            # Fallback: attach to view if root fails
            self.overlay = ctk.CTkFrame(self.view, width=0, height=0, fg_color="#000000", corner_radius=0)
        # Prevent children packing from automatically resizing the overlay
        try:
            self.overlay.pack_propagate(False)
        except Exception:
            pass

        # Instantiate widget if possible
        if self.db and self.carrito_service and BuscarArticuloWidget is not None:
            try:
                self.widget = BuscarArticuloWidget(
                    parent=self.overlay,
                    db=self.db,
                    carrito_service=self.carrito_service,
                    on_add_callback=self._refresh_ticket,
                    on_close_callback=self.hide
                )
                self.widget.pack(fill="both", expand=True)
            except Exception:
                logger.exception("Error iniciando BuscarArticuloWidget")
        else:
            logger.error("Faltan dependencias o widget no importado. DB: %s, TPV_VIEW: %s, BuscarArticuloWidget: %s", self.db, getattr(self.view, 'tpv_view', None), BuscarArticuloWidget)
            try:
                ctk.CTkLabel(self.overlay, text="ERROR: No se encuentra el servicio de carrito", text_color="red").pack(expand=True)
            except Exception:
                pass

    def _refresh_ticket(self):
        try:
            ticket = getattr(self.view, 'ticket_widget', None) or getattr(self.view, 'ticket_carrito', None) or getattr(self.view, 'ticket', None)
            if ticket and hasattr(ticket, 'update_carrito'):
                ticket.update_carrito()
        except Exception:
            logger.exception("Error refrescando ticket desde BuscarArticuloPanel")

    def show(self):
        if not self.root:
            return
        try:
            self._visible = True

            # Ensure geometry info is up to date
            try:
                self.root.update_idletasks()
            except Exception:
                pass

            root_w = max(1, self.root.winfo_width())
            root_h = max(1, self.root.winfo_height())

            # Default to 70% of available width
            overlay_w = int(root_w * 0.7)

            # If there's a right panel, reserve its width
            right = getattr(self.view, 'right_container', None) or getattr(self.view, 'right_frame', None)
            if right:
                try:
                    rc_w = right.winfo_width()
                    if rc_w and rc_w > 0:
                        overlay_w = max(200, root_w - rc_w)
                except Exception:
                    pass

            # Place overlay with explicit width/height (use place with width/height)
            try:
                self.overlay.place(x=0, y=0, width=overlay_w, height=root_h)
            except Exception:
                # fallback to configure + place
                try:
                    self.overlay.configure(width=overlay_w, height=root_h)
                    self.overlay.place(x=0, y=0)
                except Exception:
                    pass

            # Ensure overlay does not shrink to fit children
            try:
                self.overlay.pack_propagate(False)
            except Exception:
                pass

            # Force children to expand inside overlay
            try:
                if self.widget:
                    try:
                        self.widget.pack(fill="both", expand=True)
                    except Exception:
                        pass
            except Exception:
                pass

            # Bring overlay to front
            try:
                self.overlay.lift()
            except Exception:
                pass

            # Focus hint
            if self.widget and hasattr(self.widget, 'btn_cat_mode'):
                try:
                    self.widget.after(50, lambda: self.widget.btn_cat_mode.focus_set())
                except Exception:
                    pass
        except Exception:
            logger.exception("Error mostrando overlay")

    def hide(self):
        try:
            self.overlay.place_forget()
        except Exception:
            pass
        self._visible = False
        if callable(self.on_close):
            try:
                self.on_close()
            except Exception:
                logger.exception("Error ejecutando on_close callback")

    def set_ui_config(self, **kwargs):
        pass