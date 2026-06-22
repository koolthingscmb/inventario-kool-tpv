"""Vista de configuración del taller de producción (Backoffice).

Contenedor thin que gestiona los tabs y delega el contenido a:
- config_tab_colores.py
- config_tab_tallas.py
- config_tab_generos.py
- config_tab_matriz.py
- config_tab_menu.py
"""
import tkinter as tk
import customtkinter as ctk
from typing import Callable, Optional

from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.produccion.services.produccion_config_service import ProduccionConfigService
from kool_tpv.modulos.produccion.ui.subvistas.config_helper import cargar_config_produccion, get_font
from kool_tpv.modulos.produccion.ui.subvistas.config_tab_colores import ConfigTabColores
from kool_tpv.modulos.produccion.ui.subvistas.config_tab_tallas import ConfigTabTallas
from kool_tpv.modulos.produccion.ui.subvistas.config_tab_generos import ConfigTabGeneros
from kool_tpv.modulos.produccion.ui.subvistas.config_tab_matriz import ConfigTabMatriz
from kool_tpv.modulos.produccion.ui.subvistas.config_tab_menu import ConfigTabMenu
from kool_tpv.utils.config_loader import load_layout_config


class ProduccionConfigView:
    def __init__(self, parent, db: Database, on_cerrar: Optional[Callable] = None):
        self.parent = parent
        self.db = db
        self.on_cerrar = on_cerrar
        self.service = ProduccionConfigService(db)

        # Cargar configuración visual
        self.config = cargar_config_produccion()
        self._colors = self.config.get("colors", {})
        self._bg = self._colors.get("background", "#2c3e50")
        self._text = self._colors.get("text", "#ecf0f1")

        # Layout config y keyboard manager para VirtualNavList
        self._layout_config = load_layout_config()
        root = parent.winfo_toplevel()
        self._km = getattr(root, 'keyboard_manager', None)

        # Estado de tabs
        self._main_tabs = ["CATÁLOGO", "MATRIZ", "MENÚ", "TIPOS"]
        self._sub_tabs = ["COLORES", "TALLAS", "GÉNEROS"]
        self._current_main_tab = None
        self._current_sub_tab = None
        self._main_tab_labels = {}
        self._sub_tab_labels = {}
        self._sub_tab_bar = None
        self._current_tab_obj = None

        # Frame principal
        self.frame = tk.Frame(parent, bg=self._bg)
        self.frame.pack(fill=tk.BOTH, expand=True)

        # Título y botón cerrar
        self._crear_cabecera()

        # Barra de tabs principales
        self._crear_tab_bar()

        # Barra de sub-tabs (solo visible para CATÁLOGO)
        self._crear_sub_tab_bar()

        # Frame de contenido
        self._content_frame = tk.Frame(self.frame, bg=self._bg)
        self._content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(5, 10))

        # Seleccionar primer tab
        self._select_main_tab("CATÁLOGO")

    def _crear_cabecera(self):
        cabecera = tk.Frame(self.frame, bg=self._bg, height=50)
        cabecera.pack(fill="x", padx=20, pady=(10, 0))
        cabecera.pack_propagate(False)

        titulo = tk.Label(
            cabecera,
            text="CONFIGURACIÓN DEL TALLER",
            font=get_font(self.config, "title"),
            fg=self._text,
            bg=self._bg
        )
        titulo.pack(side="left", pady=8)

        btn_cerrar = ctk.CTkButton(
            cabecera,
            text="✕",
            width=40,
            height=40,
            fg_color="#e74c3c",
            hover_color="#c0392b",
            command=self._on_cerrar
        )
        btn_cerrar.pack(side="right", pady=5)

    # --- Sistema de tabs ---

    _TAB_BG_NORMAL = "#34495e"
    _TAB_BG_SELECTED = "#3498db"
    _TAB_BG_SUB_NORMAL = "#2c3e50"
    _TAB_BG_SUB_SELECTED = "#9b59b6"

    def _crear_tab_bar(self):
        bar = tk.Frame(self.frame, bg=self._bg, height=36)
        bar.pack(fill="x", padx=20, pady=(5, 0))
        bar.pack_propagate(False)

        for tab_name in self._main_tabs:
            lbl = tk.Label(
                bar, text=tab_name, font=get_font(self.config, "label"),
                fg=self._text, bg=self._TAB_BG_NORMAL,
                padx=20, pady=6, cursor="hand2"
            )
            lbl.pack(side="left", padx=(0, 4))
            lbl.bind("<Button-1>", lambda e, name=tab_name: self._select_main_tab(name))
            self._main_tab_labels[tab_name] = lbl

    def _crear_sub_tab_bar(self):
        self._sub_tab_bar = tk.Frame(self.frame, bg=self._bg, height=30)
        self._sub_tab_bar.pack_propagate(False)

        for sub_name in self._sub_tabs:
            lbl = tk.Label(
                self._sub_tab_bar, text=sub_name, font=get_font(self.config, "label"),
                fg=self._text, bg=self._TAB_BG_SUB_NORMAL,
                padx=16, pady=5, cursor="hand2"
            )
            lbl.pack(side="left", padx=(0, 4))
            lbl.bind("<Button-1>", lambda e, name=sub_name: self._select_sub_tab(name))
            self._sub_tab_labels[sub_name] = lbl

    def _select_main_tab(self, tab_name):
        if self._current_main_tab == tab_name:
            return
        self._current_main_tab = tab_name

        for name, lbl in self._main_tab_labels.items():
            bg = self._TAB_BG_SELECTED if name == tab_name else self._TAB_BG_NORMAL
            lbl.configure(bg=bg)

        if tab_name == "CATÁLOGO":
            self._sub_tab_bar.pack(fill="x", padx=20, pady=(4, 0), before=self._content_frame)
            if not self._current_sub_tab:
                self._select_sub_tab("COLORES")
            else:
                self._load_sub_tab_content(self._current_sub_tab)
        else:
            self._sub_tab_bar.pack_forget()
            self._current_sub_tab = None
            if self._km:
                try:
                    self._km.set_active_list(None)
                except Exception:
                    pass
            self._clear_content()
            if tab_name == "MATRIZ":
                self._current_tab_obj = ConfigTabMatriz(
                    self._content_frame, self.service, self.config,
                    self._colors, self._km, self._layout_config)
            elif tab_name == "MENÚ":
                self._current_tab_obj = ConfigTabMenu(
                    self._content_frame, self.service, self.config,
                    self._colors, self._km, self._layout_config)
            elif tab_name == "TIPOS":
                lbl = tk.Label(self._content_frame, text="Configuración de Tipos y Costes (Próximamente)",
                               font=get_font(self.config, "label"), fg=self._text, bg=self._bg)
                lbl.pack(pady=40)
                self._current_tab_obj = None

    def _select_sub_tab(self, sub_name):
        if self._current_sub_tab == sub_name:
            return
        self._current_sub_tab = sub_name

        for name, lbl in self._sub_tab_labels.items():
            bg = self._TAB_BG_SUB_SELECTED if name == sub_name else self._TAB_BG_SUB_NORMAL
            lbl.configure(bg=bg)

        self._load_sub_tab_content(sub_name)

    def _load_sub_tab_content(self, sub_name):
        self._clear_content()
        kwargs = dict(
            parent=self._content_frame,
            service=self.service,
            config=self.config,
            colors=self._colors,
            km=self._km,
            layout_config=self._layout_config,
        )
        if sub_name == "COLORES":
            self._current_tab_obj = ConfigTabColores(**kwargs)
        elif sub_name == "TALLAS":
            self._current_tab_obj = ConfigTabTallas(**kwargs)
        elif sub_name == "GÉNEROS":
            self._current_tab_obj = ConfigTabGeneros(**kwargs)
        self.frame.after(50, self._refresh_current_nav)

    def _clear_content(self):
        for child in self._content_frame.winfo_children():
            child.destroy()
        self._current_tab_obj = None

    def _refresh_current_nav(self):
        if self._current_tab_obj and hasattr(self._current_tab_obj, 'refresh_nav'):
            self._current_tab_obj.refresh_nav()

    def _on_cerrar(self):
        if self.on_cerrar:
            self.on_cerrar()
        self.frame.destroy()
