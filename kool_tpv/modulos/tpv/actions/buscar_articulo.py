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
        # Place overlay off-screen initially so it's pre-created but invisible
        try:
            self.overlay.place(x=-9999, y=-9999, width=1, height=1)
        except Exception:
            try:
                self.overlay.place(x=0, y=0, width=1, height=1)
            except Exception:
                pass

        # Create a close/power button for this overlay (so it shows the global power position)
        try:
            from kool_tpv.utils.global_buttons import create_global_close_button
        except Exception:
            create_global_close_button = None

        if create_global_close_button is not None:
            try:
                self.close_btn = create_global_close_button(self.overlay, command=self.hide)
            except Exception:
                self.close_btn = None
                logger.exception('Error creando close_btn en BuscarArticuloPanel')

            if getattr(self, 'close_btn', None) is not None:
                try:
                    app_root = getattr(self.view, 'parent', None) or getattr(self.view, 'root', None) or self.root
                except Exception:
                    app_root = None

                # NOTE: Power handler registration removed from __init__
                # It's now only registered in show() to avoid polluting the stack
                # with handlers from components that aren't visible yet

                # Prefer central dispatcher for the button if available
                try:
                    if app_root is not None and hasattr(app_root, '_dispatch_power'):
                        self.close_btn.configure(command=app_root._dispatch_power)
                except Exception:
                    pass

                # Ensure we unregister the handler when the overlay is destroyed
                try:
                    def _on_destroy(event=None):
                        try:
                            if app_root is not None and hasattr(app_root, 'unregister_power_handler'):
                                try:
                                    app_root.unregister_power_handler(owner=self)
                                    logger.info('BuscarArticuloPanel: power handler desregistrado en destroy')
                                except Exception:
                                    logger.exception('Error desregistrando power handler en destroy')
                        except Exception:
                            pass

                    try:
                        if getattr(self, 'overlay', None) is not None:
                            self.overlay.bind('<Destroy>', _on_destroy)
                    except Exception:
                        pass
                except Exception:
                    logger.exception('Error vinculando Destroy para desregistro en BuscarArticuloPanel')

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

            # Force geometry and paint before lifting to avoid flash
            try:
                self.overlay.update_idletasks()
            except Exception:
                pass

            try:
                self.overlay.lift()
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

            # Re-register power handler when shown to ensure this overlay has
            # precedence over other handlers while visible.
            try:
                app_root = getattr(self, 'root', None) or getattr(self.view, 'root', None) or getattr(self.view, 'parent', None)
                if app_root is not None and hasattr(app_root, 'register_power_handler'):
                    try:
                        app_root.register_power_handler(self.hide, owner=self)
                        logger.info('BuscarArticuloPanel: power handler (re)registrado en show')
                    except Exception:
                        logger.exception('BuscarArticuloPanel: error re-registrando power handler en show')
            except Exception:
                pass

            # Ensure global floating power (if any) remains on top
            try:
                app_root = getattr(self, 'root', None) or getattr(self.view, 'root', None) or getattr(self.view, 'parent', None)
                if app_root is not None and hasattr(app_root, 'power_floating'):
                    try:
                        app_root.power_floating.lift()
                    except Exception:
                        pass
            except Exception:
                pass

            # Position close button to match global power button location
            try:
                if getattr(self, 'close_btn', None) is not None:
                    app_root = self.root
                    nav = getattr(app_root, 'nav_frame', None)
                    try:
                        if app_root is not None:
                            app_root.update_idletasks()
                    except Exception:
                        pass
                    try:
                        self.overlay.update_idletasks()
                    except Exception:
                        pass

                    if nav is not None:
                        ov_x = self.overlay.winfo_rootx()
                        ov_y = self.overlay.winfo_rooty()
                        try:
                            pb = getattr(app_root, 'power_button', None)
                            if pb is not None:
                                pb_rootx = pb.winfo_rootx()
                                pb_rooty = pb.winfo_rooty()
                                rel_x = pb_rootx - ov_x
                                rel_y = pb_rooty - ov_y
                            else:
                                nav_x = nav.winfo_rootx()
                                nav_y = nav.winfo_rooty()
                                rel_x = 12 + (nav_x - ov_x)
                                rel_y = 12 + (nav_y - ov_y)
                        except Exception:
                            try:
                                nav_x = nav.winfo_rootx()
                                nav_y = nav.winfo_rooty()
                                rel_x = 12 + (nav_x - ov_x)
                                rel_y = 12 + (nav_y - ov_y)
                            except Exception:
                                rel_x, rel_y = 12, 12
                        try:
                            self.close_btn.place(x=rel_x, y=rel_y)
                            self.close_btn.lift()
                        except Exception:
                            try:
                                self.close_btn.place(x=12, y=12)
                            except Exception:
                                pass
            except Exception:
                logger.exception('Error posicionando close_btn en BuscarArticuloPanel')

        except Exception:
            logger.exception("Error mostrando overlay")

    def hide(self):
        # Instead of removing the overlay from the layout (which causes a redraw
        # and may produce a visible flash), simply lower it and keep it placed
        # off-screen for fast reuse.
        try:
            # Lower under other widgets
            self.overlay.lower()
            # Move off-screen to ensure no accidental catches
            try:
                self.overlay.place(x=-9999, y=-9999, width=1, height=1)
            except Exception:
                pass
        except Exception:
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

        # Indicate the action was handled so the global dispatcher does not
        # run the app-level fallback (`close_app`). Returning True signals
        # the dispatcher to stop propagation.
        try:
            # Unregister handler now that overlay is hidden
            try:
                app_root = getattr(self, 'root', None) or getattr(self.view, 'root', None) or getattr(self.view, 'parent', None)
                if app_root is not None and hasattr(app_root, 'unregister_power_handler'):
                    try:
                        app_root.unregister_power_handler(owner=self)
                    except Exception:
                        logger.exception('BuscarArticuloPanel: error desregistrando power handler en hide')
            except Exception:
                pass

            return True
        except Exception:
            return True

    def set_ui_config(self, **kwargs):
        pass