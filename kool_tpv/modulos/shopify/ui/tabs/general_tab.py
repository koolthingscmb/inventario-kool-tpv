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
            (0, 2, "Admin API Token (Legacy):", "shpat_xxxxxxxxxxxxxxxxxxxx", "access_token"),
            (1, 0, "Client ID (Nueva App):", "ID de la app...", "client_id"),
            (1, 2, "Client Secret (Nueva App):", "Secreto de la app...", "client_secret"),
            (2, 0, "Location ID:", "12345678", "location_id"),
            (2, 2, "Versión API:", "2026-07", "api_version"),
            (3, 0, "Marca/Proveedor:", "Kool Things", "marca"),
            (3, 2, "URL guía de tallas:", "https://...", "link_guia"),
            (4, 0, "CDN botones género:", "https://cdn.shopify.com/.../files/", "botones_cdn"),
        ]

        for row, col_label, label, placeholder, key in fields:
            tk.Label(grid_container, text=label, font=("Helvetica", 12), fg="#FFFFFF", bg=self._bg_color, anchor="e").grid(row=row, column=col_label, padx=(0, 15), pady=15, sticky="e")
            val = self._config.get(key, "")
            if key == "api_version" and not val:
                val = "2026-07"
            
            # El secreto lo ponemos tipo password para que no se vea
            show = "*" if key == "client_secret" else None
            entry = ctk.CTkEntry(grid_container, placeholder_text=placeholder, height=40, font=("Helvetica", 12), show=show)
            entry.insert(0, val)
            entry.grid(row=row, column=col_label + 1, sticky="ew", pady=15, padx=(0, 25))
            self.widgets[key] = entry

        # Fila para Checkbox y Botón de prueba
        action_row = tk.Frame(grid_container, bg=self._bg_color)
        action_row.grid(row=5, column=0, columnspan=4, sticky="ew", pady=15)

        self.widgets["sync_active"] = ctk.CTkCheckBox(
            action_row, text="ACTIVAR SINCRONIZACIÓN AUTOMÁTICA", 
            font=("Helvetica", 12, "bold"), fg_color=self._primary_color, 
            hover_color=self._secondary_color, text_color="#FFFFFF", border_width=2
        )
        if self._config.get("sync_active"):
            self.widgets["sync_active"].select()
        else:
            self.widgets["sync_active"].deselect()
        self.widgets["sync_active"].pack(side="left")

        # Botón de prueba de conexión
        self._btn_test = ctk.CTkButton(
            action_row, text="PROBAR NUEVA CONEXIÓN (OAuth)", 
            font=("Helvetica", 11, "bold"), width=220, height=34,
            fg_color="#34495e", command=self._test_connection
        )
        self._btn_test.pack(side="right", padx=10)

    def _test_connection(self):
        """Prueba el flujo client_credentials y genera un token temporal."""
        from kool_tpv.utils.widgets.notificaciones import show_success, show_error
        import threading
        
        shop = self.widgets["shop_url"].get().strip()
        cid = self.widgets["client_id"].get().strip()
        sec = self.widgets["client_secret"].get().strip()
        
        if not shop or not cid or not sec:
            show_error(self.parent, "Rellena URL, Client ID y Secret para probar")
            return
            
        def work():
            from kool_tpv.modulos.shopify.services.shopify_metafields_service import ShopifyMetafieldsService
            # Usar una instancia temporal del servicio para probar
            # Pasamos un mock de DB o simplemente el servicio actualizandolo
            from kool_tpv.modulos.shopify.services.shopify_config_service import ShopifyConfigService
            
            # Simular config para el test
            test_cfg = self._config.copy()
            test_cfg.update({"shop_url": shop, "client_id": cid, "client_secret": sec})
            
            meta_service = ShopifyMetafieldsService(self.db)
            # Inyectar config de prueba
            meta_service.config_service.get_config = lambda: test_cfg
            
            token, err = meta_service.obtener_nuevo_access_token()
            
            def done():
                if token:
                    show_success(self.parent, f"¡CONECTADO!\nToken generado correctamente.\nCaduca en ~24h.")
                else:
                    show_error(self.parent, f"Fallo de conexión:\n{err}")
            self.parent.after(0, done)
            
        threading.Thread(target=work, daemon=True).start()

    def harvest(self, config_dict: Dict[str, Any]):
        """Recoge los valores de los widgets y los mete en el diccionario de config."""
        for key, widget in self.widgets.items():
            if widget.winfo_exists():
                if isinstance(widget, ctk.CTkEntry):
                    config_dict[key] = widget.get().strip()
                elif isinstance(widget, ctk.CTkCheckBox):
                    config_dict[key] = bool(widget.get())
