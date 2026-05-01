import customtkinter as ctk
from pathlib import Path
import json
import logging

# Importar services
from kool_tpv.base_datos.categoria_service import CategoriaService
from kool_tpv.base_datos.tipo_service import TipoService
from kool_tpv.base_datos.producto_service import ProductoService
from kool_tpv.utils.factories.button_factory import ButtonFactory
from kool_tpv.utils.widgets.clickable_breadcrumb import ClickableBreadcrumb

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
        # Calcular ancho requerido para reservar espacio del botón Power desde layout_config
        power_cfg = self.layout_cfg.get('global', {}).get('power_layout', {})
        spacer_w = power_cfg.get('width', 140) + power_cfg.get('collision_margin', 18)

        try:
            if app is not None and hasattr(app, 'reserve_power_space'):
                try:
                    spacer = app.reserve_power_space(header_frame, margin=12)
                except Exception:
                    spacer = None
        except Exception:
            spacer = None

        if spacer is None:
            spacer = ctk.CTkFrame(header_frame, width=spacer_w, height=12, fg_color="transparent")

        spacer.pack(side='left')

        # Content container holds breadcrumb (top row) and top buttons (below)
        content_container = ctk.CTkFrame(header_frame, fg_color="transparent")
        content_container.pack(side='right', fill='both', expand=True)

        self.breadcrumb = ClickableBreadcrumb(
            content_container,
            font=bread_font,
            text_color=bread_cfg.get("text", "white"),
            hover_color=bread_cfg.get("text_hover", "green"),
            bg_hover=bread_cfg.get("bg_hover", "#333"),
            height=40,
            left_padding=spacer_w
        )
        self.breadcrumb.pack(fill='x', pady=(0, 5))

        # 2. Botones Superiores
        top_h = self.overlay_layout.get("top_buttons_height", 130)
        top_frame = ctk.CTkFrame(content_container, height=top_h, fg_color="transparent")
        top_frame.pack(fill='x')
        top_frame.pack_propagate(False)

        # Frame dedicado para los botones, centrado usando grid en top_frame
        top_frame.grid_columnconfigure(0, weight=1)
        top_frame.grid_columnconfigure(1, weight=0)
        top_frame.grid_columnconfigure(2, weight=1)

        button_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
        button_frame.grid(row=0, column=1)
        self._button_frame = button_frame

        btn_w = self.overlay_layout.get("main_button_width", 250)
        btn_h = self.overlay_layout.get("main_button_height", 100)
        main_font = self._get_font("main_buttons")
        # Create top buttons using central ButtonFactory
        self.btn_cat_mode = ButtonFactory.create_button(
            parent=button_frame,
            text="CATEGORÍAS",
            command=lambda: self.cambiar_modo('categorias'),
            style_key="Busqueda_principal",
            width=btn_w,
            height=btn_h
        )
        self.btn_cat_mode.pack(side="left", padx=6)

        self.btn_tipo_mode = ButtonFactory.create_button(
            parent=button_frame,
            text="TIPOS",
            command=lambda: self.cambiar_modo('tipos'),
            style_key="Busqueda_principal",
            width=btn_w,
            height=btn_h
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

        # Determine items and title based on mode; visual state is handled by styles
        if nuevo_modo == 'categorias':
            items = self.categoria_service.get_categorias_con_productos()
            titulo = "CATEGORÍAS"
        else:
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

        columnas = self._calcular_columnas(self.cat_scroll, min_width, spacing)

        row, col = 0, 0
        for item in items:
            is_selected = (item == self.seleccion_actual)
            style = "Busqueda_categoria"

            btn = ButtonFactory.create_button(
                parent=self.cat_scroll,
                text=item,
                command=lambda x=item: self.seleccionar_categoria(x),
                style_key=style,
                height=btn_height
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

            # Choose product style depending on current search mode
            style = "Busqueda_categoria_prod" if self.modo_actual == 'categorias' else "Busqueda_tipo_prod"

            btn = ButtonFactory.create_button(
                parent=self.prod_scroll,
                text=nombre,
                command=lambda p=prod: self._add_item_to_carrito(p),
                style_key=style,
                height=btn_height
            )

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