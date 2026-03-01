"""
CarritoNavList - NavList especializado para el carrito TPV
Soporta 4 tipos de línea: normal, descuento, devolución, tesoro
"""
import logging
from pathlib import Path
import json
from typing import Optional, Callable, Any
from kool_tpv.utils.widgets.nav_list import NavList

logger = logging.getLogger(__name__)


def load_config(config_name: str) -> dict:
    """Cargar archivo de configuración."""
    try:
        base = Path(__file__).resolve().parents[3]
        config_path = base / "config" / config_name
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        logger.exception(f"Error cargando {config_name}")
        return {}


class CarritoNavList(NavList):
    """NavList especializado para carrito TPV con tipos de línea y comportamiento específico."""

    def __init__(
        self,
        parent,
        on_item_change: Optional[Callable[[dict, str], None]] = None,
        keyboard_manager=None,
        **kwargs
    ):
        """
        Args:
            parent: Widget padre
            on_item_change: Callback(item_data, action) donde action = 'add' | 'remove'
            keyboard_manager: Gestor de teclado global
        """
        # Cargar configs
        colors_cfg = load_config("colors_config.json")
        fonts_cfg = load_config("font_config.json")
        layout_cfg = load_config("layout_config.json")

        # Extraer configuración específica del carrito
        self.carrito_colors = colors_cfg.get("tpv", {}).get("carrito_nav_list", {})
        self.carrito_fonts = fonts_cfg.get("modules", {}).get("tpv", {}).get("ticket_carrito", {})
        self.carrito_layout = layout_cfg.get("modules", {}).get("tpv", {}).get("carrito_nav_list", {})

        # Columnas del carrito
        col_widths = self.carrito_layout.get("column_widths", {})
        columns = [
            ("nombre", col_widths.get("producto", 180), "Producto"),
            ("cantidad", col_widths.get("cantidad", 50), "Uds"),
            ("pvp", col_widths.get("precio", 80), "Precio"),
            ("total", col_widths.get("total", 85), "Total")
        ]

        # Callback personalizado
        self.on_item_change_callback = on_item_change

        # Inicializar NavList base
        super().__init__(
            parent=parent,
            columns=columns,
            module_name="tpv",
            keyboard_manager=keyboard_manager,
            **kwargs
        )

        # Configurar colores específicos del carrito (override)
        self._apply_carrito_colors()

        # Bindings específicos del carrito
        self._setup_carrito_bindings()

        logger.info("CarritoNavList inicializado")

    def _apply_carrito_colors(self):
        """Aplicar colores específicos del carrito sobre los de NavList base."""
        try:
            line_normal = self.carrito_colors.get("line_normal", {})

            self.row_normal_bg = line_normal.get("bg", self.row_normal_bg)
            self.row_normal_text = line_normal.get("text", self.row_normal_text)
            self.row_hover_bg = line_normal.get("hover_bg", self.row_hover_bg)
            self.row_selected_bg = line_normal.get("selected_bg", self.row_selected_bg)
            self.row_selected_border = line_normal.get("selected_border", self.row_selected_border)
        except Exception:
            logger.exception("Error aplicando colores carrito")

    def _setup_carrito_bindings(self):
        """Configurar bindings específicos del carrito."""
        try:
            # Enter: añadir +1 unidad
            self._tree.bind('<Return>', lambda e: self._on_enter_key())

            # Suprimir/BackSpace: reducir -1 unidad
            self._tree.bind('<Delete>', lambda e: self._on_delete_key())
            self._tree.bind('<BackSpace>', lambda e: self._on_delete_key())
        except Exception:
            logger.exception("Error configurando bindings carrito")

    def _on_enter_key(self):
        """Handler Enter: añadir +1 unidad al item seleccionado."""
        try:
            if self.selected_index < 0:
                return

            data, _ = self.rows_data[self.selected_index]

            # No permitir añadir unidades a líneas especiales
            line_tipo = data.get("line_tipo", "normal")
            if line_tipo in ("descuento", "tesoro"):
                return

            if self.on_item_change_callback:
                self.on_item_change_callback(data, "add")

        except Exception:
            logger.exception("Error en _on_enter_key")

    def _on_delete_key(self):
        """Handler Suprimir: reducir -1 unidad al item seleccionado."""
        try:
            if self.selected_index < 0:
                return

            data, _ = self.rows_data[self.selected_index]

            if self.on_item_change_callback:
                self.on_item_change_callback(data, "remove")

        except Exception:
            logger.exception("Error en _on_delete_key")

    def add_item(self, data: dict):
        """Override: añadir item con soporte para tipos de línea."""
        try:
            # Determinar tipo de línea
            line_tipo = data.get("line_tipo", "normal")

            # Añadir item usando método padre
            super().add_item(data)

            # Aplicar estilo según tipo
            if line_tipo != "normal":
                self._apply_line_style(len(self.rows_data) - 1, line_tipo)

        except Exception:
            logger.exception("Error añadiendo item al carrito")

    def _apply_line_style(self, index: int, line_tipo: str):
        """Aplicar estilo visual según tipo de línea."""
        try:
            if index < 0 or index >= len(self.rows_data):
                return

            _, frame = self.rows_data[index]

            # Obtener colores según tipo
            tipo_colors = self.carrito_colors.get(f"line_{line_tipo}", {})
            if not tipo_colors:
                return

            bg = tipo_colors.get("bg")
            text_color = tipo_colors.get("text")

            if bg:
                frame.configure(fg_color=bg)

            if text_color:
                for child in frame.winfo_children():
                    try:
                        child.configure(text_color=text_color)
                    except Exception:
                        pass

        except Exception:
            logger.exception(f"Error aplicando estilo {line_tipo}")
