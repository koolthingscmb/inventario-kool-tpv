import tkinter as tk
import customtkinter as ctk
import logging
from typing import Dict, Any, List, Optional
from kool_tpv.utils.widgets.tag_selector import TagSelector
from kool_tpv.utils.widgets.notificaciones import show_error

logger = logging.getLogger(__name__)

class TiposTab:
    """Gestiona la pestaña de TIPOS: variantes, precios y prompts específicos."""

    def __init__(self, parent, db, config, primary_color, secondary_color, bg_color, bg_medium, tab_bg_selected, tab_bg_normal, tab_text_selected, tab_text_normal, prompts_repo):
        self.parent = parent
        self.db = db
        self._config = config
        self._primary_color = primary_color
        self._secondary_color = secondary_color
        self._bg_color = bg_color
        self._bg_medium = bg_medium
        
        # Estilos de chips/tabs
        self._tab_bg_selected = tab_bg_selected
        self._tab_bg_normal = tab_bg_normal
        self._tab_text_selected = tab_text_selected
        self._tab_text_normal = tab_text_normal
        
        self.prompts_repo = prompts_repo
        
        # Estado
        self._tipo_selected_id: Optional[int] = None
        self._tipo_selector: Optional[TagSelector] = None
        self._central_tipos: Optional[tk.Frame] = None
        self._tipos_header: Optional[tk.Frame] = None
        self._tipos_price_entries = []
        
        # Refs a widgets de configuración específica
        self._tipos_template_entry = None
        self._tipos_sorpresa_stock_entry = None
        self._tipos_sorpresa_precio_entry = None
        self._tipos_recargo_entry = None
        self._tipos_recargo_grupo_combo = None

        # Callback externo para el editor de prompts (compartido)
        self.render_prompt_editor_callback = None

    def render(self):
        """Dibuja la interfaz de la pestaña TIPOS con scroll propio."""
        scroll = ctk.CTkScrollableFrame(self.parent, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        # --- BUSCADOR Y SELECTOR ---
        self._tipo_selector = TagSelector(
            scroll,
            module_name='shopify',
            placeholder="Buscar un tipo para gestionar...",
            selectable=True,
            on_select=self._on_tipo_selected,
            on_change=self._on_tipo_web_change
        )
        self._tipo_selector.pack(fill="x", padx=10, pady=(0, 20))

        # --- ZONA CENTRAL ---
        self._central_tipos = tk.Frame(scroll, bg=self._bg_medium)
        self._central_tipos.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # Cargar tipos actuales
        self._tipo_selector.on_change_callback = None
        tipos = self._load_tipos_web()
        for t in tipos:
            self._tipo_selector.add_tag(t["id"], t["nombre"])
        self._tipo_selector.on_change_callback = self._on_tipo_web_change
        
        if self._tipo_selected_id:
            self._tipo_selector.set_active(self._tipo_selected_id)
            self._render_variantes(self._tipo_selected_id)
        else:
            self._render_placeholder_tipos()

    def _render_placeholder_tipos(self):
        self._clear_central_tipos()
        tk.Label(self._central_tipos, text="Busca y añade un tipo, luego selecciónalo para configurar",
                 font=("Helvetica", 12), fg="#888888", bg=self._bg_medium).pack(pady=40)

    def _load_tipos_web(self) -> List[Dict]:
        try:
            rows = self.db.fetch_all("SELECT id, nombre FROM tipos WHERE web_activo = 1 AND activo = 1 ORDER BY nombre")
            return [{"id": r[0], "nombre": r[1]} for r in (rows or [])]
        except Exception:
            return []

    def _on_tipo_selected(self, tipo_id: int):
        self._tipo_selected_id = tipo_id
        self._render_variantes(tipo_id)

    def _on_tipo_web_change(self):
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

    def _clear_central_tipos(self):
        if self._central_tipos and self._central_tipos.winfo_exists():
            for child in self._central_tipos.winfo_children():
                child.destroy()

    def _render_variantes(self, tipo_id: int):
        self._clear_central_tipos()
        try:
            res = self.db.fetch_one("SELECT nombre, template_suffix FROM tipos WHERE id = ?", (tipo_id,))
            tipo_nombre = res[0] if res else ""
            template_suffix = res[1] or ""
        except Exception:
            tipo_nombre, template_suffix = "", ""

        header_frame = tk.Frame(self._central_tipos, bg=self._bg_medium)
        header_frame.pack(fill="x", padx=15, pady=(10, 15))

        tk.Label(header_frame, text=tipo_nombre.upper(), font=("Helvetica", 18, "bold"),
                 fg=self._primary_color, bg=self._bg_medium).pack(side="left")

        tk.Label(header_frame, text="PLANTILLA:", font=("Helvetica", 11),
                 fg="#FFFFFF", bg=self._bg_medium).pack(side="left", padx=(30, 10))
        self._tipos_template_entry = ctk.CTkEntry(header_frame, width=150, font=("Helvetica", 12))
        self._tipos_template_entry.insert(0, template_suffix)
        self._tipos_template_entry.pack(side="left", padx=(0, 20))

        if tipo_nombre.lower() == "camiseta":
            row_config = tk.Frame(header_frame, bg=self._bg_medium)
            row_config.pack(fill="x", pady=5)
            tk.Label(row_config, text="STOCK SORPRESA:", font=("Helvetica", 11), fg="#FFFFFF", bg=self._bg_medium).pack(side="left", padx=(20, 5))
            self._tipos_sorpresa_stock_entry = ctk.CTkEntry(row_config, width=60, font=("Helvetica", 12))
            self._tipos_sorpresa_stock_entry.insert(0, self._config.get("stock_sorpresa", "50"))
            self._tipos_sorpresa_stock_entry.pack(side="left", padx=(0, 20))
            tk.Label(row_config, text="PVP SORPRESA:", font=("Helvetica", 11), fg="#FFFFFF", bg=self._bg_medium).pack(side="left", padx=(0, 5))
            self._tipos_sorpresa_precio_entry = ctk.CTkEntry(row_config, width=80, font=("Helvetica", 12))
            self._tipos_sorpresa_precio_entry.insert(0, self._config.get("precio_sorpresa", ""))
            self._tipos_sorpresa_precio_entry.pack(side="left", padx=(0, 20))
            tk.Label(row_config, text="GRUPO:", font=("Helvetica", 11, "bold"), fg=self._primary_color, bg=self._bg_medium).pack(side="left", padx=(0, 5))
            from kool_tpv.utils.widgets.searchable_combo import SearchableCombo
            from kool_tpv.modulos.produccion.repositories.produccion_tallas_grupos_repository import ProduccionTallasGruposRepository
            repo_grupos = ProduccionTallasGruposRepository(self.db)
            opts_grupos = [(g.id, g.nombre) for g in repo_grupos.get_todos()]
            self._tipos_recargo_grupo_combo = SearchableCombo(row_config, width=150, placeholder="Seleccionar...", options=opts_grupos, module_name="shopify")
            self._tipos_recargo_grupo_combo.pack(side="left", padx=(0, 20))
            if self._config.get("recargo_grupo_id"):
                self._tipos_recargo_grupo_combo.set_by_id(int(self._config.get("recargo_grupo_id")))
            tk.Label(row_config, text="RECARGO €:", font=("Helvetica", 11), fg="#FFFFFF", bg=self._bg_medium).pack(side="left", padx=(0, 5))
            self._tipos_recargo_entry = ctk.CTkEntry(row_config, width=60, font=("Helvetica", 12))
            self._tipos_recargo_entry.insert(0, self._config.get("recargo_tallas", "0"))
            self._tipos_recargo_entry.pack(side="left")

        self._tipos_price_entries = []
        list_frame = tk.Frame(self._central_tipos, bg=self._bg_medium)
        list_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        for c in range(9): list_frame.columnconfigure(c, weight=1, uniform="tipo_var")
        headers = [("VARIANTE", 20, "w"), ("SUBIR A WEB", 0, "center"), ("PRECIO WEB", 0, "center")]
        for grupo in range(3):
            for j, (texto, ancho, anclaje) in enumerate(headers):
                tk.Label(list_frame, text=texto, font=("Helvetica", 11, "bold"), fg=self._primary_color, bg=self._bg_medium, width=ancho, anchor=anclaje).grid(row=0, column=(grupo*3)+j, padx=5, pady=8, sticky="ew")

        try:
            rows = self.db.fetch_all("SELECT id, nombre, sync_web, precio_web FROM tipos_variantes WHERE tipo_id = ? AND activo = 1 ORDER BY orden, nombre", (tipo_id,))
        except Exception: rows = []
        for i, row in enumerate(rows or []):
            v_id, nombre, sync_web, precio_web = row
            fila, col_base = (i // 3) + 1, (i % 3) * 3
            tk.Label(list_frame, text=nombre.upper(), font=("Helvetica", 11), fg="#FFFFFF", bg=self._bg_medium, anchor="w").grid(row=fila, column=col_base, sticky="w", padx=5, pady=6)
            chk_var = tk.BooleanVar(value=bool(sync_web))
            chk = ctk.CTkCheckBox(list_frame, text="", variable=chk_var, fg_color=self._primary_color, hover_color=self._secondary_color, width=20)
            chk.grid(row=fila, column=col_base + 1, padx=5, pady=6)
            chk_var.trace_add("write", lambda *a, vid=v_id, var=chk_var: self._guardar_variante(vid, sync_web=int(var.get())))
            ent = ctk.CTkEntry(list_frame, width=80, height=28, font=("Helvetica", 11), justify="center")
            ent.insert(0, self._format_precio_web(precio_web))
            ent.grid(row=fila, column=col_base + 2, padx=5, pady=6)
            self._tipos_price_entries.append((v_id, ent))

        if self.render_prompt_editor_callback:
            self.render_prompt_editor_callback(self._central_tipos, tipo_id=tipo_id)

    def _format_precio_web(self, cents: Optional[int]) -> str:
        if not cents: return "0,00€"
        return f"{cents/100:.2f}".replace('.', ',') + "€"

    def _parse_precio_web(self, texto: str) -> int:
        try:
            num_str = texto.replace('€', '').replace(',', '.').strip()
            return int(float(num_str) * 100)
        except Exception: return 0

    def _guardar_variante(self, variante_id: int, sync_web: Optional[int] = None, precio_web: Optional[int] = None):
        try:
            if sync_web is not None: self.db.execute_query("UPDATE tipos_variantes SET sync_web = ? WHERE id = ?", (sync_web, variante_id))
            if precio_web is not None: self.db.execute_query("UPDATE tipos_variantes SET precio_web = ? WHERE id = ?", (precio_web, variante_id))
        except Exception: logger.exception("Error guardando variante")

    def save_tipo_actual(self):
        if self._tipo_selected_id is None: return
        if self._tipos_template_entry and self._tipos_template_entry.winfo_exists():
            self.db.execute_query("UPDATE tipos SET template_suffix = ? WHERE id = ?", (self._tipos_template_entry.get().strip(), self._tipo_selected_id))
        if self._tipos_sorpresa_stock_entry and self._tipos_sorpresa_stock_entry.winfo_exists():
            self._config["stock_sorpresa"] = self._tipos_sorpresa_stock_entry.get()
        if self._tipos_sorpresa_precio_entry and self._tipos_sorpresa_precio_entry.winfo_exists():
            self._config["precio_sorpresa"] = self._tipos_sorpresa_precio_entry.get()
        if self._tipos_recargo_entry and self._tipos_recargo_entry.winfo_exists():
            self._config["recargo_tallas"] = self._tipos_recargo_entry.get()
        if self._tipos_recargo_grupo_combo and self._tipos_recargo_grupo_combo.winfo_exists():
            self._config["recargo_grupo_id"] = self._tipos_recargo_grupo_combo.get_id()
        for v_id, ent in self._tipos_price_entries:
            if ent.winfo_exists(): self._guardar_variante(v_id, precio_web=self._parse_precio_web(ent.get()))
