"""Tab COLORES del panel de configuración UI."""
import tkinter as tk
from typing import Any, Dict

import customtkinter as ctk

from kool_tpv.modulos.config.ui.services.ui_config_service import UIConfigService
from kool_tpv.modulos.config.ui.config_tab_helper import section_title


class ColorsTab:
    """Muestra la paleta principal y los tokens de diseño."""

    def __init__(self, parent, service: UIConfigService):
        self.parent = parent
        self.service = service
        self._bg = "#2c3e50"
        self._fg = "#ecf0f1"
        self._data_colors: Dict[str, Any] = {}
        self._data_tokens: Dict[str, Any] = {}
        self._build()

    def _build(self):
        self._data_colors = self.service.cargar_json("colors_config")
        self._data_tokens = self.service.cargar_json("design_tokens")

        scroll = ctk.CTkScrollableFrame(self.parent, fg_color=self._bg)
        scroll.pack(fill=tk.BOTH, expand=True)

        self._render_core(scroll)
        self._separator(scroll)
        self._render_modules(scroll)
        self._separator(scroll)
        self._render_semantic(scroll)
        self._separator(scroll)
        self._render_tokens(scroll)

    def _color_row(self, parent, key: str, hex_color: str):
        row = tk.Frame(parent, bg=self._bg)
        row.pack(fill="x", padx=10, pady=2)

        try:
            preview = tk.Label(row, width=3, height=1, bg=hex_color, relief="solid", bd=1)
        except tk.TclError:
            preview = tk.Label(row, width=3, height=1, bg="#000000", relief="solid", bd=1)
        preview.pack(side="left", padx=(0, 8))

        tk.Label(
            row, text=key, font=("Helvetica", 10), fg=self._fg, bg=self._bg, width=35, anchor="w"
        ).pack(side="left", padx=(0, 8))

        tk.Label(
            row, text=hex_color, font=("Helvetica", 10, "bold"),
            fg="#95a5a6", bg=self._bg, width=10, anchor="w"
        ).pack(side="left")

    def _separator(self, parent):
        tk.Frame(parent, bg="#555555", height=2).pack(fill="x", padx=10, pady=15)

    def _render_core(self, parent):
        section_title(parent, "CORE — Fondos, Textos y Bordes", self._bg).pack(
            fill="x", pady=(10, 5), padx=10
        )
        for key, value in self._core_colors().items():
            self._color_row(parent, key, value)

    def _core_colors(self) -> Dict[str, str]:
        g = self._data_colors.get("global", {})
        layout = g.get("layout", {})
        core: Dict[str, str] = {}
        for k in ["background", "bg_dark", "bg_medium", "bg_sidebar", "dialog_bg", "bg_terminal"]:
            if k in g:
                core[f"Fondos.{k}"] = g[k]
        if "app_background" in layout:
            core["Fondos.app_background"] = layout["app_background"]
        if "sidebar_background" in layout:
            core["Fondos.sidebar_background"] = layout["sidebar_background"]
        for k in ["text_white", "text_gray", "text_disabled", "dialog_text", "text_matrix"]:
            if k in g:
                core[f"Textos.{k}"] = g[k]
        pob = layout.get("print_on_button", {})
        if "border" in pob:
            core["Bordes.print_on_button.border"] = pob["border"]
        return core

    def _render_modules(self, parent):
        section_title(parent, "MÓDULOS — TPV, Almacén, Producción, Clientes", self._bg).pack(
            fill="x", pady=(10, 5), padx=10
        )
        for key, value in self._module_colors().items():
            self._color_row(parent, key, value)

    def _module_colors(self) -> Dict[str, str]:
        modules: Dict[str, str] = {}
        for name in ["tpv", "almacen", "produccion", "clientes"]:
            data = self._data_colors.get(name, {})
            for key, value in data.items():
                if isinstance(value, str) and value.startswith("#"):
                    modules[f"{name}.{key}"] = value
                elif isinstance(value, dict):
                    self._flatten_colors(modules, f"{name}.{key}", value)
        return modules

    def _flatten_colors(self, out: Dict[str, str], prefix: str, data: Dict[str, Any]):
        for key, value in data.items():
            full = f"{prefix}.{key}" if prefix else key
            if isinstance(value, str) and value.startswith("#"):
                out[full] = value
            elif isinstance(value, dict):
                self._flatten_colors(out, full, value)

    def _render_semantic(self, parent):
        section_title(parent, "SEMÁNTICA — Success, Warning, Error, Info", self._bg).pack(
            fill="x", pady=(10, 5), padx=10
        )
        for key, value in self._semantic_colors().items():
            self._color_row(parent, key, value)

    def _semantic_colors(self) -> Dict[str, str]:
        g = self._data_colors.get("global", {})
        sem: Dict[str, str] = {}
        for k in ["success", "success_hover", "error", "error_hover",
                  "warning", "warning_hover", "info", "info_hover"]:
            if k in g:
                sem[k] = g[k]
        return sem

    def _render_tokens(self, parent):
        section_title(parent, "TOKENS de Diseño — design_tokens.json", self._bg).pack(
            fill="x", pady=(10, 5), padx=10
        )
        tokens: Dict[str, str] = {}
        self._flatten_colors(tokens, "", self._data_tokens)
        for key, value in tokens.items():
            self._color_row(parent, key, value)
