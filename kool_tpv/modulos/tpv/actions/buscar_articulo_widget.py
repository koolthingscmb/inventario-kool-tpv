import customtkinter as ctk
from pathlib import Path
import json
import logging

# Importar services
from kool_tpv.base_datos.categoria_service import CategoriaService
from kool_tpv.base_datos.tipo_service import TipoService
from kool_tpv.base_datos.producto_service import ProductoService

logger = logging.getLogger(__name__)

# --- CARGA DE CONFIGURACIÓN ---
BASE_DIR = Path(__file__).resolve().parents[4] 
CONFIG_DIR = BASE_DIR / "kool_tpv" / "config"

def load_config(filename: str) -> dict:
    try:
        path = CONFIG_DIR / filename
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}

# --- BREADCRUMB ---
class ClickableBreadcrumb(ctk.CTkFrame):
    def __init__(self, parent, font=None, text_color="white", hover_color="white", bg_hover="transparent", bg_color="transparent", **kwargs):
        super().__init__(parent, fg_color=bg_color, **kwargs)
        self.custom_font = font
        self.text_color = text_color
        self.hover_color = hover_color
        self.bg_hover = bg_hover

    def update_parts(self, parts: list):
        for widget in self.winfo_children():
            widget.destroy()

        for i, (text, callback) in enumerate(parts):
            if i > 0:
                ctk.CTkLabel(self, text='/', text_color=self.text_color, font=self.custom_font).pack(side='left', padx=4)

            if callback is None:
                ctk.CTkLabel(self, text=text, text_color=self.text_color, font=self.custom_font).pack(side='left', padx=2)
            else:
                btn = ctk.CTkButton(
                    self, text=text, 
                    text_color=self.text_color, 
                    fg_color='transparent',
                    font=self.custom_font, 
                    command=callback,
                    width=len(text) * 12, height=28, corner_radius=4, cursor='hand2'
                )
                btn.bind("<Enter>", lambda e, b=btn: b.configure(text_color=self.hover_color, fg_color=self.bg_hover))
                btn.bind("<Leave>", lambda e, b=btn: b.configure(text_color=self.text_color, fg_color='transparent'))
                btn.pack(side='left', padx=2)

# --- WIDGET PRINCIPAL ---
class BuscarArticuloWidget(ctk.CTkFrame):
    def __init__(self, parent, db, carrito_service, on_add_callback=None, on_close_callback=None, **kwargs):
        super().__init__(parent, **kwargs)

        self.db = db
        self.carrito_service = carrito_service
        self.on_add_callback = on_add_callback
        self.on_close_callback = on_close_callback

        self.categoria_service = CategoriaService(self.db)
        self.tipo_service = TipoService(self.db)
        self.producto_service = ProductoService(self.db)

        self.layout_cfg = load_config("layout_config.json")
        self.colors_cfg = load_config("colors_config.json")
        self.font_cfg = load_config("font_config.json")

        self.overlay_layout = self.layout_cfg.get("modules", {}).get("tpv", {}).get("buscar_overlay", {})
        self.overlay_colors = self.colors_cfg.get("tpv", {}).get("buscar_overlay", {})
        self.overlay_fonts = self.font_cfg.get("modules", {}).get("tpv", {}).get("buscar_overlay", {})

        self.modo_actual = 'categorias'
        self.seleccion_actual = None    

        self._setup_ui()
        self.cambiar_modo('categorias')

    def _get_font(self, key_name):
        font_data = self.overlay_fonts.get(key_name, {})
        return (
            font_data.get("family", "Arial"),
            font_data.get("size", 16),
            font_data.get("weight", "bold")
        )

    def _setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=0)
        self.grid_rowconfigure(2, weight=30) # 30% Categorías
        self.grid_rowconfigure(3, weight=70) # 70% Productos

        # 1+2. Header area (breadcrumb + top buttons) inside a container so we
        # can reserve space for the global power button at the left.
        bread_font = self._get_font("breadcrumb")
        bread_cfg = self.overlay_colors.get("breadcrumb", {})

        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(10, 5))
        header_frame.pack_propagate(False)

        # Try to reserve the power-space using the app helper if available
        try:
            app = self.winfo_toplevel()
        except Exception:
            app = None

        spacer = None
        try:
            if app is not None and hasattr(app, 'reserve_power_space'):
                try:
                    spacer = app.reserve_power_space(header_frame, margin=12)
                except Exception:
                    spacer = None
        except Exception:
            spacer = None

        if spacer is None:
            spacer = ctk.CTkFrame(header_frame, width=12, height=12, fg_color="transparent")

        spacer.pack(side='left')

        # Content container holds breadcrumb (top row) and top buttons (below)
        content_container = ctk.CTkFrame(header_frame, fg_color="transparent")
        content_container.pack(side='left', fill='both', expand=True)

        self.breadcrumb = ClickableBreadcrumb(
            content_container,
            font=bread_font,
            text_color=bread_cfg.get("text", "white"),
            hover_color=bread_cfg.get("text_hover", "green"),
            bg_hover=bread_cfg.get("bg_hover", "#333"),
            height=40
        )
        self.breadcrumb.pack(fill='x', pady=(0, 5))

        # 2. Botones Superiores
        top_h = self.overlay_layout.get("top_buttons_height", 130)
        top_frame = ctk.CTkFrame(content_container, height=top_h, fg_color="transparent")
        top_frame.pack(fill='x')
        top_frame.pack_propagate(False)

        btn_w = self.overlay_layout.get("main_button_width", 250)
        btn_h = self.overlay_layout.get("main_button_height", 100)
        main_font = self._get_font("main_buttons")
        main_colors = self.overlay_colors.get("main_buttons", {})

        self.btn_cat_mode = ctk.CTkButton(
            top_frame, text="CATEGORÍAS",
            fg_color=main_colors.get("bg", "#000"),
            hover_color=main_colors.get("hover", "#333"),
            text_color=main_colors.get("text", "#FFF"),
            font=main_font, width=btn_w, height=btn_h,
            border_color=main_colors.get("border", "#0F0"),
            border_width=main_colors.get("border_width", 2),
            command=lambda: self.cambiar_modo('categorias')
        )
        self.btn_cat_mode.pack(side="left", padx=6)

        self.btn_tipo_mode = ctk.CTkButton(
            top_frame, text="TIPOS",
            fg_color=main_colors.get("bg", "#000"),
            hover_color=main_colors.get("hover", "#333"),
            text_color=main_colors.get("text", "#FFF"),
            font=main_font, width=btn_w, height=btn_h,
            border_color=main_colors.get("border", "#0F0"),
            border_width=main_colors.get("border_width", 2),
            command=lambda: self.cambiar_modo('tipos')
        )
        self.btn_tipo_mode.pack(side="left", padx=6)

        # 3. Zona Categorías
        bg_cat = self.overlay_colors.get("categories_area_bg", "#000")
        self.cat_frame = ctk.CTkFrame(self, fg_color=bg_cat)
        self.cat_frame.grid(row=2, column=0, sticky="nsew", padx=20, pady=5)

        self.cat_scroll = ctk.CTkScrollableFrame(self.cat_frame, fg_color="transparent")
        self.cat_scroll.pack(fill="both", expand=True, padx=5, pady=5)

        # 4. Zona Productos
        bg_prod = self.overlay_colors.get("articles_area_bg", "#000")
        self.prod_frame = ctk.CTkFrame(self, fg_color=bg_prod)
        self.prod_frame.grid(row=3, column=0, sticky="nsew", padx=20, pady=5)

        self.prod_scroll = ctk.CTkScrollableFrame(self.prod_frame, fg_color="transparent")
        self.prod_scroll.pack(fill="both", expand=True, padx=5, pady=5)

    def _limpiar_scroll(self, scroll_frame):
        for widget in scroll_frame.winfo_children():
            widget.destroy()

    def _calcular_columnas(self, scroll_frame, min_width, spacing):
        try:
            scroll_frame.update_idletasks()
            w = scroll_frame.winfo_width()
            if w < 100: w = 800
            return max(1, w // (min_width + spacing))
        except:
            return 4

    def cambiar_modo(self, nuevo_modo):
        self.modo_actual = nuevo_modo
        self.seleccion_actual = None

        colors = self.overlay_colors.get("main_buttons", {})
        active_bg = colors.get("bg_active", "#00FF9D")
        normal_bg = colors.get("bg", "#000")
        active_txt = colors.get("text_active", "#000")
        normal_txt = colors.get("text", "#00FF9D")

        if nuevo_modo == 'categorias':
            self.btn_cat_mode.configure(fg_color=active_bg, text_color=active_txt)
            self.btn_tipo_mode.configure(fg_color=normal_bg, text_color=normal_txt)
            items = self.categoria_service.get_categorias_con_productos()
            titulo = "CATEGORÍAS"
        else:
            self.btn_cat_mode.configure(fg_color=normal_bg, text_color=normal_txt)
            self.btn_tipo_mode.configure(fg_color=active_bg, text_color=active_txt)
            items = self.tipo_service.get_tipos_con_productos()
            titulo = "TIPOS"

        self.breadcrumb.update_parts([("VOLVER", self.on_close_callback), (titulo, None)])
        self._render_categorias(items)
        self._limpiar_scroll(self.prod_scroll)

    def _render_categorias(self, items):
        self._limpiar_scroll(self.cat_scroll)

        min_width = self.overlay_layout.get("category_button_min_width", 120)
        btn_height = self.overlay_layout.get("category_button_height", 48)
        spacing = self.overlay_layout.get("grid_spacing", 10)
        font = self._get_font("category_buttons")
        colors = self.overlay_colors.get("category_buttons", {})

        columnas = self._calcular_columnas(self.cat_scroll, min_width, spacing)

        row, col = 0, 0
        for item in items:
            is_selected = (item == self.seleccion_actual)
            bg = colors.get("bg_selected", "#00FF9D") if is_selected else colors.get("bg", "#222")
            fg = colors.get("text_selected", "#000") if is_selected else colors.get("text", "#FFF")

            btn = ctk.CTkButton(
                self.cat_scroll, text=item,
                fg_color=bg, hover_color=colors.get("hover", "#333"),
                text_color=fg,
                height=btn_height, font=font,
                border_color=colors.get("border", "#fff"),
                border_width=colors.get("border_width", 0),
                command=lambda x=item: self.seleccionar_categoria(x)
            )
            btn.grid(row=row, column=col, padx=spacing, pady=spacing, sticky="ew")
            col += 1
            if col >= columnas:
                col = 0
                row += 1

        for i in range(columnas):
            self.cat_scroll.grid_columnconfigure(i, weight=1)

    def seleccionar_categoria(self, nombre):
        self.seleccion_actual = nombre

        if self.modo_actual == 'categorias':
            items = self.categoria_service.get_categorias_con_productos()
        else:
            items = self.tipo_service.get_tipos_con_productos()
        self._render_categorias(items)

        titulo_modo = "CATEGORÍAS" if self.modo_actual == 'categorias' else "TIPOS"
        self.breadcrumb.update_parts([
            ("VOLVER", self.on_close_callback), 
            (titulo_modo, lambda: self.cambiar_modo(self.modo_actual)), 
            (str(nombre).upper(), None)
        ])

        if self.modo_actual == 'categorias':
            productos = self.producto_service.get_productos_by_categoria(nombre)
        else:
            productos = self.producto_service.get_productos_by_tipo(nombre)

        self._render_productos(productos)

    def _render_productos(self, productos):
        self._limpiar_scroll(self.prod_scroll)

        min_width = self.overlay_layout.get("category_button_min_width", 120)
        btn_height = self.overlay_layout.get("article_button_height", 56)
        spacing = self.overlay_layout.get("grid_spacing", 10)
        font = self._get_font("article_buttons")
        colors = self.overlay_colors.get("article_buttons", {})

        columnas = self._calcular_columnas(self.prod_scroll, min_width, spacing)

        row, col = 0, 0
        for prod in productos:
            nombre = prod.get('nombre', '???')
            hover_bg = colors.get("hover", "#00FF9D")
            hover_text = colors.get("text_hover", "#000")

            btn = ctk.CTkButton(
                self.prod_scroll, text=nombre,
                fg_color=colors.get("bg", "#333"),
                text_color=colors.get("text", "white"),
                height=btn_height, font=font,
                border_color=colors.get("border", "#fff"),
                border_width=colors.get("border_width", 0),
                command=lambda p=prod: self._add_item_to_carrito(p)
            )
            btn.configure(hover_color=hover_bg)
            btn.bind("<Enter>", lambda e, b=btn: b.configure(text_color=hover_text))
            btn.bind("<Leave>", lambda e, b=btn, tc=colors.get("text", "white"): b.configure(text_color=tc))

            btn.grid(row=row, column=col, padx=spacing, pady=spacing, sticky="ew")

            col += 1
            if col >= columnas:
                col = 0
                row += 1

        for i in range(columnas):
            self.prod_scroll.grid_columnconfigure(i, weight=1)

    def _add_item_to_carrito(self, producto_data):
        if self.carrito_service:
            if self.carrito_service.add_item(producto_data):
                if callable(self.on_add_callback):
                    self.on_add_callback()