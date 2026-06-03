"""
BuscarSubView - Subvista de búsqueda de artículos.

Similar a CajeroSubView, se muestra en el grid izquierdo del TPV.
Permite buscar por categorías o tipos, mostrando los productos en scrollables.
"""
import customtkinter as ctk
from pathlib import Path
import json
import logging

from kool_tpv.base_datos.categoria_service import CategoriaService
from kool_tpv.base_datos.tipo_service import TipoService
from kool_tpv.base_datos.producto_service import ProductoService
from kool_tpv.utils.factories.button_factory import ButtonFactory
from kool_tpv.utils.widgets.clickable_breadcrumb import ClickableBreadcrumb
from kool_tpv.utils.keyboard_nav_mixin import KeyboardNavigableMixin

logger = logging.getLogger(__name__)

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


class BuscarSubView(ctk.CTkFrame, KeyboardNavigableMixin):
    """
    Subvista de búsqueda. Se muestra en el grid izquierdo del TPV.
    Reemplaza temporalmente el grid principal de botones.
    """
    
    def __init__(self, parent, db, carrito_service, on_add_callback=None, on_close_callback=None, **kwargs):
        ctk.CTkFrame.__init__(self, parent, **kwargs)
        KeyboardNavigableMixin.__init_keyboard_mixin__(self)
        
        self.db = db
        self.carrito_service = carrito_service
        self.on_add_callback = on_add_callback
        self.on_close_callback = on_close_callback
        
        self.categoria_service = CategoriaService(self.db)
        self.tipo_service = TipoService(self.db)
        self.producto_service = ProductoService(self.db)
        
        # Configs
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
        
        # Configurar navegación por teclado
        self._setup_buscar_keyboard_nav()
    
    def _get_font(self, key_name):
        font_data = self.overlay_fonts.get(key_name, {})
        return (
            font_data.get("family", "Arial"),
            font_data.get("size", 16),
            font_data.get("weight", "bold")
        )
    
    def _setup_ui(self):
        """Configurar la UI de la subvista."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # Header
        self.grid_rowconfigure(1, weight=0)  # Botones modo
        self.grid_rowconfigure(2, weight=30)  # Categorías 30%
        self.grid_rowconfigure(3, weight=70)  # Productos 70%
        
        # Configurar colores de fondo
        bg_color = self.overlay_colors.get("categories_area_bg", "#1a1a1a")
        self.configure(fg_color=bg_color)
        
        # 1. Header con breadcrumb
        bread_font = self._get_font("breadcrumb")
        bread_cfg = self.overlay_colors.get("breadcrumb", {})
        
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(5, 2))
        
        self.breadcrumb = ClickableBreadcrumb(
            header_frame,
            font=bread_font,
            text_color=bread_cfg.get("text", "white"),
            hover_color=bread_cfg.get("text_hover", "green"),
            bg_hover=bread_cfg.get("bg_hover", "#333"),
            height=30
        )
        self.breadcrumb.pack(fill='x')
        
        # 2. Botones de modo (CATEGORÍAS / TIPOS)
        top_frame = ctk.CTkFrame(self, height=80, fg_color="transparent")
        top_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        top_frame.grid_columnconfigure(0, weight=1)
        top_frame.grid_columnconfigure(1, weight=1)
        
        btn_w = self.overlay_layout.get("main_button_width", 200)
        btn_h = self.overlay_layout.get("main_button_height", 60)
        
        self.btn_cat_mode = ButtonFactory.create_button(
            parent=top_frame,
            text="CATEGORÍAS",
            command=lambda: self.cambiar_modo('categorias'),
            style_key="Busqueda_principal",
            width=btn_w,
            height=btn_h
        )
        self.btn_cat_mode.grid(row=0, column=0, padx=5, pady=5)
        
        self.btn_tipo_mode = ButtonFactory.create_button(
            parent=top_frame,
            text="TIPOS",
            command=lambda: self.cambiar_modo('tipos'),
            style_key="Busqueda_principal",
            width=btn_w,
            height=btn_h
        )
        self.btn_tipo_mode.grid(row=0, column=1, padx=5, pady=5)
        
        # 3. Zona Categorías (30%)
        bg_cat = self.overlay_colors.get("categories_area_bg", "#000")
        self.cat_frame = ctk.CTkFrame(self, fg_color=bg_cat)
        self.cat_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)
        
        self.cat_scroll = ctk.CTkScrollableFrame(self.cat_frame, fg_color="transparent")
        self.cat_scroll.pack(fill="both", expand=True, padx=5, pady=5)
        
        # 4. Zona Productos (70%)
        bg_prod = self.overlay_colors.get("articles_area_bg", "#000")
        self.prod_frame = ctk.CTkFrame(self, fg_color=bg_prod)
        self.prod_frame.grid(row=3, column=0, sticky="nsew", padx=10, pady=5)
        
        self.prod_scroll = ctk.CTkScrollableFrame(self.prod_frame, fg_color="transparent")
        self.prod_scroll.pack(fill="both", expand=True, padx=5, pady=5)
    
    def _limpiar_scroll(self, scroll_frame):
        for widget in scroll_frame.winfo_children():
            widget.destroy()
    
    def _calcular_columnas(self, scroll_frame, min_width, spacing):
        try:
            scroll_frame.update_idletasks()
            w = scroll_frame.winfo_width()
            if w < 100:
                w = 800
            return max(1, w // (min_width + spacing))
        except:
            return 4
    
    def cambiar_modo(self, nuevo_modo):
        """Cambiar entre modo categorías y tipos."""
        self.clear_keyboard_navigation()
        
        self.modo_actual = nuevo_modo
        self.seleccion_actual = None
        
        if nuevo_modo == 'categorias':
            items = self.categoria_service.get_categorias_con_productos()
            titulo = "CATEGORÍAS"
        else:
            items = self.tipo_service.get_tipos_con_productos()
            titulo = "TIPOS"
        
        self.breadcrumb.update_parts([
            ("VOLVER", self.on_close_callback),
            (titulo, None)
        ])
        self._render_categorias(items)
        self._limpiar_scroll(self.prod_scroll)
        
        self._setup_buscar_keyboard_nav()
    
    def _render_categorias(self, items):
        self._limpiar_scroll(self.cat_scroll)
        
        min_width = self.overlay_layout.get("category_button_min_width", 120)
        btn_height = self.overlay_layout.get("category_button_height", 48)
        spacing = self.overlay_layout.get("grid_spacing", 10)
        
        columnas = self._calcular_columnas(self.cat_scroll, min_width, spacing)
        
        row, col = 0, 0
        for item in items:
            btn = ButtonFactory.create_button(
                parent=self.cat_scroll,
                text=item,
                command=lambda x=item: self.seleccionar_categoria(x),
                style_key="Busqueda_categoria",
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
            titulo_modo = "CATEGORÍAS"
        else:
            items = self.tipo_service.get_tipos_con_productos()
            titulo_modo = "TIPOS"
        
        self._render_categorias(items)
        
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
        self._setup_buscar_keyboard_nav()
    
    def _render_productos(self, productos):
        self._limpiar_scroll(self.prod_scroll)
        
        min_width = self.overlay_layout.get("category_button_min_width", 120)
        btn_height = self.overlay_layout.get("article_button_height", 56)
        spacing = self.overlay_layout.get("grid_spacing", 10)
        
        columnas = self._calcular_columnas(self.prod_scroll, min_width, spacing)
        
        row, col = 0, 0
        for prod in productos:
            nombre = prod.get('nombre', '???')
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
            try:
                producto_para_carrito = self.producto_service.get_producto_para_carrito(producto_data)
            except Exception:
                producto_para_carrito = producto_data
            
            if self.carrito_service.add_item(producto_para_carrito):
                if callable(self.on_add_callback):
                    self.on_add_callback()
    
    def _setup_buscar_keyboard_nav(self):
        """Configurar navegación por teclado."""
        self._navigable_buttons = []
        
        # Botones de modo
        for btn in [self.btn_cat_mode, self.btn_tipo_mode]:
            wrapped = lambda b=btn: self._execute_btn_command(b)
            self._navigable_buttons.append((btn, wrapped))
        
        # Botones de categorías
        for child in self.cat_scroll.winfo_children():
            if isinstance(child, ctk.CTkButton):
                wrapped = lambda c=child: self._execute_btn_command(c)
                self._navigable_buttons.append((child, wrapped))
        
        # Botones de productos
        for child in self.prod_scroll.winfo_children():
            if isinstance(child, ctk.CTkButton):
                wrapped = lambda c=child: self._execute_btn_command(c)
                self._navigable_buttons.append((child, wrapped))
        
        if self._navigable_buttons:
            self._setup_keyboard_navigation()
    
    def _execute_btn_command(self, btn):
        try:
            cmd = btn.cget("command")
            if callable(cmd):
                cmd()
        except Exception:
            pass
