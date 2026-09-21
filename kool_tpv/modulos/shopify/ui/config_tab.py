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
        
        # Estado de edición de prompts (memoria temporal antes de APLICAR CAMBIOS)
        self._prompt_edits = {}         # { (clave, tipo_id): texto }
        self._prompt_nombre_edits = {}  # { clave: nombre }  (solo para genéricos)
        
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
        self._tabs = ["GENERAL", "TIPOS", "IA", "IA PROMPTS", "FUENTES", "LOGS"]

        # Estado de la pestaña TIPOS
        self._tipo_selected_id: Optional[int] = None
        self._tipo_selector: Optional[TagSelector] = None
        self._central_tipos: Optional[tk.Frame] = None
        self._tipos_header: Optional[tk.Frame] = None

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
            elif tab_name == "TIPOS":
                self._render_tipos()
            elif tab_name == "IA":
                self._render_ia()
            elif tab_name == "FUENTES":
                self._render_fuentes()
            elif tab_name == "IA PROMPTS":
                self._render_ia_prompts()

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
                elif isinstance(widget, ctk.CTkTextbox):
                    self._config[key] = widget.get("1.0", "end-1c").strip()
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

        if self._current_tab in ["GENERAL", "TIPOS", "IA", "IA PROMPTS", "FUENTES"]:
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
        self._create_section_header(self._content_frame, "CONEXIÓN SHOPIFY")
        grid_container = tk.Frame(self._content_frame, bg=self._bg_color)
        grid_container.pack(fill="x", padx=10)
        grid_container.columnconfigure(1, weight=1)
        grid_container.columnconfigure(3, weight=1)

        fields = [
            # (fila, col_label, texto_label, placeholder, clave)
            (0, 0, "URL de la tienda:", "tienda.myshopify.com", "shop_url"),
            (0, 2, "Admin API Token:", "shpat_xxxxxxxxxxxxxxxxxxxx", "access_token"),
            (1, 0, "Location ID:", "12345678", "location_id"),
            (1, 2, "Versión API:", "2026-07", "api_version"),
            (2, 0, "Plantilla producto:", "camiseta", "template_suffix"),
            (2, 2, "Marca/Proveedor:", "Kool Things", "marca"),
            (3, 0, "URL guía de tallas:", "https://...", "link_guia"),
            (3, 2, "CDN botones género:", "https://cdn.shopify.com/.../files/", "botones_cdn"),
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

        # Fila 5: estado del servicio
        self.widgets["sync_active"] = ctk.CTkCheckBox(grid_container, text="ACTIVAR SINCRONIZACIÓN AUTOMÁTICA", font=("Helvetica", 12, "bold"), fg_color=self._primary_color, hover_color=self._secondary_color, text_color="#FFFFFF", border_width=2)
        if self._config.get("sync_active"): self.widgets["sync_active"].select()
        else: self.widgets["sync_active"].deselect()
        self.widgets["sync_active"].grid(row=4, column=0, columnspan=4, sticky="w", pady=15)

    def _render_tipos(self):
        self._create_section_header(self._content_frame, "TIPOS ACTIVOS PARA SHOPIFY")

        # --- ZONA CENTRAL (primero, para evitar fantasmas visuales) ---
        self._central_tipos = tk.Frame(self._content_frame, bg=self._bg_medium)
        self._central_tipos.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # --- BUSCADOR Y SELECTOR ---
        self._tipo_selector = TagSelector(
            self._content_frame,
            module_name='shopify',
            placeholder="Buscar un tipo para gestionar...",
            selectable=True,
            on_select=self._on_tipo_selected,
            on_change=self._on_tipo_web_change
        )
        # Poner el buscador ARRIBA de la zona central
        self._tipo_selector.pack(before=self._central_tipos, fill="x", padx=10, pady=(0, 20))
        
        # Cargar tipos actuales (desactivando callback temporalmente para evitar spam de etiquetas)
        self._tipo_selector.on_change_callback = None
        tipos = self._load_tipos_web()
        for t in tipos:
            self._tipo_selector.add_tag(t["id"], t["nombre"])
        self._tipo_selector.on_change_callback = self._on_tipo_web_change
        
        # Restaurar selección si existe
        if self._tipo_selected_id:
            self._tipo_selector.set_active(self._tipo_selected_id)
            self._render_variantes(self._tipo_selected_id)
        else:
            self._render_placeholder_tipos()

    def _render_placeholder_tipos(self):
        self._clear_central_tipos()
        tk.Label(self._central_tipos, text="Busca y añade un tipo, luego selecciónalo para configurar",
                 font=("Helvetica", 12), fg="#888888", bg=self._bg_medium).pack(pady=40)

    def _load_tipos_web(self) -> List[Dict[str, Any]]:
        try:
            rows = self.db.fetch_all(
                "SELECT id, nombre FROM tipos WHERE web_activo = 1 AND activo = 1 ORDER BY nombre"
            )
            return [{"id": r[0], "nombre": r[1]} for r in (rows or [])]
        except Exception:
            logger.exception("Error cargando tipos web")
            return []

    def _clear_central_tipos(self):
        if self._central_tipos and self._central_tipos.winfo_exists():
            for child in self._central_tipos.winfo_children():
                child.destroy()

    def _on_tipo_selected(self, tipo_id: int):
        """Callback cuando se clica un chip en el TagSelector."""
        self._tipo_selected_id = tipo_id
        self._render_variantes(tipo_id)

    def _on_tipo_web_change(self):
        """Callback cuando se borra un tag del selector."""
        if not self._tipo_selector: return
        selected_ids = self._tipo_selector.get_selected_ids()
        try:
            self.db.execute_query("UPDATE tipos SET web_activo = 0")
            if selected_ids:
                placeholders = ",".join(["?"] * len(selected_ids))
                self.db.execute_query(f"UPDATE tipos SET web_activo = 1 WHERE id IN ({placeholders})", tuple(selected_ids))
            
            if self._tipo_selected_id not in selected_ids:
                self._tipo_selected_id = None
                self._render_placeholder_tipos()
        except Exception:
            logger.exception("Error actualizando web_activo")

    def _render_variantes(self, tipo_id: int):
        self._clear_central_tipos()
        if not self._central_tipos:
            return

        try:
            tipo_row = self.db.fetch_one("SELECT nombre FROM tipos WHERE id = ?", (tipo_id,))
            tipo_nombre = (tipo_row[0] if tipo_row else "").upper()
        except Exception:
            tipo_nombre = ""

        header_frame = tk.Frame(self._central_tipos, bg=self._bg_medium)
        header_frame.pack(fill="x", padx=15, pady=(10, 15))

        tk.Label(header_frame, text=tipo_nombre, font=("Helvetica", 18, "bold"),
                 fg=self._primary_color, bg=self._bg_medium).pack(side="left")

        # --- Plantilla por tipo ---
        try:
            tpl_row = self.db.fetch_one("SELECT template_suffix FROM tipos WHERE id = ?", (tipo_id,))
            tipo_template = (tpl_row[0] or "") if tpl_row else ""
        except Exception:
            tipo_template = ""

        tk.Label(header_frame, text="PLANTILLA:", font=("Helvetica", 11),
                 fg="#FFFFFF", bg=self._bg_medium).pack(side="left", padx=(30, 10))
        self._tipos_template_entry = ctk.CTkEntry(header_frame, width=150, font=("Helvetica", 12))
        self._tipos_template_entry.insert(0, tipo_template)
        self._tipos_template_entry.pack(side="left", padx=(0, 20))

        # --- Campos extra solo para Camiseta ---
        self._tipos_sorpresa_stock_entry = None
        self._tipos_sorpresa_precio_entry = None
        self._tipos_recargo_entry = None
        self._tipos_recargo_grupo_combo = None

        if tipo_nombre.lower() == "camiseta":
            # --- Fila 1: Stock y Precio Sorpresa ---
            row1 = tk.Frame(header_frame, bg=self._bg_medium)
            row1.pack(fill="x", pady=(0, 5))

            tk.Label(row1, text="STOCK SORPRESA:", font=("Helvetica", 11),
                     fg="#FFFFFF", bg=self._bg_medium).pack(side="left", padx=(20, 10))
            self._tipos_sorpresa_stock_entry = ctk.CTkEntry(row1, width=80, font=("Helvetica", 12))
            self._tipos_sorpresa_stock_entry.insert(0, self._config.get("stock_sorpresa", "50"))
            self._tipos_sorpresa_stock_entry.pack(side="left", padx=(0, 20))

            tk.Label(row1, text="PRECIO SORPRESA:", font=("Helvetica", 11),
                     fg="#FFFFFF", bg=self._bg_medium).pack(side="left", padx=(0, 10))
            self._tipos_sorpresa_precio_entry = ctk.CTkEntry(row1, width=100, font=("Helvetica", 12))
            self._tipos_sorpresa_precio_entry.insert(0, self._config.get("precio_sorpresa", ""))
            self._tipos_sorpresa_precio_entry.pack(side="left", padx=(0, 20))

            # --- Fila 2: Recargos ---
            row2 = tk.Frame(header_frame, bg=self._bg_medium)
            row2.pack(fill="x")

            tk.Label(row2, text="RECARGO TALLAS GRANDES (€):", font=("Helvetica", 11),
                     fg="#FFFFFF", bg=self._bg_medium).pack(side="left", padx=(20, 10))
            self._tipos_recargo_entry = ctk.CTkEntry(row2, width=60, font=("Helvetica", 12))
            self._tipos_recargo_entry.insert(0, self._config.get("recargo_tallas", "0"))
            self._tipos_recargo_entry.pack(side="left", padx=(0, 20))

            tk.Label(row2, text="APLICAR A GRUPO:", font=("Helvetica", 11),
                     fg="#FFFFFF", bg=self._bg_medium).pack(side="left", padx=(0, 10))
            
            from kool_tpv.utils.widgets.searchable_combo import SearchableCombo
            from kool_tpv.modulos.produccion.repositories.produccion_tallas_grupos_repository import ProduccionTallasGruposRepository
            
            repo_grupos = ProduccionTallasGruposRepository(self.db)
            grupos = repo_grupos.get_todos()
            opts_grupos = [(g.id, g.nombre) for g in grupos]
            
            self._tipos_recargo_grupo_combo = SearchableCombo(row2, width=180, placeholder="Seleccionar grupo...", options=opts_grupos)
            self._tipos_recargo_grupo_combo.pack(side="left")
            
            grupo_id_cfg = self._config.get("recargo_grupo_id")
            if grupo_id_cfg:
                self._tipos_recargo_grupo_combo.set_by_id(int(grupo_id_cfg))

        # --- Lista de variantes ---
        self._tipos_price_entries = []
        list_frame = tk.Frame(self._central_tipos, bg=self._bg_medium)
        list_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        for c in range(9):
            list_frame.columnconfigure(c, weight=1, uniform="tipo_var")

        headers = [("VARIANTE", 20, "w"), ("SUBIR A WEB", 0, "center"), ("PRECIO WEB", 0, "center")]
        for grupo in range(3):
            col_base = grupo * 3
            for j, (texto, ancho, anclaje) in enumerate(headers):
                tk.Label(list_frame, text=texto, font=("Helvetica", 11, "bold"),
                         fg=self._primary_color, bg=self._bg_medium, width=ancho, anchor=anclaje).grid(
                             row=0, column=col_base + j, padx=5, pady=8, sticky="ew")

        try:
            rows = self.db.fetch_all(
                "SELECT id, nombre, sync_web, precio_web FROM tipos_variantes WHERE tipo_id = ? AND activo = 1 ORDER BY orden, nombre",
                (tipo_id,)
            )
        except Exception:
            logger.exception("Error cargando variantes")
            rows = []

        for i, row in enumerate(rows or []):
            v_id, nombre, sync_web, precio_web = row
            fila = (i // 3) + 1
            col_base = (i % 3) * 3

            tk.Label(list_frame, text=nombre.upper(), font=("Helvetica", 11),
                     fg="#FFFFFF", bg=self._bg_medium, anchor="w").grid(
                         row=fila, column=col_base, sticky="w", padx=5, pady=6)

            chk_var = tk.BooleanVar(value=bool(sync_web))
            chk = ctk.CTkCheckBox(list_frame, text="", variable=chk_var, fg_color=self._primary_color,
                                  hover_color=self._secondary_color, width=20)
            chk.grid(row=fila, column=col_base + 1, padx=5, pady=6)
            chk_var.trace_add("write", lambda *a, vid=v_id, var=chk_var: self._guardar_variante(vid, sync_web=int(var.get())))

            precio_str = self._format_precio_web(precio_web)
            entry_precio = ctk.CTkEntry(list_frame, width=90, font=("Helvetica", 12))
            entry_precio.insert(0, precio_str)
            entry_precio.grid(row=fila, column=col_base + 2, padx=5, pady=6)
            self._tipos_price_entries.append((v_id, entry_precio))

        # --- Prompts IA (Punto 3 - Tabs unificados) ---
        self._create_section_header(self._central_tipos, "PROMPTS IA")
        self._render_prompt_editor_panel(self._central_tipos, tipo_id=tipo_id)

    def _render_prompt_editor_panel(self, parent, tipo_id=None):
        """Renderiza la zona de edición de prompts con chips y editor único."""
        frame = tk.Frame(parent, bg=self._bg_medium if tipo_id else self._bg_color)
        frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        # Determinar qué prompts mostrar
        if tipo_id is None:
            # Modo IA PROMPTS: solo genéricos
            prompts = self.prompts_repo.get_genericos()
        else:
            # Modo TIPOS: las 5 claves estándar
            prompts = []
            for clave in ["tags", "body", "seo", "seo_title", "html"]:
                p = self.prompts_repo.get_prompt(clave)
                if p: prompts.append(p)

        if not prompts:
            return

        # Chips
        chips_frame = tk.Frame(frame, bg=frame["bg"])
        chips_frame.pack(fill="x", pady=(0, 10))
        
        # Guardar refs de widgets según el contexto
        ctx = "tipo" if tipo_id else "gen"
        setattr(self, f"_{ctx}_prompt_chips", {})
        setattr(self, f"_{ctx}_prompt_area", tk.Frame(frame, bg=frame["bg"]))
        getattr(self, f"_{ctx}_prompt_area").pack(fill="both", expand=True)

        for p in prompts:
            clave = p['clave']
            chip = tk.Label(
                chips_frame, text=p['nombre'].upper(), font=("Helvetica", 10, "bold"),
                fg=self._tab_text_normal, bg=self._tab_bg_normal,
                padx=16, pady=8, cursor="hand2"
            )
            chip.pack(side="left", padx=(0, 6))
            chip.bind("<Button-1>", lambda e=None, c=clave, t=tipo_id: self._select_prompt_v2(c, t))
            getattr(self, f"_{ctx}_prompt_chips")[clave] = chip

        # Seleccionar el primero
        self._select_prompt_v2(prompts[0]['clave'], tipo_id)

    def _select_prompt_v2(self, clave: str, tipo_id: Optional[int]):
        """Versión unificada del selector de prompts."""
        ctx = "tipo" if tipo_id else "gen"
        area = getattr(self, f"_{ctx}_prompt_area")
        chips = getattr(self, f"_{ctx}_prompt_chips")
        
        # Flush actual si existe
        active_key = getattr(self, f"_{ctx}_active_prompt", None)
        editor = getattr(self, f"_{ctx}_prompt_editor", None)
        if active_key and editor and editor.winfo_exists():
            self._prompt_edits[(active_key, tipo_id)] = editor.get("1.0", "end-1c")
            nombre_entry = getattr(self, f"_{ctx}_prompt_nombre_entry", None)
            if nombre_entry and nombre_entry.winfo_exists():
                self._prompt_nombre_edits[active_key] = nombre_entry.get().strip()

        setattr(self, f"_{ctx}_active_prompt", clave)
        
        # Visual chips
        for c, lbl in chips.items():
            if c == clave: lbl.configure(bg=self._tab_bg_selected, fg=self._tab_text_selected)
            else: lbl.configure(bg=self._tab_bg_normal, fg=self._tab_text_normal)

        for child in area.winfo_children(): child.destroy()

        # Datos
        data = self.prompts_repo.get_prompt(clave, tipo_id) or self.prompts_repo.get_prompt(clave)
        texto = self._prompt_edits.get((clave, tipo_id)) or self.prompts_repo.get_texto(clave, tipo_id)

        # Header (Nombre editable si es genérico)
        head = tk.Frame(area, bg=area["bg"])
        head.pack(fill="x", pady=(0, 5))
        
        if tipo_id is None:
            tk.Label(head, text="NOMBRE:", font=("Helvetica", 10, "bold"), fg="#888", bg=head["bg"]).pack(side="left", padx=(0, 8))
            nombre_entry = ctk.CTkEntry(head, width=220, height=28, font=("Helvetica", 11))
            nombre_entry.insert(0, self._prompt_nombre_edits.get(clave) or data.get('nombre') or clave)
            nombre_entry.pack(side="left", padx=(0, 20))
            setattr(self, f"_{ctx}_prompt_nombre_entry", nombre_entry)
        
        marcadores = self._MARCADORES.get(clave, "")
        tk.Label(head, text=f"Marcadores: {marcadores}", font=("Helvetica", 9, "italic"), fg="#888", bg=head["bg"]).pack(side="left")

        # Editor
        h = 180 if tipo_id else 540
        txt = ctk.CTkTextbox(area, height=h, font=("Consolas" if not tipo_id else "Helvetica", 12 if not tipo_id else 11), wrap="word")
        txt.pack(fill="both", expand=True, pady=(0, 8))
        txt.insert("1.0", texto)
        setattr(self, f"_{ctx}_prompt_editor", txt)
        
        if tipo_id:
            txt.after(100, self._ajustar_altura_prompt_tipo)

        # Footer (Estado + Botones)
        foot = tk.Frame(area, bg=area["bg"])
        foot.pack(fill="x")
        
        if tipo_id is not None:
            es_perso = bool(self.prompts_repo.get_prompt(clave, tipo_id))
            lbl_est = tk.Label(foot, text="PERSONALIZADO" if es_perso else "GENÉRICO", font=("Helvetica", 9, "bold"),
                               fg="#00FF00" if es_perso else "#888888", bg=foot["bg"])
            lbl_est.pack(side="left")
            
            ButtonFactory.create_button(foot, text="GUARDAR", color=self._primary_color, text_color="#000000",
                                        command=lambda: self._guardar_prompt_tipo_v2(clave, tipo_id, txt, lbl_est),
                                        width=110, height=30).pack(side="right")
            ButtonFactory.create_button(foot, text="RESTAURAR GENÉRICO", color=self._secondary_color, text_color="#FFFFFF",
                                        command=lambda: self._restaurar_prompt_v2(clave, tipo_id, txt, lbl_est),
                                        width=150, height=30).pack(side="right", padx=(0, 8))
        else:
            # En IA PROMPTS el botón de restaurar es al original del código
            ButtonFactory.create_button(head, text="RESTAURAR ORIGINAL", color=self._secondary_color, text_color="#FFFFFF",
                                        command=lambda: self._restaurar_prompt_v2(clave, None, txt, None),
                                        width=170, height=26).pack(side="right")

    def _guardar_prompt_tipo_v2(self, clave, tipo_id, txt, lbl_est):
        texto = txt.get("1.0", "end-1c")
        if self.prompts_repo.save_texto(clave, texto, tipo_id):
            self._prompt_edits.pop((clave, tipo_id), None)
            lbl_est.configure(text="PERSONALIZADO", fg="#00FF00")
            show_success(self.frame, f"{clave} guardado para este tipo.")
        else:
            show_error(self.frame, "Error al guardar.")

    def _restaurar_prompt_v2(self, clave, tipo_id, txt, lbl_est):
        """Restaurar un prompt: si tipo_id es None -> original del código; si tipo_id -> genérico."""
        texto = self.prompts_repo.reset_to_default(clave, tipo_id)
        if texto is None and tipo_id is not None:
            texto = self.prompts_repo.get_texto(clave, None)
        
        if texto is not None:
            self._prompt_edits.pop((clave, tipo_id), None)
            txt.delete("1.0", "end")
            txt.insert("1.0", texto)
            if lbl_est: lbl_est.configure(text="GENÉRICO", fg="#888888")
            show_success(self.frame, "Prompt restaurado.")
        else:
            show_error(self.frame, "No se pudo restaurar.")

    def _ajustar_altura_prompt_tipo(self):
        """Ajusta el alto del editor de prompts al espacio visible disponible."""
        try:
            # Detectar cuál es el editor activo (gen o tipo)
            ctx = "gen" if self._current_tab == "IA PROMPTS" else "tipo"
            editor = getattr(self, f'_{ctx}_prompt_editor', None)
            
            if editor is None or not editor.winfo_exists():
                return
            top = editor.winfo_toplevel()
            editor_y = editor.winfo_rooty() - top.winfo_rooty()
            disponible = top.winfo_height() - editor_y - 160
            editor.configure(height=max(200, disponible))
        except Exception:
            pass

    def _guardar_variante(self, variante_id: int, sync_web: Optional[int] = None, precio_web: Optional[int] = None):
        try:
            if sync_web is not None:
                self.db.execute_query("UPDATE tipos_variantes SET sync_web = ? WHERE id = ?", (sync_web, variante_id))
            if precio_web is not None:
                self.db.execute_query("UPDATE tipos_variantes SET precio_web = ? WHERE id = ?", (precio_web, variante_id))
        except Exception:
            logger.exception(f"Error guardando variante {variante_id}")
            show_error(self.frame, "Error guardando la variante.")

    def _format_precio_web(self, cents: Optional[int]) -> str:
        try:
            return f"{int(cents or 0) / 100:.2f}".replace(".", ",")
        except Exception:
            return "0,00"

    def _parse_precio_web(self, texto: str) -> int:
        try:
            limpio = texto.replace("€", "").strip().replace(",", ".")
            if not limpio:
                return 0
            return int(round(float(limpio) * 100))
        except Exception:
            return 0

    def _guardar_config_valor(self, key: str, valor: str):
        self._config[key] = valor
        try:
            self.service.save_config(self._config)
        except Exception:
            logger.exception(f"Error guardando config {key}")
            show_error(self.frame, "Error guardando el valor.")

    def _guardar_template_suffix(self, tipo_id: int, valor: str):
        try:
            self.db.execute_query(
                "UPDATE tipos SET template_suffix = ? WHERE id = ?",
                (valor.strip(), tipo_id)
            )
        except Exception:
            logger.exception(f"Error guardando template_suffix para tipo {tipo_id}")
            show_error(self.frame, "Error guardando la plantilla.")

    def _guardar_tipo_actual(self):
        """Guarda plantilla, sorpresa y precios web del tipo seleccionado en TIPOS."""
        tipo_id = getattr(self, "_tipo_selected_id", None)
        if tipo_id is None:
            return

        template_entry = getattr(self, "_tipos_template_entry", None)
        if template_entry is not None and template_entry.winfo_exists():
            self._guardar_template_suffix(tipo_id, template_entry.get())

        stock_entry = getattr(self, "_tipos_sorpresa_stock_entry", None)
        if stock_entry is not None and stock_entry.winfo_exists():
            self._guardar_config_valor("stock_sorpresa", stock_entry.get())

        precio_entry = getattr(self, "_tipos_sorpresa_precio_entry", None)
        if precio_entry is not None and precio_entry.winfo_exists():
            self._guardar_config_valor("precio_sorpresa", precio_entry.get())

        recargo_entry = getattr(self, "_tipos_recargo_entry", None)
        if recargo_entry is not None and recargo_entry.winfo_exists():
            self._guardar_config_valor("recargo_tallas", recargo_entry.get())

        recargo_grupo = getattr(self, "_tipos_recargo_grupo_combo", None)
        if recargo_grupo is not None and recargo_grupo.winfo_exists():
            self._guardar_config_valor("recargo_grupo_id", recargo_grupo.get_id())

        for v_id, ent in getattr(self, "_tipos_price_entries", []):
            try:
                if ent.winfo_exists():
                    self._guardar_variante(v_id, precio_web=self._parse_precio_web(ent.get()))
            except Exception:
                continue

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

        tk.Label(grid_container, text="Google Books API Key:", font=("Helvetica", 12), fg="#FFFFFF", bg=self._bg_color, anchor="e", width=25).grid(row=2, column=0, padx=(0, 20), pady=15, sticky="e")
        val_google = self._config.get("google_api_key", "")
        entry_g = ctk.CTkEntry(grid_container, placeholder_text="AIza...", height=40, show="*", font=("Helvetica", 12))
        entry_g.insert(0, val_google)
        entry_g.grid(row=2, column=1, sticky="ew", pady=15)
        self.widgets["google_api_key"] = entry_g

    def _render_fuentes(self):
        self._create_section_header(self._content_frame, "CONECTORES DE DATOS EXTERNOS")
        
        # --- ZONA GLOBAL DE SELECCIÓN DE TIPO ---
        selection_zone = tk.Frame(self._content_frame, bg=self._bg_color)
        selection_zone.pack(fill="x", padx=10, pady=(0, 20))
        
        tk.Label(
            selection_zone, text="TIPO DE PRODUCTO A VINCULAR:", 
            font=("Helvetica", 10, "bold"), fg="#888", bg=self._bg_color
        ).pack(side="left", padx=(0, 10))
        
        # Cargar tipos para el combo
        try:
            rows = self.db.fetch_all("SELECT id, nombre FROM tipos ORDER BY nombre ASC")
            all_types = [(r[0], r[1]) for r in (rows or [])]
        except Exception:
            all_types = []
            
        from kool_tpv.utils.widgets.searchable_combo import SearchableCombo
        self.type_combo = SearchableCombo(
            selection_zone, 
            options=all_types,
            placeholder="Selecciona un tipo...",
            width=300,
            module_name='shopify'
        )
        self.type_combo.pack(side="left")
        
        # --- LISTADO DE CONECTORES ---
        sources = self.source_manager.get_all_sources()

        for source in sources:
            f_frame = tk.Frame(self._content_frame, bg=self._bg_medium, bd=1, relief="flat")
            f_frame.pack(fill="x", pady=5, ipady=10)
            
            # Contenedor izquierdo (Nombre + Tags)
            left_container = tk.Frame(f_frame, bg=self._bg_medium)
            left_container.pack(side="left", fill="both", expand=True, padx=20)
            
            top_line = tk.Frame(left_container, bg=self._bg_medium)
            top_line.pack(fill="x")
            
            tk.Label(top_line, text=source.name, font=("Helvetica", 12, "bold"), fg=self._primary_color, bg=self._bg_medium).pack(side="left")
            tk.Label(top_line, text=f"- {source.description}", font=("Helvetica", 10), fg="#888", bg=self._bg_medium).pack(side="left", padx=10)
            
            # Zona de Tags (Vínculos actuales)
            tags_frame = tk.Frame(left_container, bg=self._bg_medium)
            tags_frame.pack(fill="x", pady=(5, 0))
            self._render_source_tags(source, tags_frame)
            
            # Botones derecha
            cb = ctk.CTkCheckBox(f_frame, text="ACTIVAR", font=("Helvetica", 10, "bold"), fg_color=self._primary_color, hover_color=self._secondary_color, text_color="#FFFFFF")
            if self._config.get(source.id): cb.select()
            else: cb.deselect()
            cb.pack(side="right", padx=10)
            self.widgets[source.id] = cb

            btn_test = ctk.CTkButton(f_frame, text="Test", width=60, height=24, fg_color=self._secondary_color, command=lambda s=source: self._on_test_source(s))
            btn_test.pack(side="right", padx=10)

            # Botón "+" para añadir el tipo seleccionado en el combo
            btn_add = ctk.CTkButton(
                f_frame, text="+", width=30, height=24, 
                fg_color=self._primary_color, font=("Helvetica", 14, "bold"),
                command=lambda s=source, tf=tags_frame: self._on_add_type_to_source(s, tf)
            )
            btn_add.pack(side="right", padx=10)

    def _render_source_tags(self, source, parent):
        """Dibuja los tipos vinculados como etiquetas."""
        for child in parent.winfo_children():
            child.destroy()
            
        try:
            # Obtener nombres de tipos mapeados
            query = """
                SELECT t.id, t.nombre 
                FROM tipos t
                JOIN shopify_source_type_mapping m ON t.id = m.tipo_id
                WHERE m.source_id = ?
                ORDER BY t.nombre ASC
            """
            rows = self.db.fetch_all(query, (source.id,))
            
            if not rows:
                tk.Label(parent, text="Sin tipos vinculados", font=("Helvetica", 8, "italic"), fg="#555", bg=self._bg_medium).pack(side="left")
                return

            for t_id, t_nombre in rows:
                tag = tk.Frame(parent, bg="#333", padx=5, pady=2)
                tag.pack(side="left", padx=(0, 5))
                
                tk.Label(tag, text=t_nombre.upper(), font=("Helvetica", 8, "bold"), fg=self._primary_color, bg="#333").pack(side="left")
                
                btn_del = tk.Label(tag, text="✕", font=("Helvetica", 8), fg="#666", bg="#333", cursor="hand2")
                btn_del.pack(side="left", padx=(5, 0))
                btn_del.bind("<Button-1>", lambda e, sid=source.id, tid=t_id, tf=parent: self._on_remove_type_from_source(sid, tid, tf, source))

        except Exception:
            logger.exception("Error renderizando tags")

    def _on_add_type_to_source(self, source, tags_frame):
        """Añade el tipo seleccionado en el combo al conector."""
        tipo_id = self.type_combo.get_id()
        if not tipo_id:
            show_error(self.frame, "Selecciona primero un tipo en el buscador superior.")
            return
            
        # Obtener mapeos actuales para añadir el nuevo
        current_ids = self.service.get_source_type_mappings(source.id)
        if tipo_id in current_ids:
            show_error(self.frame, "Este tipo ya está vinculado a esta fuente.")
            return
            
        current_ids.append(tipo_id)
        if self.service.update_source_type_mappings(source.id, current_ids):
            self._render_source_tags(source, tags_frame)
        else:
            show_error(self.frame, "Error al guardar el vínculo.")

    def _on_remove_type_from_source(self, source_id, tipo_id, tags_frame, source):
        """Elimina un vínculo de tipo."""
        current_ids = self.service.get_source_type_mappings(source_id)
        if tipo_id in current_ids:
            current_ids.remove(tipo_id)
            if self.service.update_source_type_mappings(source_id, current_ids):
                self._render_source_tags(source, tags_frame)

    # Marcadores disponibles por prompt
    _MARCADORES = {
        "tags": "{titulo_base} {tipo_producto}",
        "body": "{variante} {tipo_producto} {titulo_base} {tono} {instrucciones_variante} {tags} {beneficio} {tags_top3}",
        "seo": "{tipo_producto} {titulo_base} {tags} {beneficio}",
        "seo_title": "{titulo} {variante} {marca}",
        "html": "{titulo_introductorio} {parrafo_introductorio} {titulo_seccion_calidad} {bloque_calidad_impresion} {bloque_calidad_material} {bloque_calidad_durabilidad} {bloque_porque_elegirnos} {botones_html}",
        "manga_seo": "{product_name} {source_data}",
    }

    def _render_ia_prompts(self):
        """Pestaña de prompts genéricos: chips arriba, un editor unificado."""
        self._create_section_header(self._content_frame, "PROMPTS DE IA (GENÉRICOS)")
        self._render_prompt_editor_panel(self._content_frame, tipo_id=None)

    def _on_save(self):
        self._harvest_widgets()
        
        # Flush editores activos a memoria antes de guardar
        for ctx in ["gen", "tipo"]:
            active = getattr(self, f"_{ctx}_active_prompt", None)
            tipo_id = self._tipo_selected_id if ctx == "tipo" else None
            editor = getattr(self, f"_{ctx}_prompt_editor", None)
            if active and editor and editor.winfo_exists():
                self._prompt_edits[(active, tipo_id)] = editor.get("1.0", "end-1c")
                nom_entry = getattr(self, f"_{ctx}_prompt_nombre_entry", None)
                if nom_entry and nom_entry.winfo_exists():
                    self._prompt_nombre_edits[active] = nom_entry.get().strip()

        ok = self.service.save_config(self._config)
        
        # Guardar los prompts editados en su tabla
        prompts_ok = True
        for (clave, t_id), texto in self._prompt_edits.items():
            prompts_ok = self.prompts_repo.save_texto(clave, texto, t_id) and prompts_ok
        
        for clave, nombre in self._prompt_nombre_edits.items():
            prompts_ok = self.prompts_repo.save_nombre(clave, nombre) and prompts_ok
            # Refrescar chips visuales
            for ctx in ["gen", "tipo"]:
                chips = getattr(self, f"_{ctx}_prompt_chips", {})
                if clave in chips:
                    try: chips[clave].configure(text=(nombre or clave).upper())
                    except Exception: pass

        self._prompt_edits = {}
        self._prompt_nombre_edits = {}

        # Guardar los campos del tipo seleccionado en TIPOS (precios, plantilla...)
        if self._current_tab == "TIPOS":
            self._guardar_tipo_actual()

        if ok and prompts_ok:
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
        success, message = source.test_connection()
        if success:
            self.service.add_log("TEST_SOURCE", "success", f"{source.name}: {message}")
            show_success(self.frame, f"{source.name} OK: {message}")
        else:
            self.service.add_log("TEST_SOURCE", "error", f"Fallo {source.name}: {message}")
            show_error(self.frame, f"Error en {source.name}:\n{message}")

    def _on_refresh_logs(self):
        if self._current_tab == "LOGS":
            self._refresh_logs_data()

    def _on_clear_logs(self):
        if self.service.clear_logs():
            show_success(self.frame, "Logs limpiados.")
            self._on_refresh_logs()
        else:
            show_error(self.frame, "No se pudo limpiar el historial.")
