import tkinter as tk
import customtkinter as ctk
import logging
from typing import List, Dict, Any, Optional
from kool_tpv.utils.widgets.virtual_nav_list import VirtualNavList
from kool_tpv.utils.widgets.notificaciones import show_success, show_error

logger = logging.getLogger(__name__)

class LogsTab:
    """Muestra el historial de eventos de Shopify."""

    def __init__(self, parent, service, bg_color):
        self.parent = parent
        self.service = service
        self._bg_color = bg_color
        self.nav_list = None

    def render(self):
        """Dibuja la lista de logs."""
        columnas = [
            ("fecha", 180, "FECHA"),
            ("accion", 120, "ACCIÓN"),
            ("resultado", 100, "ESTADO"),
            ("mensaje", 400, "DETALLE")
        ]
        
        # En el taller de producción se usa esta forma de instanciar
        self.nav_list = VirtualNavList(
            self.parent,
            columns=columnas,
            module_name="shopify"
        )
        self.nav_list.pack(fill=tk.BOTH, expand=True)
        self.refresh()

    def refresh(self):
        """Actualiza los datos de la lista."""
        try:
            logs = self.service.get_logs(limit=200)
            if self.nav_list:
                self.nav_list.set_items(logs)
        except Exception:
            logger.exception("Error refrescando logs en LogsTab")

    def clear(self):
        """Limpia el historial de la base de datos."""
        if self.service.clear_logs():
            show_success(self.parent, "Logs limpiados.")
            self.refresh()
        else:
            show_error(self.parent, "No se pudo limpiar el historial.")
