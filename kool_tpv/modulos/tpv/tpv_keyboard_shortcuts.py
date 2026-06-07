"""TpvKeyboardShortcuts - Gestión centralizada de shortcuts de teclado del TPV.

Shortcuts registrados:
  F1  → Pago efectivo
  F2  → Pago tarjeta
  F3  → Pago web
  F4  → Pago multi
  F5  → Ciclar foco: Grid → Carrito → Payment (si activo)
  Space → Abrir BuscarProducto / cerrar subvista activa
"""
import logging
import time

logger = logging.getLogger(__name__)


class TpvKeyboardShortcuts:
    """Registra y gestiona todos los shortcuts de teclado del TPV."""

    def __init__(self, controller):
        self.ctrl = controller
        self._zone = 'grid'  # zona de foco actual: 'grid' | 'carrito' | 'payment'
        self._root = controller.view.winfo_toplevel()
        self._register()

    def _register(self):
        root = self._root
        root.bind_all('<F1>',     lambda e: self._fkey_pago('cash'))
        root.bind_all('<F2>',     lambda e: self._fkey_pago('tarjeta'))
        root.bind_all('<F3>',     lambda e: self._fkey_pago('web'))
        root.bind_all('<F4>',     lambda e: self._fkey_pago('multi'))
        root.bind_all('<F5>',     lambda e: self._ciclar_zona())
        root.bind_all('<space>',  lambda e: self._spacebar(e))
        logger.info('TpvKeyboardShortcuts registrados (F1-F5, Space)')

    def detach(self):
        for key in ('<F1>', '<F2>', '<F3>', '<F4>', '<F5>', '<space>'):
            try:
                self._root.unbind_all(key)
            except Exception:
                pass

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
            # El primer botón del grid tiene el foco por defecto
            center = getattr(view, 'center_area', None)
            if center:
                center.focus_set()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Space: Buscar producto / cerrar subvista
    # ------------------------------------------------------------------

    def _spacebar(self, event):
        """Abrir BuscarProducto o cerrar subvista activa."""
        try:
            # No interceptar si el foco está en un Entry/Text
            focused = self._root.focus_get()
            if focused is not None:
                cls = focused.__class__.__name__.lower()
                if any(w in cls for w in ('entry', 'text', 'textbox', 'ctkentry', 'ctktextbox', 'spinbox', 'combobox')):
                    return

            view = self.ctrl.view

            # Si hay subvista activa → cerrarla y enfocar grid
            if hasattr(view, 'pop_subview'):
                stack = getattr(view, '_subview_stack', [])
                if len(stack) > 1:
                    view.pop_subview()
                    self._focus_grid()
                    self._zone = 'grid'
                    return

            # Si hay overlay de buscar_articulo visible → ocultarlo
            buscar = getattr(view, '_buscar_articulo', None) or \
                     getattr(self.ctrl, '_buscar_action', None)
            if buscar is not None:
                visible = getattr(buscar, '_visible', False)
                if visible:
                    buscar.hide()
                    self._focus_grid()
                    self._zone = 'grid'
                    return
                else:
                    buscar.show()
                    self._zone = 'grid'
                    return

            logger.debug('Space: no hay subvista ni buscar_articulo disponible')
        except Exception:
            logger.exception('Error en spacebar handler')
