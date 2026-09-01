"""Vista principal de configuración UI (Master Config).

Copia el patrón de ProduccionConfigView: barra de tabs principales y contenido
dinámico por tab. No usa base de datos, solo el UIConfigService.
"""
import tkinter as tk
import customtkinter as ctk
from typing import Callable, Optional
from kool_tpv.modulos.config.ui.services.ui_config_service import UIConfigService
from kool_tpv.utils.config_loader import load_colors


class ConfigTabView:
    """Vista con tabs para gestionar colores, tipografía, botones, layout, etc."""

    _MAIN_TABS = [
        "COLORES", "BOTONES",
        "DIÁLOGOS", "TOASTS", "NAV LIST", "SISTEMA"
    ]
    _TAB_BG_NORMAL = "#34495e"
    _TAB_BG_SELECTED = "#3498db"

    def __init__(self, parent, on_cerrar: Optional[Callable] = None):
        self.parent = parent
        self.on_cerrar = on_cerrar
        self.service = UIConfigService()
        
        # Paleta dinámica del módulo config
        try:
            colors = load_colors('config')
            self._TAB_BG_SELECTED = colors.get('buttons', {}).get('primary', {}).get('bg', '#FF9800')
            self._TAB_BG_NORMAL = colors.get('buttons', {}).get('secondary', {}).get('bg', '#643300')
        except Exception:
            self._TAB_BG_SELECTED = "#FF9800"
            self._TAB_BG_NORMAL = "#643300"

        self._bg = "#2c3e50"
        self._text = "#ecf0f1"
        self._current_tab = None
        self._tab_labels = {}
        self._current_tab_obj = None

        self.frame = tk.Frame(parent, bg=self._bg)
        self.frame.pack(fill=tk.BOTH, expand=True)

        self._crear_cabecera()
        self._crear_tab_bar()

        self._content_frame = tk.Frame(self.frame, bg=self._bg)
        self._content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(5, 10))

        self._select_tab("COLORES")

    def _crear_cabecera(self):
        cabecera = tk.Frame(self.frame, bg=self._bg, height=50)
        cabecera.pack(fill="x", padx=20, pady=(10, 0))
        cabecera.pack_propagate(False)

        tk.Label(
            cabecera,
            text="CONFIGURACIÓN UI",
            font=("Helvetica", 18, "bold"),
            fg=self._text,
            bg=self._bg
        ).pack(side="left", pady=8)

        ctk.CTkButton(
            cabecera,
            text="✕",
            width=40,
            height=40,
            fg_color="#e74c3c",
            hover_color="#c0392b",
            command=self._on_cerrar
        ).pack(side="right", pady=5)

    def _crear_tab_bar(self):
        bar = tk.Frame(self.frame, bg=self._bg, height=36)
        bar.pack(fill="x", padx=20, pady=(5, 0))
        bar.pack_propagate(False)

        for tab_name in self._MAIN_TABS:
            lbl = tk.Label(
                bar, text=tab_name, font=("Helvetica", 12, "bold"),
                fg=self._text, bg=self._TAB_BG_NORMAL,
                padx=16, pady=6, cursor="hand2"
            )
            lbl.pack(side="left", padx=(0, 4))
            lbl.bind("<Button-1>", lambda e, name=tab_name: self._select_tab(name))
            self._tab_labels[tab_name] = lbl

    def _select_tab(self, tab_name: str):
        if self._current_tab == tab_name:
            return
        self._current_tab = tab_name

        for name, lbl in self._tab_labels.items():
            bg = self._TAB_BG_SELECTED if name == tab_name else self._TAB_BG_NORMAL
            lbl.configure(bg=bg)

        self._clear_content()

        if tab_name == "COLORES":
            from kool_tpv.modulos.config.ui.tabs.colors_tab import ColorsTab
            self._current_tab_obj = ColorsTab(self._content_frame, self.service)
        elif tab_name == "BOTONES":
            from kool_tpv.modulos.config.ui.tabs.buttons_tab import ButtonsTab
            self._current_tab_obj = ButtonsTab(self._content_frame, self.service)
        elif tab_name == "DIÁLOGOS":
            from kool_tpv.modulos.config.ui.tabs.dialogs_tab import DialogsTab
            self._current_tab_obj = DialogsTab(self._content_frame, self.service)
        elif tab_name == "TOASTS":
            from kool_tpv.modulos.config.ui.tabs.toasts_tab import ToastsTab
            self._current_tab_obj = ToastsTab(self._content_frame, self.service)
        elif tab_name == "NAV LIST":
            from kool_tpv.modulos.config.ui.tabs.nav_list_tab import NavListTab
            self._current_tab_obj = NavListTab(self._content_frame, self.service)
        elif tab_name == "SISTEMA":
            from kool_tpv.modulos.config.ui.tabs.sistema_tab import SistemaTab
            self._current_tab_obj = SistemaTab(self._content_frame, self.service)
        else:
            self._mostrar_placeholder(tab_name)

    def _mostrar_placeholder(self, texto: str):
        tk.Label(
            self._content_frame,
            text=f"{texto}\n(Próximamente)",
            font=("Helvetica", 16, "bold"),
            fg=self._text,
            bg=self._bg,
            justify="center"
        ).pack(expand=True)

    def _clear_content(self):
        for child in self._content_frame.winfo_children():
            child.destroy()
        self._current_tab_obj = None

    def _on_cerrar(self):
        if self.on_cerrar:
            self.on_cerrar()
        self.frame.destroy()
