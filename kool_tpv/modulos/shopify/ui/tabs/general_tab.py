import tkinter as tk
import customtkinter as ctk
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class GeneralTab:
    """Gestiona la configuración general de conexión con Shopify."""

    def __init__(self, parent, db, config, bg_color, primary_color, secondary_color):
        self.parent = parent
        self.db = db
        self._config = config
        self._bg_color = bg_color
        self._primary_color = primary_color
        self._secondary_color = secondary_color
        self.widgets = {}

    def render(self):
        """Dibuja la interfaz con scroll propio."""
        scroll = ctk.CTkScrollableFrame(self.parent, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        grid_container = tk.Frame(scroll, bg=self._bg_color)
        grid_container.pack(fill="x", padx=10)
        grid_container.columnconfigure(1, weight=1)
        grid_container.columnconfigure(3, weight=1)

        fields = [
            (0, 0, "URL de la tienda:", "tienda.myshopify.com", "shop_url"),
            (0, 2, "Admin API Token:", "shpat_xxxxxxxxxxxxxxxxxxxx", "access_token"),
            (1, 0, "Location ID:", "12345678", "location_id"),
            (1, 2, "Versión API:", "2026-07", "api_version"),
            (2, 0, "Marca/Proveedor:", "Kool Things", "marca"),
            (2, 2, "URL guía de tallas:", "https://...", "link_guia"),
            (3, 0, "CDN botones género:", "https://cdn.shopify.com/.../files/", "botones_cdn"),
        ]

        for row, col_label, label, placeholder, key in fields:
            tk.Label(grid_container, text=label, font=("Helvetica", 12), fg="#FFFFFF", bg=self._bg_color, anchor="e").grid(row=row, column=col_label, padx=(0, 15), pady=15, sticky="e")
            val = self._config.get(key, "")
            if key == "api_version" and not val:
                val = "2026-07"
            entry = ctk.CTkEntry(grid_container, placeholder_text=placeholder, height=40, font=("Helvetica", 12))
            entry.insert(0, val)
            entry.grid(row=row, column=col_label + 1, sticky="ew", pady=15, padx=(0, 25))
            self.widgets[key] = entry

        self.widgets["sync_active"] = ctk.CTkCheckBox(
            grid_container, text="ACTIVAR SINCRONIZACIÓN AUTOMÁTICA", 
            font=("Helvetica", 12, "bold"), fg_color=self._primary_color, 
            hover_color=self._secondary_color, text_color="#FFFFFF", border_width=2
        )
        if self._config.get("sync_active"):
            self.widgets["sync_active"].select()
        else:
            self.widgets["sync_active"].deselect()
        self.widgets["sync_active"].grid(row=4, column=0, columnspan=4, sticky="w", pady=15)

    def harvest(self, config_dict: Dict[str, Any]):
        """Recoge los valores de los widgets y los mete en el diccionario de config."""
        for key, widget in self.widgets.items():
            if widget.winfo_exists():
                if isinstance(widget, ctk.CTkEntry):
                    config_dict[key] = widget.get().strip()
                elif isinstance(widget, ctk.CTkCheckBox):
                    config_dict[key] = bool(widget.get())
