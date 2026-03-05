import customtkinter as ctk
from pathlib import Path
import json

# Importar services de BD
from kool_tpv.base_datos.categoria_service import CategoriaService
from kool_tpv.base_datos.tipo_service import TipoService
from kool_tpv.base_datos.producto_service import ProductoService
from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.tpv.carrito.carrito_service import CarritoService

# --- RUTAS CONFIG ---
BASE_DIR = Path(__file__).resolve().parent 
CONFIG_DIR = BASE_DIR / "kool_tpv" / "config"

def load_config(filename: str) -> dict:
    try:
        with open(CONFIG_DIR / filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

# --- BREADCRUMB ---
class ClickableBreadcrumb(ctk.CTkFrame):
    def __init__(self, parent, font=None, text_color="white", bg_color="transparent", **kwargs):
        super().__init__(parent, fg_color=bg_color, **kwargs)
        self.parts = []
        self.custom_font = font
        self.text_color = text_color

    def update_parts(self, parts: list):
        for widget in self.winfo_children():
            widget.destroy()
        self.parts = parts
        for i, (text, callback) in enumerate(parts):
            if i > 0:
                ctk.CTkLabel(self, text='/', text_color=self.text_color, font=self.custom_font).pack(side='left', padx=4)
            is_last = (i == len(parts) - 1)
            if is_last or callback is None:
                ctk.CTkLabel(self, text=text, text_color=self.text_color, font=self.custom_font).pack(side='left', padx=2)
            else:
                btn = ctk.CTkButton(
                    self, text=text, text_color=self.text_color, fg_color='transparent',
                    hover_color='#333333', font=self.custom_font, command=callback,
                    width=len(text) * 12, height=28, corner_radius=4, cursor='hand2'
                )
                btn.pack(side='left', padx=2)

# --- APP PRUEBA ---
class AppPruebaOverlay(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Conectar a la base de datos
        from pathlib import Path
        import os
        project_root = Path(__file__).resolve().parent
        db_path = project_root / "kool_tpv" / "base_datos" / "kool_bd.db"
        self.db = Database(str(db_path))
        self.db.connect()
        # Inicializar servicios
        self.carrito_service = CarritoService()

        # Crear services
        self.categoria_service = CategoriaService(self.db)
        self.tipo_service = TipoService(self.db)
        self.producto_service = ProductoService(self.db)

        # Cargar Configuraciones
        self.layout_cfg = load_config("layout_config.json")
        self.buttons_cfg = load_config("buttons_config.json")
        self.colors_cfg = load_config("colors_config.json")
        self.font_cfg = load_config("font_config.json")
        self.geometry("1600x960")
        self.title("Prueba Overlay Buscar Artículo")

        # Sidebar (Izquierda - Simulado vacío)
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color="#2B2B2B")
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Panel Derecho (Ticket)
        self.right_panel = ctk.CTkFrame(self, width=520, corner_radius=0, fg_color="#1a1a1a")
        self.right_panel.pack(side="right", fill="y")
        self.right_panel.pack_propagate(False)

        try:
            from kool_tpv.utils.widgets.ticket_carrito import TicketCarrito
            self.ticket = TicketCarrito(self.right_panel)
            self.ticket.pack(fill="both", expand=True)
            # Conectar carrito
            self.ticket.carrito_service = self.carrito_service
        except ImportError:
            ctk.CTkLabel(self.right_panel, text="ERROR TICKET", text_color="red").pack()

        # Panel Central (Aquí irá el overlay)
        self.center_area = ctk.CTkFrame(self, corner_radius=0, fg_color="#222831")
        self.center_area.pack(side="left", fill="both", expand=True)

        # Breadcrumb
        bread_font_cfg = self.font_cfg.get("breadcrumb", {})
        bread_font = (bread_font_cfg.get("family", "Courier New"), bread_font_cfg.get("size", 20), "bold")
        bread_color = self.colors_cfg.get("global", {}).get("text_matrix", "#00FF00")

        self.breadcrumb = ClickableBreadcrumb(self.center_area, font=bread_font, text_color=bread_color, height=50)
        self.breadcrumb.pack(side="top", fill="x", padx=20, pady=10)
        self.breadcrumb.update_parts([("TPV", None), ("BUSCAR ARTÍCULO", None)])

        # C) Overlay - Botones Superiores (CATEGORÍAS / TIPOS)
        overlay_layout = self.layout_cfg.get("modules", {}).get("tpv", {}).get("buscar_overlay", {})
        overlay_colors = self.colors_cfg.get("tpv", {}).get("buscar_overlay", {})
        overlay_fonts = self.font_cfg.get("modules", {}).get("tpv", {}).get("buscar_overlay", {})

        # Altura y padding desde config
        top_h = overlay_layout.get("top_buttons_height", 130)

        top_frame = ctk.CTkFrame(self.center_area, height=top_h, fg_color="transparent")
        top_frame.pack(side="top", fill="x", padx=20, pady=10)
        top_frame.pack_propagate(False)

        # Leer fuente desde config (sin hardcodear bold)
        main_btn_cfg = overlay_fonts.get("main_buttons", {})
        main_font = (
            main_btn_cfg.get("family", "Arial"), 
            main_btn_cfg.get("size", 30), 
            main_btn_cfg.get("weight", "bold")
        )

        # Leer colores desde config
        main_colors = overlay_colors.get("main_buttons", {})

        # Leer dimensiones desde config
        btn_w = overlay_layout.get("main_button_width", 250)
        btn_h = overlay_layout.get("main_button_height", 100)

        btn_cat = ctk.CTkButton(
            top_frame, text="CATEGORÍAS",
            fg_color=main_colors.get("bg"),
            hover_color=main_colors.get("hover"),
            text_color=main_colors.get("text"),
            font=main_font,
            width=btn_w, height=btn_h,
            command=self.mostrar_categorias,
            border_color=main_colors.get("border"),
            border_width=main_colors.get("border_width", 0)
        )
        btn_cat.pack(side="left", padx=6)

        btn_tipos = ctk.CTkButton(
            top_frame, text="TIPOS",
            fg_color=main_colors.get("bg"),
            hover_color=main_colors.get("hover"),
            text_color=main_colors.get("text"),
            font=main_font,
            width=btn_w, height=btn_h,
            command=self.mostrar_tipos,
            border_color=main_colors.get("border"),
            border_width=main_colors.get("border_width", 0)
        )
        btn_tipos.pack(side="left", padx=6)

        # C.2) Área Categorías (Sin fondo, expansible 50%)
        self.categories_area = ctk.CTkFrame(self.center_area, fg_color="transparent")
        self.categories_area.pack(side="top", fill="both", expand=True, padx=20, pady=10)

        self.categories_scroll = ctk.CTkScrollableFrame(self.categories_area, fg_color="transparent")
        self.categories_scroll.pack(fill="both", expand=True)

        # C.3) Área Artículos (Sin fondo, expansible 50%)
        self.articles_area = ctk.CTkFrame(self.center_area, fg_color="transparent")
        self.articles_area.pack(side="top", fill="both", expand=True, padx=20, pady=10)

        self.articles_scroll = ctk.CTkScrollableFrame(self.articles_area, fg_color="transparent")
        self.articles_scroll.pack(fill="both", expand=True)

    def mostrar_categorias(self):
        # Limpiar área
        for widget in self.categories_scroll.winfo_children():
            widget.destroy()

        # Leer configuraciones
        overlay_layout = self.layout_cfg.get("modules", {}).get("tpv", {}).get("buscar_overlay", {})
        overlay_colors = self.colors_cfg.get("tpv", {}).get("buscar_overlay", {})
        overlay_fonts = self.font_cfg.get("modules", {}).get("tpv", {}).get("buscar_overlay", {})

        # Estilos botones categoría
        cat_colors = overlay_colors.get("category_buttons", {})
        cat_font_cfg = overlay_fonts.get("category_buttons", {})
        cat_font = (cat_font_cfg.get("family", "Arial"), cat_font_cfg.get("size", 18), cat_font_cfg.get("weight", "bold"))

        # Layout
        min_width = overlay_layout.get("category_button_min_width", 120)
        btn_height = overlay_layout.get("category_button_height", 48)
        spacing = overlay_layout.get("category_grid_spacing", 10)
        
        # Obtener categorías de BD
        categorias = self.categoria_service.get_categorias_con_productos()

        # Calcular columnas dinámico
        try:
            self.categories_scroll.update_idletasks()
            ancho_disponible = max(200, self.categories_scroll.winfo_width())
            columnas = max(1, ancho_disponible // (min_width + spacing))
        except:
            columnas = 3

        # Crear grid de botones
        row = 0
        col = 0
        for cat in categorias:
            btn = ctk.CTkButton(
                self.categories_scroll, 
                text=cat,
                fg_color=cat_colors.get("bg"),
                hover_color=cat_colors.get("hover"),
                text_color=cat_colors.get("text"),
                font=cat_font,
                height=btn_height,
                border_color=cat_colors.get("border"),
                border_width=cat_colors.get("border_width", 0),
                command=lambda c=cat: self.mostrar_productos(c, 'categoria'),
            )
            btn.grid(row=row, column=col, padx=spacing, pady=spacing)

            col += 1
            if col >= columnas:
                col = 0
                row += 1

        # Configurar peso de columnas
        for i in range(columnas):
            self.categories_scroll.grid_columnconfigure(i, weight=1)

    def mostrar_tipos(self):
        # Limpiar área
        for widget in self.categories_scroll.winfo_children():
            widget.destroy()

        # Leer configuraciones
        overlay_layout = self.layout_cfg.get("modules", {}).get("tpv", {}).get("buscar_overlay", {})
        overlay_colors = self.colors_cfg.get("tpv", {}).get("buscar_overlay", {})
        overlay_fonts = self.font_cfg.get("modules", {}).get("tpv", {}).get("buscar_overlay", {})

        # Estilos botones
        cat_colors = overlay_colors.get("category_buttons", {})
        cat_font_cfg = overlay_fonts.get("category_buttons", {})
        cat_font = (cat_font_cfg.get("family", "Arial"), cat_font_cfg.get("size", 18), cat_font_cfg.get("weight", "bold"))

        # Layout
        min_width = overlay_layout.get("category_button_min_width", 120)
        btn_height = overlay_layout.get("category_button_height", 48)
        spacing = overlay_layout.get("category_grid_spacing", 10)

        # Obtener tipos de BD
        tipos = self.tipo_service.get_tipos_con_productos()

        # Calcular columnas dinámico
        try:
            self.categories_scroll.update_idletasks()
            ancho_disponible = max(200, self.categories_scroll.winfo_width())
            columnas = max(1, ancho_disponible // (min_width + spacing))
        except:
            columnas = 3

        # Crear grid de botones
        row = 0
        col = 0
        for tipo in tipos:
            btn = ctk.CTkButton(
                self.categories_scroll, 
                text=tipo,
                fg_color=cat_colors.get("bg"),
                hover_color=cat_colors.get("hover"),
                text_color=cat_colors.get("text"),
                font=cat_font,
                height=btn_height,
                border_color=cat_colors.get("border"),
                border_width=cat_colors.get("border_width", 0),
                command=lambda t=tipo: self.mostrar_productos(t, 'tipo')
            )
            btn.grid(row=row, column=col, padx=spacing, pady=spacing)

            col += 1
            if col >= columnas:
                col = 0
                row += 1

        # Configurar peso de columnas
        for i in range(columnas):
            self.categories_scroll.grid_columnconfigure(i, weight=1)

    def mostrar_productos(self, categoria_o_tipo, filtro_tipo='categoria'):
        # Limpiar área
        for widget in self.articles_scroll.winfo_children():
            widget.destroy()

        # Leer configuraciones
        overlay_layout = self.layout_cfg.get("modules", {}).get("tpv", {}).get("buscar_overlay", {})
        overlay_colors = self.colors_cfg.get("tpv", {}).get("buscar_overlay", {})
        overlay_fonts = self.font_cfg.get("modules", {}).get("tpv", {}).get("buscar_overlay", {})

        # Estilos botones artículos
        art_colors = overlay_colors.get("article_buttons", {})
        art_font_cfg = overlay_fonts.get("article_buttons", {})
        art_font = (art_font_cfg.get("family", "Arial"), art_font_cfg.get("size", 18), art_font_cfg.get("weight", "bold"))

        # Layout
        min_width = overlay_layout.get("category_button_min_width", 120)
        btn_height = overlay_layout.get("article_button_height", 56)
        spacing = overlay_layout.get("category_grid_spacing", 10)

        # Obtener productos de BD
        if filtro_tipo == 'categoria':
            productos = self.producto_service.get_productos_by_categoria(categoria_o_tipo)
        else:
            productos = self.producto_service.get_productos_by_tipo(categoria_o_tipo)

        # Calcular columnas
        try:
            self.articles_scroll.update_idletasks()
            ancho_disponible = max(200, self.articles_scroll.winfo_width())
            columnas = max(1, ancho_disponible // (min_width + spacing))
        except:
            columnas = 3

        print(f"SPACING PRODUCTOS: {spacing}")
        print(f"MIN_WIDTH PRODUCTOS: {min_width}")
        print(f"COLUMNAS CALCULADAS: {columnas}")    



        # Crear grid de botones
        row = 0
        col = 0
        for prod in productos:
            nombre = prod.get('nombre', '???')
            btn = ctk.CTkButton(
                self.articles_scroll, 
                text=nombre,
                fg_color=art_colors.get("bg"),
                hover_color=art_colors.get("hover"),
                text_color=art_colors.get("text"),
                font=art_font,
                height=btn_height,
                border_color=art_colors.get("border"),
                border_width=art_colors.get("border_width", 0),
                command=lambda p=prod: self._add_item_to_carrito(p)
            )
            btn.grid(row=row, column=col, padx=spacing, pady=spacing)

            col += 1
            if col >= columnas:
                col = 0
                row += 1

        # Configurar peso de columnas
        for i in range(columnas):
            self.articles_scroll.grid_columnconfigure(i, weight=1)        

    def _add_item_to_carrito(self, producto_data):
        """Añadir producto al carrito y refrescar ticket"""
        if self.carrito_service.add_item(producto_data):
            self.ticket.update_carrito()

if __name__ == "__main__":
    app = AppPruebaOverlay()
    app.mainloop()