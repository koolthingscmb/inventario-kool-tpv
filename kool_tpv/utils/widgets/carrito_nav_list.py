"""
CarritoNavList - NavList especializado para el carrito TPV
Soporta 4 tipos de línea: normal, descuento, devolución, tesoro
"""
import logging
from pathlib import Path
import json
from typing import Optional, Callable, Any, List
from kool_tpv.utils.widgets.virtual_nav_list import VirtualNavList

logger = logging.getLogger(__name__)


def load_config(config_name: str) -> dict:
    """Cargar archivo de configuración."""
    try:
        base = Path(__file__).resolve().parents[2]
        config_path = base / "config" / config_name
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        logger.exception(f"Error cargando {config_name}")
        return {}


class CarritoNavList(VirtualNavList):
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

        # Inicializar VirtualNavList base
        super().__init__(
            parent=parent,
            columns=columns,
            module_name="tpv",
            keyboard_manager=keyboard_manager,
            row_color_callback=self._get_row_color,
            **kwargs
        )

        # Configurar colores específicos del carrito (override)
        self._apply_carrito_colors()

        logger.info("CarritoNavList virtualizado inicializado")

        # Bindings específicos del carrito
        self._setup_carrito_bindings()

    def _get_row_color(self, data: dict, index: int) -> dict:
        """Determinar color de fila según el tipo de línea."""
        line_tipo = data.get("line_tipo", "normal")
        if line_tipo == "normal":
            return {}
        
        tipo_colors = self.carrito_colors.get(f"line_{line_tipo}", {})
        return {
            'bg': tipo_colors.get("bg"),
            'fg': tipo_colors.get("text")
        }

    def _apply_carrito_colors(self):
        """Aplicar colores específicos del carrito sobre los de NavList base."""
        try:
            line_normal = self.carrito_colors.get("line_normal", {})

            self.row_normal_bg = line_normal.get("bg", self.row_normal_bg)
            self.row_normal_text = line_normal.get("text", self.row_normal_text)
            self.row_selected_bg = line_normal.get("selected_bg", self.row_selected_bg)
            self.row_selected_text = line_normal.get("selected_text", self.row_selected_text)
            self.row_selected_border = line_normal.get("selected_border", self.row_selected_border)
        except Exception:
            logger.exception("Error aplicando colores carrito")

    def add_item(self, item_data: dict):
        """Método de compatibilidad para añadir un solo item."""
        # En una lista virtual es más eficiente usar set_items con toda la lista,
        # pero esto permite compatibilidad con el código actual de TicketCarrito.
        current_items = list(self._all_data)
        current_items.append(item_data)
        self.set_items(current_items)

    def _setup_carrito_bindings(self):
        """Configurar bindings específicos del carrito."""
        try:
            # Hacer bind en el widget principal (self), no en _tree
            # NavList base ya gestiona flechas arriba/abajo internamente

            # Registrar tiempo de cualquier tecla para detectar Enter de escáner
            self.bind('<KeyPress>', self._on_any_key)

            # Enter: añadir +1 unidad (handler recibe event y puede prevenir propagación)
            self.bind('<Return>', self._on_enter_key)
            self.bind('<KP_Enter>', self._on_enter_key)  # Enter del teclado numérico

            # Suprimir/BackSpace: reducir -1 unidad
            self.bind('<Delete>', self._on_delete_key)
            self.bind('<BackSpace>', self._on_delete_key)

            # Dar foco al widget para que reciba eventos de teclado
            self.focus_set()

        except Exception:
            logger.exception("Error configurando bindings carrito")

    def _on_any_key(self, event=None):
        import time
        self._last_any_key_time = time.monotonic() * 1000

    def _on_enter_key(self, event=None):
        """Handler Enter: añadir +1 unidad al item seleccionado."""
        try:
            import time
            now = time.monotonic() * 1000

            # Ignorar Enter si el BarcodeService acaba de despachar un código (es el Enter del escáner)
            barcode_svc = getattr(self, '_barcode_service', None)
            if barcode_svc is not None:
                last_dispatch = barcode_svc.get_last_dispatch_time()
                if last_dispatch > 0 and (now - last_dispatch) < 300:
                    logger.debug('CarritoNavList: Enter ignorado (viene del escáner)')
                    return 'break'

                # Si el escáner tiene caracteres pendientes en buffer, no consumir el Enter
                if barcode_svc._buffer:
                    return

            data = self.get_selected_data()
            if not data:
                # No consumir Enter si no hay selección: permitir que llegue a BarcodeService
                return

            # No permitir añadir unidades a líneas especiales
            line_tipo = data.get("line_tipo", "normal")
            if line_tipo in ("descuento", "tesoro"):
                return "break"

            if self.on_item_change_callback:
                current_index = self.selected_index
                # Ejecutar callback que probablemente actualice el servicio y la lista
                try:
                    self.on_item_change_callback(data, "add")
                except Exception:
                    logger.exception("Error ejecutando on_item_change_callback add")

                # Re-seleccionar la misma fila después de cualquier reconstrucción
                try:
                    self.after_idle(lambda: self._select(current_index))
                except Exception:
                    pass

            # Mantener foco en el widget
            try:
                self._canvas.focus_set()
            except Exception:
                pass

            return "break"

        except Exception:
            logger.exception("Error en _on_enter_key")
            return "break"

    def _on_delete_key(self, event=None):
        """Handler Suprimir: reducir -1 unidad al item seleccionado.
        """
        try:
            data = self.get_selected_data()
            if not data:
                return "break"

            current_index = self.selected_index

            # Si la fila es visual y define un on_remove, ejecutarlo y no tocar el modelo
            try:
                if data.get('visual'):
                    callback = data.get('on_remove')
                    try:
                        if callable(callback):
                            callback()
                    except Exception:
                        logger.exception('Error ejecutando callback on_remove de fila visual')
                    # Re-seleccionar la misma (o primera) fila después de la actualización
                    try:
                        self.after_idle(lambda: self._select(current_index))
                    except Exception:
                        pass
                    try:
                        self._canvas.focus_set()
                    except Exception:
                        pass
                    return "break"
            except Exception:
                logger.exception('Error comprobando fila visual en _on_delete_key')

            if self.on_item_change_callback:
                try:
                    self.on_item_change_callback(data, "remove")
                except Exception:
                    logger.exception("Error ejecutando on_item_change_callback remove")

                # Re-seleccionar la misma fila después de actualización
                try:
                    self.after_idle(lambda: self._select(current_index))
                except Exception:
                    pass

            try:
                self._canvas.focus_set()
            except Exception:
                pass

            return "break"

        except Exception:
            logger.exception("Error en _on_delete_key")
            return "break"

    def set_items(self, items: List[dict]):
        """Reemplazar todas las filas con nueva lista y formateo para visual."""
        try:
            display_items = []
            for itm in items:
                display = dict(itm or {})
                try:
                    from decimal import Decimal
                    from kool_tpv.base_datos.money_adapter import read_from_db
                    from kool_tpv.utils.formatter_service import FormatterService
                    fmt = FormatterService()

                    for key in ("pvp", "total"):
                        if key in display:
                            v = display.get(key)
                            # int -> cents
                            if isinstance(v, int):
                                euros = read_from_db(v)
                            # digit-only string -> cents
                            elif isinstance(v, str) and v.isdigit():
                                euros = read_from_db(int(v))
                            # float integral -> cents
                            elif isinstance(v, float) and float(v).is_integer():
                                euros = read_from_db(int(v))
                            else:
                                try:
                                    euros = Decimal(str(v))
                                except:
                                    euros = Decimal('0')

                            display[key] = fmt.format_precio(euros)
                except Exception:
                    try:
                        if 'pvp' in display:
                            display['pvp'] = f"{float(display.get('pvp',0)):.2f} €"
                    except: pass
                display_items.append(display)
            
            super().set_items(display_items)
        except Exception:
            logger.exception("Error en CarritoNavList.set_items")
