"""
FavoritosSubView - Subvista de acceso rápido a productos.
Reemplaza la antigua búsqueda por categorías.
"""
import customtkinter as ctk
import logging
from typing import Optional, Dict
from PIL import Image
from pathlib import Path

from kool_tpv.utils.factories.button_factory import ButtonFactory
from .favoritos_service import FavoritosService
from kool_tpv.base_datos.producto_service import ProductoService
from kool_tpv.utils.config_loader import load_font_config, load_layout_config
from kool_tpv.utils.keyboard_nav_mixin import KeyboardNavigableMixin

logger = logging.getLogger(__name__)

class FavoritosSubView(ctk.CTkFrame, KeyboardNavigableMixin):
    def __init__(self, parent, db, carrito_service, on_add_callback=None, on_close_callback=None, on_edit_callback=None, **kwargs):
        ctk.CTkFrame.__init__(self, parent, **kwargs)
        KeyboardNavigableMixin.__init_keyboard_mixin__(self)
        
        self.db = db
        self.carrito_service = carrito_service
        self.on_add_callback = on_add_callback
        self.on_close_callback = on_close_callback
        self.on_edit_callback = on_edit_callback
        
        self.favoritos_service = FavoritosService(self.db)
        self.producto_service = ProductoService(self.db)
        
        # Variables de filtrado
        self._categoria_filtro = None  # ID de la categoría seleccionada (None = Todas)
        self._tipo_filtro = None      # ID del tipo seleccionado (None = Todos)
        self._full_items = []         # Cache de todos los favoritos cargados
        self._filter_buttons = {}     # Botones de filtro por ID de tipo
        self._categoria_buttons = {}  # Botones de filtro por ID de categoría
        
        self._icon_cache: Dict[str, ctk.CTkImage] = {}
        self._icons_dir = Path(__file__).resolve().parent.parent.parent.parent / "assets" / "iconos"
        
        self._setup_ui()
        self.cargar_favoritos()
        
        # Cleanup al destruir
        self.bind("<Destroy>", self._on_destroy)

    def _setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1) # El grid de favoritos expande
        
        # 1. Header con botón de configuración y filtros
        header_frame = ctk.CTkFrame(self, fg_color="transparent", height=120)
        header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        header_frame.grid_propagate(False)

        # Botón CONFIG para editar favoritos (arriba a la derecha)
        self.btn_edit = ButtonFactory.create_button(
            parent=header_frame,
            text="⚙️ CONFIG",
            command=self.on_edit_callback,
            style_key="action_secondary",
            width=120,
            height=40
        )
        self.btn_edit.pack(side="top", anchor="e", padx=5, pady=(0, 5))

        # Fila de categorías (arriba)
        self.categoria_container = ctk.CTkFrame(header_frame, fg_color="transparent")
        self.categoria_container.pack(side="top", fill="x", pady=(0, 5))

        # Fila de tipos (abajo)
        self.filter_container = ctk.CTkFrame(header_frame, fg_color="transparent")
        self.filter_container.pack(side="top", fill="x")

        # 2. Área de Grid (Scrollable por si hay muchos, aunque planeamos 30)
        self.scroll_container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_container.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        
        # Configurar 5 columnas para el grid
        for i in range(5):
            self.scroll_container.grid_columnconfigure(i, weight=1)

    def cargar_favoritos(self, reset_cache=True):
        # Limpiar grid de productos
        for widget in self.scroll_container.winfo_children():
            widget.destroy()
            
        # Cargar datos si es necesario
        if reset_cache or not self._full_items:
            self._full_items = self.favoritos_service.listar_favoritos()
            self._crear_botones_categoria()
            self._crear_botones_filtro()
            
        # Aplicar filtros (categoría + tipo)
        items = self._full_items
        if self._categoria_filtro is not None:
            items = [i for i in items if i.get('categoria_id') == self._categoria_filtro]
        if self._tipo_filtro is not None:
            items = [i for i in items if i.get('tipo_id') == self._tipo_filtro]
            
        # Cargar configs
        font_cfg = load_font_config()
        layout_cfg = load_layout_config()
        
        fav_font_data = font_cfg.get("modules", {}).get("tpv", {}).get("favorite_chip", {})
        fav_font = (
            fav_font_data.get("family", "Courier New"),
            fav_font_data.get("size", 14),
            fav_font_data.get("weight", "bold")
        )
        
        fav_layout = layout_cfg.get("modules", {}).get("tpv", {}).get("favorites", {})
        cols = fav_layout.get("columns", 6)
        chip_h = fav_layout.get("chip_height", 70)
        spacing = fav_layout.get("grid_spacing", 5)
        max_chars = fav_layout.get("max_chars_line", 15)

        if not items:
            ctk.CTkLabel(
                self.scroll_container, 
                text="NO HAY PRODUCTOS EN FAVORITOS.\nPULSA EL BOTÓN CONFIG PARA AÑADIR.",
                font=fav_font,
                text_color="#666666"
            ).grid(row=0, column=0, columnspan=cols, pady=50)
            self._setup_keyboard_navigation()
            return

        row, col = 0, 0
        # Configurar columnas dinámicamente
        for i in range(cols):
            self.scroll_container.grid_columnconfigure(i, weight=1)

        # Limpiar navegación anterior
        self._navigable_buttons = []

        # Añadir botones de categoría primero (arriba)
        for cid, btn in self._categoria_buttons.items():
            self._navigable_buttons.append((btn, lambda b=btn: self._execute_btn_command(b)))
        # Añadir botones de tipo segundo (medio)
        for tid, btn in self._filter_buttons.items():
            self._navigable_buttons.append((btn, lambda b=btn: self._execute_btn_command(b)))

        for item in items:
            # Crear el Chip de favorito
            color = item.get('color') or "#333333"
            nombre_raw = item.get('nombre_favorito') or item.get('nombre_producto') or "???"
            
            # Cargar icono si existe
            icono_name = item.get('icono')
            # Tamaño más pequeño para el lateral (aprox 40% del alto del chip)
            icon_size = int(chip_h * 0.45)
            ctk_img = self._get_icon_image(icono_name, icon_size) if icono_name else None
            
            # Auto-wrap del nombre basado en el config
            nombre_formateado = self._wrap_text(nombre_raw, max_chars)
            
            precio = f"{item.get('pvp', 0.00):.2f}€"
            
            # Botón personalizado (Chip)
            btn = ctk.CTkButton(
                self.scroll_container,
                text=f"{nombre_formateado}\n{precio}",
                font=fav_font,
                fg_color=color,
                hover_color=self._adjust_color_brightness(color, 0.2),
                text_color=self._get_text_color_for_bg(color),
                height=chip_h, 
                corner_radius=8,
                border_width=0,
                border_color="#00FF00",
                image=ctk_img,
                compound="left", # Icono a la izquierda
                command=lambda p=item: self._add_to_cart(p)
            )
            btn.grid(row=row, column=col, padx=spacing, pady=spacing, sticky="nsew")
            
            # Añadir a navegación
            self._navigable_buttons.append((btn, lambda b=btn: self._execute_btn_command(b)))
            
            col += 1
            if col >= cols:
                col = 0
                row += 1

        # Activar navegación por teclado
        self._setup_keyboard_navigation()

    def _execute_btn_command(self, btn):
        """Ejecutar comando de un botón."""
        try:
            cmd = btn.cget("command")
            if callable(cmd):
                cmd()
        except Exception:
            pass

    def _on_destroy(self, event):
        """Limpiar navegación por teclado al destruir la subvista."""
        self.clear_keyboard_navigation()

    def _crear_botones_filtro(self):
        """Crea dinámicamente los botones de filtro por tipo en el header.
        Si hay categoría seleccionada, solo muestra los tipos de esa categoría."""
        # Limpiar botones anteriores
        for widget in self.filter_container.winfo_children():
            widget.destroy()
        self._filter_buttons = {}

        if not self._full_items:
            return

        # Filtrar items por categoría si hay una seleccionada
        items_filtrados = self._full_items
        if self._categoria_filtro is not None:
            items_filtrados = [i for i in self._full_items if i.get('categoria_id') == self._categoria_filtro]

        # Extraer tipos únicos de los items filtrados
        tipos_dict = {}
        for item in items_filtrados:
            t_id = item.get('tipo_id')
            if t_id and t_id not in tipos_dict:
                tipos_dict[t_id] = {
                    "nombre": item.get('tipo_nombre', "Sin Tipo"),
                    "icono": item.get('icono'),
                    "color": item.get('tipo_color') or "#333333"
                }

        # Botón "TODOS"
        btn_todos = ctk.CTkButton(
            self.filter_container,
            text="TODOS",
            width=108,  # 80 * 1.35
            height=54, # 40 * 1.35
            font=("Courier New", 14, "bold"),
            fg_color="#333333",
            text_color=self._get_text_color_for_bg("#333333"),
            border_width=0,
            border_color="#00FF00",
            command=lambda: self._aplicar_filtro(None)
        )
        btn_todos.pack(side="left", padx=5)
        self._filter_buttons[None] = btn_todos

        # Botones por tipo
        for t_id, t_info in tipos_dict.items():
            # Icono un poco más grande para acompañar al botón (35px aprox)
            icono_img = self._get_icon_image(t_info["icono"], 35)
            
            btn = ctk.CTkButton(
                self.filter_container,
                text=t_info["nombre"] if not icono_img else "",
                image=icono_img,
                width=68,  # 50 * 1.35
                height=54, # 40 * 1.35
                font=("Courier New", 12, "bold"),
                fg_color=t_info["color"],
                text_color=self._get_text_color_for_bg(t_info["color"]),
                border_width=0,
                border_color="#00FF00",
                command=lambda tid=t_id: self._aplicar_filtro(tid)
            )
            btn.pack(side="left", padx=2)
            self._filter_buttons[t_id] = btn
            
        self._resaltar_filtro_activo()

    def _aplicar_filtro(self, tipo_id):
        """Aplica el filtro de tipo y repinta el grid."""
        self._tipo_filtro = tipo_id
        self.cargar_favoritos(reset_cache=False)
        self._resaltar_filtro_activo()

    def _aplicar_filtro_categoria(self, categoria_id):
        """Aplica el filtro de categoría, resetea el de tipo y repinta."""
        self._categoria_filtro = categoria_id
        self._tipo_filtro = None  # Resetear filtro de tipo al cambiar categoría
        self._crear_botones_filtro()  # Recrear tipos para la nueva categoría
        self.cargar_favoritos(reset_cache=False)
        self._resaltar_categoria_activa()

    def _resaltar_filtro_activo(self):
        """Resalta el botón de tipo activo con un borde verde, manteniendo su color original."""
        for tid, btn in self._filter_buttons.items():
            if tid == self._tipo_filtro:
                btn.configure(border_width=3, border_color="#00FF00")
            else:
                btn.configure(border_width=0)

    def _resaltar_categoria_activa(self):
        """Resalta el botón de categoría activo con un borde verde, manteniendo su color original."""
        for cid, btn in self._categoria_buttons.items():
            if cid == self._categoria_filtro:
                btn.configure(border_width=3, border_color="#00FF00")
            else:
                btn.configure(border_width=0)

    def _crear_botones_categoria(self):
        """Crea dinámicamente los botones de filtro por categoría en el header."""
        # Limpiar botones anteriores
        for widget in self.categoria_container.winfo_children():
            widget.destroy()
        self._categoria_buttons = {}

        if not self._full_items:
            return

        # Extraer categorías únicas
        cats_dict = {}
        for item in self._full_items:
            c_id = item.get('categoria_id')
            if c_id and c_id not in cats_dict:
                cats_dict[c_id] = {
                    "nombre": item.get('categoria_nombre', "Sin Categoría"),
                    "color": item.get('categoria_color') or "#333333"
                }

        # Botón "TODAS"
        btn_todas = ctk.CTkButton(
            self.categoria_container,
            text="TODAS",
            width=108,
            height=40,
            font=("Courier New", 14, "bold"),
            fg_color="#333333",
            text_color=self._get_text_color_for_bg("#333333"),
            border_width=0,
            border_color="#00FF00",
            command=lambda: self._aplicar_filtro_categoria(None)
        )
        btn_todas.pack(side="left", padx=5)
        self._categoria_buttons[None] = btn_todas

        # Botones por categoría
        for c_id, c_info in cats_dict.items():
            btn = ctk.CTkButton(
                self.categoria_container,
                text=c_info["nombre"],
                width=100,
                height=40,
                font=("Courier New", 12, "bold"),
                fg_color=c_info["color"],
            text_color=self._get_text_color_for_bg(c_info["color"]),
                border_width=0,
                border_color="#00FF00",
                command=lambda cid=c_id: self._aplicar_filtro_categoria(cid)
            )
            btn.pack(side="left", padx=2)
            self._categoria_buttons[c_id] = btn

        self._resaltar_categoria_activa()

    def _get_icon_image(self, icon_name: str, size: int) -> Optional[ctk.CTkImage]:
        """Obtener y cachear la imagen del icono."""
        if not icon_name:
            return None
            
        cache_key = f"{icon_name}_{size}"
        if cache_key in self._icon_cache:
            return self._icon_cache[cache_key]
            
        icon_path = self._icons_dir / icon_name
        if not icon_path.exists():
            return None
            
        try:
            pil_img = Image.open(icon_path).convert("RGBA")
            
            # Aplicar opacidad (50%)
            alpha = pil_img.split()[3]
            alpha = alpha.point(lambda p: int(p * 0.50))
            pil_img.putalpha(alpha)
            
            ctk_img = ctk.CTkImage(
                light_image=pil_img,
                dark_image=pil_img,
                size=(size, size)
            )
            self._icon_cache[cache_key] = ctk_img
            return ctk_img
        except Exception:
            logger.warning(f"No se pudo cargar el icono: {icon_path}")
            return None

    def _wrap_text(self, text, max_width):
        """Trocea el texto en múltiples líneas si supera el ancho máximo."""
        import textwrap
        try:
            lines = textwrap.wrap(text, width=max_width)
            return "\n".join(lines)
        except Exception:
            return text

    def _add_to_cart(self, fav_item):
        """Añadir el producto al carrito usando los datos del favorito."""
        if not self.carrito_service:
            return
            
        try:
            # Necesitamos el objeto producto completo para el carrito
            producto_id = fav_item.get('producto_id')
            producto_data = self.producto_service.get_producto_para_carrito(producto_id)
            
            # Intentar usar el controlador de la vista TPV para añadir con lógica de PVP variable
            try:
                # Buscar TpvView ascendiendo en la jerarquía
                parent = self.master
                tpv_view = None
                while parent:
                    if hasattr(parent, 'controller') and parent.controller:
                        tpv_view = parent
                        break
                    if hasattr(parent, 'master'):
                        parent = parent.master
                    else:
                        break
                
                if tpv_view and hasattr(tpv_view.controller, 'handle_add_product'):
                    tpv_view.controller.handle_add_product(producto_data)
                    return # handle_add_product se encarga de todo
            except Exception:
                logger.exception("Error intentando usar controller para añadir item")

            if self.carrito_service.add_item(producto_data):
                if callable(self.on_add_callback):
                    self.on_add_callback()
        except Exception:
            logger.exception("Error añadiendo favorito al carrito")

    def _get_text_color_for_bg(self, hex_color):
        """Devuelve 'black' o 'white' según la luminancia del color de fondo."""
        try:
            hex_color = hex_color.lstrip('#')
            r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
            # Fórmula de luminancia relativa (ITU-R BT.601)
            luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
            return "black" if luminance > 0.6 else "white"
        except Exception:
            return "white"

    def _adjust_color_brightness(self, hex_color, factor):
        """Ajustar el brillo de un color hex para el efecto hover."""
        try:
            hex_color = hex_color.lstrip('#')
            rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            new_rgb = []
            for c in rgb:
                res = int(c + (255 - c) * factor) if factor > 0 else int(c * (1 + factor))
                new_rgb.append(max(0, min(255, res)))
            return '#{:02x}{:02x}{:02x}'.format(*new_rgb)
        except Exception:
            return hex_color
