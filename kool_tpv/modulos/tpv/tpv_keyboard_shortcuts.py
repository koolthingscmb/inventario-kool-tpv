"""TpvKeyboardShortcuts - Gestión centralizada de shortcuts de teclado del TPV.

Shortcuts registrados:
  F1  → Pago efectivo
  F2  → Pago tarjeta
  F3  → Pago web
  F4  → Pago multi
  F5  → Ciclar foco: Grid → Carrito → Payment (si activo)
"""
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def _load_layout_config() -> dict:
    try:
        path = Path(__file__).resolve().parents[3] / 'kool_tpv' / 'config' / 'layout_config.json'
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        logger.exception('Error cargando layout_config.json en TpvKeyboardShortcuts')
        return {}


class TpvKeyboardShortcuts:
    """Registra y gestiona todos los shortcuts de teclado del TPV."""

    def __init__(self, controller):
        self.ctrl = controller
        self._zone = 'grid'
        self._root = controller.view.winfo_toplevel()
        cfg = _load_layout_config()
        nav = cfg.get('global', {}).get('keyboard_navigation', {})
        self._zone_colors = nav.get('zone_colors', {'carrito': '#4A9EFF', 'payment': '#4AFF91', 'grid': 'transparent'})
        self._zone_border_width = nav.get('zone_border_width', 3)
        self._register()

    def _register(self):
        root = self._root
        root.bind_all('<F1>', lambda e: self._fkey_pago('cash'))
        root.bind_all('<F2>', lambda e: self._fkey_pago('tarjeta'))
        root.bind_all('<F3>', lambda e: self._fkey_pago('web'))
        root.bind_all('<F4>', lambda e: self._fkey_pago('multi'))
        root.bind_all('<F5>', lambda e: self._ciclar_zona())
        logger.info('TpvKeyboardShortcuts registrados (F1-F5)')

    def detach(self):
        for key in ('<F1>', '<F2>', '<F3>', '<F4>', '<F5>'):
            try:
                self._root.unbind_all(key)
            except Exception:
                pass
        self._clear_zone_indicators()

    # ------------------------------------------------------------------
    # F1-F4: Formas de pago
    # ------------------------------------------------------------------

    def _fkey_pago(self, tipo: str):
        """Activar forma de pago o recuperar foco si ya está activa."""
        try:
            view = self.ctrl.view
            ticket = getattr(view, 'ticket_carrito', None)
            if ticket is None:
                return
            carrito = getattr(view, 'carrito_service', None)
            if carrito is None or carrito.is_empty():
                return

            active_type = getattr(ticket, 'active_payment_type', None)
            active_ctrl = getattr(ticket, 'active_payment_controller', None)
            tipo_ticket = 'efectivo' if tipo == 'cash' else tipo

            # Si ya está activo el mismo tipo → recuperar foco
            if active_type == tipo_ticket and active_ctrl is not None:
                self._focus_payment(tipo, active_ctrl)
                self._zone = 'payment'
                return

            on_fin = self.ctrl.payment_controllers.get(tipo)

            if tipo == 'cash':
                ticket.activar_pago_efectivo(on_finalizar=on_fin)
            elif tipo == 'tarjeta':
                ticket.activar_pago_tarjeta(on_finalizar=on_fin)
            elif tipo == 'web':
                ticket.activar_pago_web(on_finalizar=on_fin)
            elif tipo == 'multi':
                ticket.activar_pago_multi(on_finalizar=on_fin)

            self._zone = 'payment'
            self._apply_zone_indicator('payment')
            logger.info(f'F-key: pago {tipo} activado')
        except Exception:
            logger.exception(f'Error activando pago {tipo} por F-key')

    def _focus_payment(self, tipo: str, ctrl):
        try:
            if tipo == 'cash':
                ctrl.entry_cantidad.focus_set()
            elif tipo == 'multi':
                ctrl.entry_efectivo.focus_set()
            else:
                ctrl.btn_finalizar.focus_set()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # F5: Ciclar zonas
    # ------------------------------------------------------------------

    def _ciclar_zona(self):
        """Ciclar foco entre Grid → Carrito → Payment (si activo)."""
        try:
            view = self.ctrl.view
            ticket = getattr(view, 'ticket_carrito', None)
            has_payment = (
                ticket is not None and
                getattr(ticket, 'active_payment_controller', None) is not None
            )

            if self._zone == 'grid':
                self._focus_carrito()
                self._zone = 'carrito'
            elif self._zone == 'carrito':
                if has_payment:
                    active_ctrl = ticket.active_payment_controller
                    active_type = getattr(ticket, 'active_payment_type', '')
                    tipo = 'cash' if active_type == 'efectivo' else active_type
                    self._focus_payment(tipo, active_ctrl)
                    self._zone = 'payment'
                else:
                    self._focus_grid()
                    self._zone = 'grid'
            elif self._zone == 'payment':
                self._focus_grid()
                self._zone = 'grid'

            self._apply_zone_indicator(self._zone)
            logger.debug(f'Zona de foco: {self._zone}')
        except Exception:
            logger.exception('Error ciclando zona de foco')

    def _focus_carrito(self):
        try:
            view = self.ctrl.view
            ticket = getattr(view, 'ticket_carrito', None)
            if ticket and hasattr(ticket, 'carrito_nav_list'):
                ticket.carrito_nav_list.focus_set()
        except Exception:
            pass

    def _focus_grid(self):
        try:
            view = self.ctrl.view
            center = getattr(view, 'center_area', None)
            if center:
                center.focus_set()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Indicadores visuales de zona
    # ------------------------------------------------------------------

    def _apply_zone_indicator(self, zone: str):
        """Aplicar borde de color al widget de la zona activa."""
        try:
            view = self.ctrl.view
            ticket = getattr(view, 'ticket_carrito', None)

            color_carrito = self._zone_colors.get('carrito', '#4A9EFF')
            color_payment = self._zone_colors.get('payment', '#4AFF91')
            bw = self._zone_border_width

            # Borde en carrito_nav_list
            if ticket and hasattr(ticket, 'carrito_nav_list'):
                nav = ticket.carrito_nav_list
                try:
                    if zone == 'carrito':
                        nav.configure(border_color=color_carrito, border_width=bw)
                    else:
                        nav.configure(border_width=0)
                except Exception:
                    pass

            # Borde en payment_area
            if ticket and hasattr(ticket, 'payment_area'):
                pa = ticket.payment_area
                try:
                    if zone == 'payment':
                        pa.configure(border_color=color_payment, border_width=bw)
                    else:
                        pa.configure(border_width=0)
                except Exception:
                    pass

        except Exception:
            logger.exception('Error aplicando indicador de zona')

    def _clear_zone_indicators(self):
        """Quitar todos los bordes de zona."""
        self._apply_zone_indicator('grid')
