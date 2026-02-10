"""Controlador ligero para enlazar acciones UI del TPV.

Aquí conectamos el botón BUSCAR ARTÍCULO con el overlay implementado
en `actions.buscar_articulo.BuscarArticuloPanel`.
"""
from __future__ import annotations
import logging
from typing import Optional

try:
    from kool_tpv.modulos.tpv.actions.buscar_articulo import BuscarArticuloPanel
except Exception:
    BuscarArticuloPanel = None


class TpvController:
    """Controlador que conecta la vista TPV con handlers de acciones.

    Actualmente sólo conecta el botón de búsqueda para mostrar/ocultar
    el panel de 'buscar artículo'.
    """

    def __init__(self, view) -> None:
        self.view = view
        self.panel: Optional[BuscarArticuloPanel] = None
        self._attach()

    def _attach(self) -> None:
        try:
            logging.info("TpvController: attaching BuscarArticuloPanel")
            if BuscarArticuloPanel is None:
                return

            action_panel = getattr(self.view, "action_panel", None)
            if action_panel is None:
                return

            # Pass the whole view so the panel can position itself to
            # cover the nav_frame + action_panel (leaving the right column)
            try:
                self.panel = BuscarArticuloPanel(self.view)
            except Exception:
                # fallback to older signature accepting action_panel
                self.panel = BuscarArticuloPanel(action_panel)

            # Reconfigurar el botón de búsqueda para abrir el panel
            search_btn = getattr(self.view, "search_button", None)
            if search_btn is not None:
                try:
                    search_btn.configure(command=self.panel.show)
                    logging.info("TpvController: asignado command show() al search_button")
                except Exception:
                    # Fallback: intentar asignar via bind
                    try:
                        search_btn.bind("<Button-1>", lambda e: self.panel.show())
                        logging.info("TpvController: asignado bind <Button-1> al search_button")
                    except Exception:
                        logging.exception("TpvController: no se pudo vincular el search_button")
            # Wire panel article selection to carrito if view exposes carrito_service/ui
            try:
                if self.panel is not None:
                    def _on_selected(item):
                        try:
                            if getattr(self.view, 'carrito_service', None) is not None:
                                try:
                                    self.view.carrito_service.add_item(item)
                                except Exception:
                                    logging.exception('Error añadiendo item al carrito')
                            if getattr(self.view, 'carrito_ui', None) is not None:
                                try:
                                    self.view.carrito_ui.update_display()
                                except Exception:
                                    logging.exception('Error actualizando CarritoUI')
                        except Exception:
                            logging.exception('Error en panel on_article_selected wrapper')

                    try:
                        self.panel.on_article_selected = _on_selected
                    except Exception:
                        logging.exception('No se pudo asignar on_article_selected al panel')
            except Exception:
                logging.exception('Error wiring panel selection to carrito')
        except Exception:
            logging.exception("Error attach TpvController")
