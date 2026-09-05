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
from kool_tpv.utils.widgets.virtual_nav_list import VirtualNavList

class ShopifyConfigTab:
    """Panel de configuración de Shopify con pestañas superiores y footer de acciones."""

    def __init__(self, parent, service):
        self.parent = parent
        self.service = service
        self.db = service.db
        
        # Inicializar el gestor de fuentes dinámicas
        self.source_manager = SourceManager()
        
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
        self._tabs = ["GENERAL", "IA", "FUENTES", "LOGS"]
        
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
        
        # Guardar valores actuales en el diccionario de configuración antes de destruir widgets
        self._harvest_widgets()
        
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
            self._render_logs()
        else:
            self._content_frame.pack(fill=tk.BOTH, expand=True)
            if tab_name == "GENERAL":
                self._render_general()
            elif tab_name == "IA":
                self._render_ia()
            elif tab_name == "FUENTES":
                self._render_fuentes()

    def _harvest_widgets(self):
        """Recoge los valores de los widgets actuales y los guarda en self._config."""
        for key, widget in self.widgets.items():
            try:
                if not widget.winfo_exists():
                    continue
                
                if isinstance(widget, ctk.CTkEntry):
                    self._config[key] = widget.get().strip()
                elif isinstance(widget, ctk.CTkCheckBox):
                    self._config[key] = bool(widget.get())
                elif isinstance(widget, ctk.CTkOptionMenu):
                    self._config[key] = widget.get()
            except Exception:
                continue

    def _clear_content(self):
        """Limpia el área de contenido."""
        try:
            for child in self._content_frame.winfo_children():
                child.destroy()
        except Exception:
            pass
        if hasattr(self, 'nav_list'):
            try:
                self.nav_list.destroy()
                del self.nav_list
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

        if self._current_tab in ["GENERAL", "IA", "FUENTES"]:
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
                    command=self._on_test_ia,
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
                command=self._on_refresh_logs,
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
                command=self._on_clear_logs,
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

    def _render_general(self):
        self._create_section_header(self._content_frame, "CONEXIÓN CON SHOPIFY")
        grid_container = tk.Frame(self._content_frame, bg=self._bg_color)
        grid_container.pack(fill="x", padx=10)
        grid_container.columnconfigure(1, weight=1)

        fields = [
            ("URL de la tienda:", "tienda.myshopify.com", "Ej: mitienda.myshopify.com", "shop_url"),
            ("Admin API Token:", "shpat_xxxxxxxxxxxxxxxxxxxx", "Token de la App Personalizada en Shopify", "access_token"),
            ("Location ID:", "12345678", "ID de la ubicación física para stock", "location_id")
        ]
        
        for i, (label, placeholder, tooltip, key) in enumerate(fields):
            tk.Label(grid_container, text=label, font=("Helvetica", 12), fg="#FFFFFF", bg=self._bg_color, anchor="e", width=25).grid(row=i, column=0, padx=(0, 20), pady=15, sticky="e")
            val = self._config.get(key, "")
            entry = ctk.CTkEntry(grid_container, placeholder_text=placeholder, height=40, font=("Helvetica", 12))
            entry.insert(0, val)
            entry.grid(row=i, column=1, sticky="ew", pady=15)
            self.widgets[key] = entry
            tk.Label(grid_container, text=tooltip, font=("Helvetica", 9, "italic"), fg="#666", bg=self._bg_color, anchor="w").grid(row=i, column=2, padx=(10, 0), sticky="w")

        self._create_section_header(self._content_frame, "ESTADO DEL SERVICIO")
        cb_frame = tk.Frame(self._content_frame, bg=self._bg_color)
        cb_frame.pack(fill="x", padx=10)
        
        self.widgets["sync_active"] = ctk.CTkCheckBox(cb_frame, text="ACTIVAR SINCRONIZACIÓN AUTOMÁTICA", font=("Helvetica", 12, "bold"), fg_color=self._primary_color, hover_color=self._secondary_color, text_color="#FFFFFF", border_width=2)
        if self._config.get("sync_active"): self.widgets["sync_active"].select()
        else: self.widgets["sync_active"].deselect()
        self.widgets["sync_active"].pack(side="left", pady=10)

    def _render_ia(self):
        self._create_section_header(self._content_frame, "CONFIGURACIÓN GPT (OPENAI)")
        grid_container = tk.Frame(self._content_frame, bg=self._bg_color)
        grid_container.pack(fill="x", padx=10)
        grid_container.columnconfigure(1, weight=1)

        tk.Label(grid_container, text="Modelo de IA:", font=("Helvetica", 12), fg="#FFFFFF", bg=self._bg_color, anchor="e", width=25).grid(row=0, column=0, padx=(0, 20), pady=15, sticky="e")
        current_model = self._config.get("ia_model", "gpt-4o-mini")
        combo = ctk.CTkOptionMenu(grid_container, values=["gpt-4o-mini", "gpt-4o"], height=40, width=250)
        combo.set(current_model)
        combo.grid(row=0, column=1, sticky="w", pady=15)
        self.widgets["ia_model"] = combo

        tk.Label(grid_container, text="OpenAI API Key:", font=("Helvetica", 12), fg="#FFFFFF", bg=self._bg_color, anchor="e", width=25).grid(row=1, column=0, padx=(0, 20), pady=15, sticky="e")
        val_key = self._config.get("ia_api_key", "")
        entry = ctk.CTkEntry(grid_container, placeholder_text="sk-...", height=40, show="*", font=("Helvetica", 12))
        entry.insert(0, val_key)
        entry.grid(row=1, column=1, sticky="ew", pady=15)
        self.widgets["ia_api_key"] = entry

    def _render_fuentes(self):
        self._create_section_header(self._content_frame, "CONECTORES DE DATOS EXTERNOS")
        sources = self.source_manager.get_all_sources()

        for source in sources:
            f_frame = tk.Frame(self._content_frame, bg=self._bg_medium, bd=1, relief="flat")
            f_frame.pack(fill="x", pady=5, ipady=10)
            tk.Label(f_frame, text=source.name, font=("Helvetica", 12, "bold"), fg=self._primary_color, bg=self._bg_medium).pack(side="left", padx=20)
            tk.Label(f_frame, text=f"- {source.description}", font=("Helvetica", 10), fg="#888", bg=self._bg_medium).pack(side="left")
            
            cb = ctk.CTkCheckBox(f_frame, text="ACTIVAR", font=("Helvetica", 10, "bold"), fg_color=self._primary_color, hover_color=self._secondary_color, text_color="#FFFFFF")
            if self._config.get(source.id): cb.select()
            else: cb.deselect()
            cb.pack(side="right", padx=10)
            self.widgets[source.id] = cb

            btn_test = ctk.CTkButton(f_frame, text="Test", width=60, height=24, fg_color=self._secondary_color, command=lambda s=source: self._on_test_source(s))
            btn_test.pack(side="right", padx=10)

    def _render_logs(self):
        """Pestaña de logs usando VirtualNavList."""
        columns = [
            ("FECHA", 180, "FECHA", False),
            ("ACCIÓN", 150, "ACCIÓN", False),
            ("RESULTADO", 120, "RESULTADO", False),
            ("MENSAJE", 400, "MENSAJE", True)
        ]

        self.nav_list = VirtualNavList(
            self._content_container,
            columns=columns,
            module_name='shopify'
        )
        self.nav_list.pack(fill=tk.BOTH, expand=True)
        self._refresh_logs_data()

    def _refresh_logs_data(self):
        """Carga los datos de la BD en la VirtualNavList."""
        if not hasattr(self, 'nav_list') or not self.nav_list.winfo_exists():
            return

        logs = self.service.get_logs(limit=100)
        items = []
        for l in logs:
            bg = "#1b3320" if l["resultado"] == "success" else "#331b1b"
            fg = "#2ecc71" if l["resultado"] == "success" else "#e74c3c"
            items.append({
                "FECHA": l["fecha"],
                "ACCIÓN": l["accion"],
                "RESULTADO": l["resultado"].upper(),
                "MENSAJE": l["mensaje"],
                "_row_bg": bg,
                "_row_fg": fg
            })
        self.nav_list.set_items(items)

    def _on_save(self):
        self._harvest_widgets()
        ok = self.service.save_config(self._config)
        if ok:
            self.service.add_log("SAVE_CONFIG", "success", "Configuración actualizada")
            show_success(self.frame, "Configuración guardada.")
        else:
            self.service.add_log("SAVE_CONFIG", "error", "Fallo al guardar")
            show_error(self.frame, "Error al guardar.")

    def _on_test_ia(self):
        api_key = self.widgets.get("ia_api_key").get().strip()
        model = self.widgets.get("ia_model").get()
        if not api_key:
            show_error(self.frame, "Introduce una API Key.")
            return
        ai_service = OpenAIService(api_key, model)
        success, message = ai_service.test_connection()
        if success:
            self.service.add_log("TEST_IA", "success", f"OpenAI OK ({model})")
            show_success(self.frame, f"Éxito: {message}")
        else:
            self.service.add_log("TEST_IA", "error", f"Fallo OpenAI: {message}")
            show_error(self.frame, f"Error: {message}")

    def _on_test_source(self, source):
        if source.test_connection():
            self.service.add_log("TEST_SOURCE", "success", f"{source.name} OK")
            show_success(self.frame, f"{source.name} OK.")
        else:
            self.service.add_log("TEST_SOURCE", "error", f"Fallo {source.name}")
            show_error(self.frame, f"Error en {source.name}.")

    def _on_refresh_logs(self):
        if self._current_tab == "LOGS":
            self._refresh_logs_data()

    def _on_clear_logs(self):
        if self.service.clear_logs():
            show_success(self.frame, "Logs limpiados.")
            self._on_refresh_logs()
        else:
            show_error(self.frame, "No se pudo limpiar el historial.")
