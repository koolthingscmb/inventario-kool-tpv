import tkinter as tk
import customtkinter as ctk
import logging
from typing import Dict, Any, Optional
from kool_tpv.modulos.shopify.services.openai_service import OpenAIService
from kool_tpv.utils.widgets.notificaciones import show_success, show_error

logger = logging.getLogger(__name__)

class IATab:
    """Gestiona la configuración de las APIs de IA (OpenAI y Google Books)."""

    def __init__(self, parent, db, config, bg_color, primary_color, secondary_color):
        self.parent = parent
        self.db = db
        self._config = config
        self._bg_color = bg_color
        self._primary_color = primary_color
        self._secondary_color = secondary_color
        self.widgets = {}

    def render(self):
        """Dibuja el formulario de configuración de IA."""
        grid_container = tk.Frame(self.parent, bg=self._bg_color)
        grid_container.pack(fill="x", padx=10)
        grid_container.columnconfigure(1, weight=1)

        # Modelo de IA
        tk.Label(grid_container, text="Modelo de IA:", font=("Helvetica", 12), 
                 fg="#FFFFFF", bg=self._bg_color, anchor="e", width=25).grid(row=0, column=0, padx=(0, 20), pady=15, sticky="e")
        
        current_model = self._config.get("ia_model", "gpt-4o-mini")
        combo = ctk.CTkOptionMenu(grid_container, values=["gpt-4o-mini", "gpt-4o"], height=40, width=250)
        combo.set(current_model)
        combo.grid(row=0, column=1, sticky="w", pady=15)
        self.widgets["ia_model"] = combo

        # OpenAI API Key
        tk.Label(grid_container, text="OpenAI API Key:", font=("Helvetica", 12), 
                 fg="#FFFFFF", bg=self._bg_color, anchor="e", width=25).grid(row=1, column=0, padx=(0, 20), pady=15, sticky="e")
        
        val_key = self._config.get("ia_api_key", "")
        entry = ctk.CTkEntry(grid_container, placeholder_text="sk-...", height=40, show="*", font=("Helvetica", 12))
        entry.insert(0, val_key)
        entry.grid(row=1, column=1, sticky="ew", pady=15)
        self.widgets["ia_api_key"] = entry

        # Google Books API Key
        tk.Label(grid_container, text="Google Books API Key:", font=("Helvetica", 12), 
                 fg="#FFFFFF", bg=self._bg_color, anchor="e", width=25).grid(row=2, column=0, padx=(0, 20), pady=15, sticky="e")
        
        val_google = self._config.get("google_api_key", "")
        entry_g = ctk.CTkEntry(grid_container, placeholder_text="AIza...", height=40, show="*", font=("Helvetica", 12))
        entry_g.insert(0, val_google)
        entry_g.grid(row=2, column=1, sticky="ew", pady=15)
        self.widgets["google_api_key"] = entry_g

        # Botón de Test
        btn_test = ctk.CTkButton(
            grid_container, text="TEST CONEXIÓN OPENAI", height=40,
            fg_color=self._secondary_color, font=("Helvetica", 12, "bold"),
            command=self._on_test_ia
        )
        btn_test.grid(row=3, column=1, sticky="w", pady=20)

    def _on_test_ia(self):
        """Prueba la conexión con OpenAI usando los valores actuales del formulario."""
        api_key = self.widgets["ia_api_key"].get().strip()
        model = self.widgets["ia_model"].get()
        
        if not api_key:
            show_error(self.parent, "Introduce una API Key antes de probar.")
            return

        ai_service = OpenAIService(api_key, model)
        success, message = ai_service.test_connection()
        
        if success:
            show_success(self.parent, f"Conexión con OpenAI correcta: {message}")
        else:
            show_error(self.parent, f"Error en conexión OpenAI: {message}")

    def harvest(self, config_dict: Dict[str, Any]):
        """Recoge los valores de los widgets y los mete en el diccionario de config."""
        for key, widget in self.widgets.items():
            if widget.winfo_exists():
                config_dict[key] = widget.get().strip()
