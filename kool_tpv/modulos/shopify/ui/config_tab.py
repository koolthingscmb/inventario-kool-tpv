"""Shopify Configuration Tab.

Handles the UI for Shopify settings including General, IA, Sources, and Logs.
Follows the pattern from ProduccionConfigView.
"""
import tkinter as tk
import customtkinter as ctk
import logging
from typing import Dict, Any, List, Optional

from kool_tpv.utils.factories.button_factory import ButtonFactory
from kool_tpv.utils.config_loader import load_colors
from kool_tpv.utils.widgets.notificaciones import show_success, show_error
from kool_tpv.modulos.shopify.services.openai_service import OpenAIService
from kool_tpv.modulos.shopify.services.sources.source_manager import SourceManager
from kool_tpv.modulos.shopify.shopify_prompts_repository import ShopifyPromptsRepository
from kool_tpv.utils.widgets.virtual_nav_list import VirtualNavList
from kool_tpv.utils.dialogs.multi_select_dialog import show_multi_select_dialog
from kool_tpv.utils.widgets.tag_selector import TagSelector

# Componentes y Tabs independientes
from kool_tpv.modulos.shopify.ui.tabs.prompt_editor_component import PromptEditorComponent
from kool_tpv.modulos.shopify.ui.tabs.general_tab import GeneralTab
from kool_tpv.modulos.shopify.ui.tabs.tipos_tab import TiposTab
from kool_tpv.modulos.shopify.ui.tabs.ia_tab import IATab
from kool_tpv.modulos.shopify.ui.tabs.ia_tonos_tab import IATonosTab
from kool_tpv.modulos.shopify.ui.tabs.ia_beneficios_tab import IABeneficiosTab
from kool_tpv.modulos.shopify.ui.tabs.fuentes_tab import FuentesTab
from kool_tpv.modulos.shopify.ui.tabs.logs_tab import LogsTab

logger = logging.getLogger(__name__)

class ShopifyConfigTab:
    """Panel de configuración de Shopify con pestañas superiores y footer de acciones."""

    def __init__(self, parent, service):
        self.parent = parent
        self.service = service
        self.db = service.db
        
        # Inicializar el gestor de fuentes dinámicas
        self.source_manager = SourceManager(self.db)
        
        # Repositorio de prompts IA (tabla shopify_prompts)
        self.prompts_repo = ShopifyPromptsRepository(self.db)
        
        # Cargar colores del módulo Shopify
        try:
            self._colors_cfg = load_colors('shopify')
            self._primary_color = self._colors_cfg.get('primary', '#00A4DF')
            self._secondary_color = self._colors_cfg.get('secondary', '#3498db')
            self._bg_color = self._colors_cfg.get('background', '#000000')
            self._bg_medium = self._colors_cfg.get('bg_medium', '#1a1a1a')
            
            # Paletas de botones para tabs
            btn_colors = self._colors_cfg.get('buttons', {})
            self._tab_bg_selected = btn_colors.get('primary', {}).get('bg', '#00A4DF')
            self._tab_bg_normal = btn_colors.get('secondary', {}).get('bg', '#3498db')
            self._tab_text_selected = btn_colors.get('primary', {}).get('text', '#FFFFFF')
            self._tab_text_normal = btn_colors.get('secondary', {}).get('text', '#FFFFFF')
        except Exception:
            self._primary_color = '#00A4DF'
            self._secondary_color = '#3498db'
            self._bg_color = '#000000'
            self._bg_medium = '#1a1a1a'
            self._tab_bg_selected = '#00A4DF'
            self._tab_bg_normal = '#3498db'
            self._tab_text_selected = '#FFFFFF'
            self._tab_text_normal = '#FFFFFF'

        self._current_tab = None
        self._tab_labels = {}
        self._tabs = ["GENERAL", "TIPOS", "IA", "IA PROMPTS", "IA TONOS", "IA BENEFICIOS", "FUENTES", "LOGS"]

        # Diccionario para almacenar los widgets de entrada
        self.widgets = {}
        # Cargar configuración desde la BD
        self._config = self.service.get_config()

        # Main frame
        self.frame = tk.Frame(parent, bg=self._bg_color)
        self.frame.pack(fill=tk.BOTH, expand=True)

        # Tab bar
        self._create_tab_bar()

        # Content area
        self._content_container = tk.Frame(self.frame, bg=self._bg_color)
        self._content_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=(10, 0))
        
        # Frame scrollable para pestañas normales
        self._content_frame = ctk.CTkScrollableFrame(self._content_container, fg_color="transparent")
        self._content_frame.pack(fill=tk.BOTH, expand=True)

        # --- Inicializar Componentes ---
        self._prompt_editor = PromptEditorComponent(
            self._content_frame, self.db, self.prompts_repo,
            self._primary_color, self._secondary_color, self._bg_color, self._bg_medium,
            self._tab_bg_selected, self._tab_bg_normal, self._tab_text_selected, self._tab_text_normal
        )

        # --- Inicializar pestañas independientes ---
        self._general_tab = GeneralTab(self._content_frame, self.db, self._config, self._bg_color, self._primary_color, self._secondary_color)
        self._ia_tab = IATab(self._content_frame, self.db, self._config, self._bg_color, self._primary_color, self._secondary_color)
        self._ia_tonos_tab = IATonosTab(self._content_frame, self.db, self._primary_color, self._bg_color, self._bg_medium)
        self._ia_beneficios_tab = IABeneficiosTab(self._content_frame, self.db, self._primary_color, self._bg_color, self._bg_medium)
        self._fuentes_tab = FuentesTab(self._content_frame, self.db, self._config, self.source_manager, self.service, self._primary_color, self._secondary_color, self._bg_color, self._bg_medium)
        self._logs_tab = LogsTab(self._content_container, self.service, self._bg_color)
        
        self._tipos_tab = TiposTab(
            self._content_frame, self.db, self._config, 
            self._primary_color, self._secondary_color, self._bg_color, self._bg_medium,
            self._tab_bg_selected, self._tab_bg_normal, self._tab_text_selected, self._tab_text_normal,
            self.prompts_repo
        )
        self._tipos_tab.render_prompt_editor_callback = self._prompt_editor.render

        # Footer area for persistent buttons
        self._footer_frame = tk.Frame(self.frame, bg=self._bg_medium, height=70)
        self._footer_frame.pack(side="bottom", fill="x")
        self._footer_frame.pack_propagate(False)
        self._render_footer()

        # Select first tab
        self._select_tab("GENERAL")

    def _create_tab_bar(self):
        """Crea la barra de pestañas superior."""
        bar = tk.Frame(self.frame, bg=self._bg_color, height=45)
        bar.pack(fill="x", padx=20, pady=(15, 0))
        bar.pack_propagate(False)

        for tab_name in self._tabs:
            lbl = tk.Label(
                bar, text=tab_name, font=("Helvetica", 11, "bold"),
                fg=self._tab_text_normal, bg=self._tab_bg_normal,
                padx=25, pady=10, cursor="hand2"
            )
            lbl.pack(side="left", padx=(0, 5))
            lbl.bind("<Button-1>", lambda e, name=tab_name: self._select_tab(name))
            self._tab_labels[tab_name] = lbl

    def _select_tab(self, tab_name: str):
        """Cambia entre pestañas."""
        if self._current_tab == tab_name:
            return
        
        # Actualizar visual de pestañas
        for name, lbl in self._tab_labels.items():
            if name == tab_name:
                lbl.configure(bg=self._tab_bg_selected, fg=self._tab_text_selected)
            else:
                lbl.configure(bg=self._tab_bg_normal, fg=self._tab_text_normal)
        
        self._current_tab = tab_name
        self._clear_content()
        self.widgets.clear()
        self._render_footer()
        
        # Manejo especial para LOGS para usar VirtualNavList sin doble scroll
        if tab_name == "LOGS":
            self._content_frame.pack_forget()
            self._logs_tab.render()
        else:
            self._content_frame.pack(fill=tk.BOTH, expand=True)
            if tab_name == "GENERAL":
                self._general_tab.render()
            elif tab_name == "TIPOS":
                self._tipos_tab.render()
            elif tab_name == "IA":
                self._ia_tab.render()
            elif tab_name == "FUENTES":
                self._fuentes_tab.render()
            elif tab_name == "IA PROMPTS":
                self._render_ia_prompts()
            elif tab_name == "IA TONOS":
                self._ia_tonos_tab.render()
            elif tab_name == "IA BENEFICIOS":
                self._ia_beneficios_tab.render()

    def _harvest_widgets(self):
        """Recoge los valores de los widgets actuales y los guarda en self._config."""
        pass

    def _clear_content(self):
        """Limpia el área de contenido."""
        try:
            for child in self._content_frame.winfo_children():
                child.destroy()
            for child in self._content_container.winfo_children():
                if child != self._content_frame:
                    child.destroy()
        except Exception:
            pass

    def _render_footer(self):
        """Renderiza los botones en el footer según la pestaña activa."""
        for child in self._footer_frame.winfo_children():
            child.destroy()

        style_solid = {
            "corner_radius": 10,
            "border_width": 0,
            "font": ("Roboto-SemiBold", 16)
        }

        if self._current_tab in ["GENERAL", "TIPOS", "IA", "IA PROMPTS", "IA TONOS", "IA BENEFICIOS", "FUENTES"]:
            palette = self._colors_cfg.get("buttons", {}).get("primary", {})
            btn_save = ButtonFactory.create_button(
                self._footer_frame, text="APLICAR CAMBIOS",
                color=palette.get("bg", self._primary_color),
                hover_color=palette.get("hover", self._primary_color),
                text_color=palette.get("text", "#000000"),
                command=self._on_save,
                width=220, height=45,
                **style_solid
            )
            btn_save.pack(side="right", padx=20, pady=12)

            if self._current_tab == "IA":
                palette_sec = self._colors_cfg.get("buttons", {}).get("secondary", {})
                btn_test = ButtonFactory.create_button(
                    self._footer_frame, text="PROBAR CONEXIÓN",
                    color=palette_sec.get("bg", self._secondary_color),
                    hover_color=palette_sec.get("hover", self._secondary_color),
                    text_color=palette_sec.get("text", "#FFFFFF"),
                    command=self._ia_tab._on_test_ia,
                    width=200, height=45,
                    **style_solid
                )
                btn_test.pack(side="right", padx=0, pady=12)

        elif self._current_tab == "LOGS":
            palette = self._colors_cfg.get("buttons", {}).get("primary", {})
            btn_refresh = ButtonFactory.create_button(
                self._footer_frame, text="REFRESCAR",
                color=palette.get("bg", self._primary_color),
                hover_color=palette.get("hover", self._primary_color),
                text_color=palette.get("text", "#000000"),
                command=self._logs_tab.refresh,
                width=180, height=45,
                **style_solid
            )
            btn_refresh.pack(side="left", padx=20, pady=12)

            palette_acc = self._colors_cfg.get("buttons", {}).get("accent", {})
            btn_clear = ButtonFactory.create_button(
                self._footer_frame, text="LIMPIAR",
                color=palette_acc.get("bg", "#f1c40f"),
                hover_color=palette_acc.get("hover", "#f39c12"),
                text_color=palette_acc.get("text", "#000000"),
                command=self._logs_tab.clear,
                width=180, height=45,
                **style_solid
            )
            btn_clear.pack(side="right", padx=20, pady=12)

    def _create_section_header(self, parent, text: str):
        """Crea un header de sección con el color Primary."""
        f = tk.Frame(parent, bg=self._bg_color)
        f.pack(fill="x", pady=(10, 20))
        lbl = tk.Label(f, text=text, font=("Helvetica", 14, "bold"), fg=self._primary_color, bg=self._bg_color, anchor="w")
        lbl.pack(side="left")
        line = tk.Frame(f, bg=self._primary_color, height=2)
        line.pack(side="left", fill="x", expand=True, padx=(15, 0), pady=(2, 0))

    def _render_ia_prompts(self):
        """Pestaña de prompts genéricos."""
        self._create_section_header(self._content_frame, "PROMPTS DE IA (GENÉRICOS)")
        self._prompt_editor.render(self._content_frame, tipo_id=None)

    def _on_save(self):
        # Recoger datos de pestañas y componentes
        edits = {}
        nom_edits = {}
        self._prompt_editor.harvest_all(edits, nom_edits)
        
        self._ia_tab.harvest(self._config)
        self._general_tab.harvest(self._config)
        self._fuentes_tab.harvest(self._config)

        ok = self.service.save_config(self._config)
        
        # Guardar Tonos y Beneficios
        prompts_ok = self._ia_tonos_tab.save() and self._ia_beneficios_tab.save()
        
        # Guardar Prompts editados
        for (clave, t_id), texto in edits.items():
            prompts_ok = self.prompts_repo.save_texto(clave, texto, t_id) and prompts_ok
        
        for clave, nombre in nom_edits.items():
            prompts_ok = self.prompts_repo.save_nombre(clave, nombre) and prompts_ok

        # Guardar el tipo actual si estamos en esa pestaña
        if self._current_tab == "TIPOS":
            self._tipos_tab.save_tipo_actual()

        if ok and prompts_ok:
            self.service.add_log("SAVE_CONFIG", "success", "Configuración actualizada")
            show_success(self.frame, "Configuración guardada.")
        else:
            self.service.add_log("SAVE_CONFIG", "error", "Fallo al guardar")
            show_error(self.frame, "Error al guardar.")
