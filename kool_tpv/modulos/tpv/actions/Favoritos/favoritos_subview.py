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

logger = logging.getLogger(__name__)

class FavoritosSubView(ctk.CTkFrame):
    def __init__(self, parent, db, carrito_service, on_add_callback=None, on_close_callback=None, on_edit_callback=None, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.db = db
        self.carrito_service = carrito_service
        self.on_add_callback = on_add_callback
        self.on_close_callback = on_close_callback
        self.on_edit_callback = on_edit_callback
        
        self.favoritos_service = FavoritosService(self.db)
        self.producto_service = ProductoService(self.db)
        
        self._icon_cache: Dict[str, ctk.CTkImage] = {}
        self._icons_dir = Path("/Volumes/ALMACEN/KOOL_THINGS/KOOL_TPV_V2/kool_tpv/assets/iconos")
        
        self._setup_ui()
        self.cargar_favoritos()

    def _setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1) # El grid de favoritos expande
        
        # 1. Header con botones de acción
        header_frame = ctk.CTkFrame(self, fg_color="transparent", height=60)
        header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        header_frame.grid_propagate(False)
        
        # Botón Volver (Estilo Breadcrumb manual)
        btn_back = ctk.CTkButton(
            header_frame,
            text="< VOLVER",
            font=("Courier New", 16, "bold"),
            fg_color="transparent",
            text_color="#00FF00",
            hover_color="#333333",
            width=100,
            command=self.on_close_callback
        )
        btn_back.pack(side="left", padx=5)
        
        ctk.CTkLabel(
            header_frame,
            text="FAVORITOS",
            font=("Courier New", 20, "bold"),
            text_color="#00FF00"
        ).pack(side="left", padx=20)

        # Botón EDITAR (para el paso 4)
        self.btn_edit = ButtonFactory.create_button(
            parent=header_frame,
            text="⚙️ CONFIG",
            command=self.on_edit_callback,
            style_key="action_secondary",
            width=120,
            height=40
        )
        self.btn_edit.pack(side="right", padx=5)

        # 2. Área de Grid (Scrollable por si hay muchos, aunque planeamos 30)
        self.scroll_container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_container.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        
        # Configurar 5 columnas para el grid
        for i in range(5):
            self.scroll_container.grid_columnconfigure(i, weight=1)

    def cargar_favoritos(self):
        # Limpiar grid actual
        for widget in self.scroll_container.winfo_children():
            widget.destroy()
            
        items = self.favoritos_service.listar_favoritos()
        
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
            return

        row, col = 0, 0
        # Configurar columnas dinámicamente
        for i in range(cols):
            self.scroll_container.grid_columnconfigure(i, weight=1)

        for item in items:
            # Crear el Chip de favorito
            color = item.get('color') or "#333333"
            nombre_raw = item.get('nombre_favorito') or item.get('nombre_producto') or "???"
            
            # Cargar icono si existe
            icono_name = item.get('icono')
            ctk_img = self._get_icon_image(icono_name, chip_h - 20) if icono_name else None
            
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
                text_color="white",
                height=chip_h, 
                corner_radius=8,
                image=ctk_img,
                compound="top", # Icono arriba, texto abajo (más fiable que 'center')
                command=lambda p=item: self._add_to_cart(p)
            )
            btn.grid(row=row, column=col, padx=spacing, pady=spacing, sticky="nsew")
            
            col += 1
            if col >= cols:
                col = 0
                row += 1

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
            pil_img = Image.open(icon_path)
            # El icono se usa como marca de agua, así que si es necesario podrías bajar opacidad aquí
            # Pero confiamos en que el usuario suba iconos blancos/sutiles.
            
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
            
            if self.carrito_service.add_item(producto_data):
                if callable(self.on_add_callback):
                    self.on_add_callback()
        except Exception:
            logger.exception("Error añadiendo favorito al carrito")

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
