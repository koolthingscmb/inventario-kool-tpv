"""
button_action_mapper.py - Mapeo de botones TPV a acciones

Centraliza la asignación de comandos a botones del grid.
Facilita mantenimiento y evita código repetitivo.
"""
import logging
import re
import unicodedata
from typing import Dict, Callable, Any

logger = logging.getLogger(__name__)


# Mapeo: texto botón → lambda que recibe view
BUTTON_ACTIONS: Dict[str, Callable[[Any], None]] = {
    'CLIENTE': lambda view: _execute_action(view, '_cliente_action', 'ejecutar'),
    'CAJERO': lambda view: _execute_action(view, '_cajero_action', 'ejecutar'),
    'COBRAR': lambda view: _activate_payment(view, 'efectivo'),
    'CASH': lambda view: _activate_payment(view, 'efectivo'),
    'STOCK': lambda view: _show_ui(view, '_stock_ui'),
    'CIERRE': lambda view: _show_ui(view, '_cierre_ui'),
    'CIERRES': lambda view: _show_ui(view, '_cierre_ui'),
    'TICKETS': lambda view: _open_tickets_guarded(view),
    'TICKET': lambda view: _open_tickets_guarded(view),
    'DESCUENTO': lambda view: _execute_action(view, 'descuento_action', 'ejecutar'),
    'DEVOLUCIÓN': lambda view: _attempt_devolucion(view),
    'DEVOLUCION': lambda view: _attempt_devolucion(view),
    'REALIZAR DEVOLUCIÓN': lambda view: _attempt_devolucion(view),
    'REALIZAR DEVOLUCION': lambda view: _attempt_devolucion(view),
    'MULTI': lambda view: _activate_payment(view, 'multi'),
    'MIXTO': lambda view: _activate_payment(view, 'multi'),
    'TARJETA': lambda view: _activate_payment(view, 'tarjeta'),
    'CARD': lambda view: _activate_payment(view, 'tarjeta'),
    'WEB': lambda view: _activate_payment(view, 'web'),
    'CONFIG': lambda view: _open_config(view),
    'PRINT ON': lambda view: _toggle_print(view),
}


def _execute_action(view, attr_name: str, method_name: str):
    """Helper: ejecutar método de un atributo de view."""
    try:
        obj = getattr(view, attr_name, None)
        if obj is None:
            logger.warning(f'{attr_name} no disponible en view')
            return

        method = getattr(obj, method_name, None)
        if method is None or not callable(method):
            logger.warning(f'{attr_name}.{method_name} no es callable')
            return

        method()
    except Exception:
        logger.exception(f'Error ejecutando {attr_name}.{method_name}')


def _show_ui(view, attr_name: str):
    """Helper: llamar .show() en una UI."""
    try:
        ui = getattr(view, attr_name, None)
        if ui is None:
            logger.warning(f'{attr_name} no disponible')
            return

        if not hasattr(ui, 'show'):
            logger.warning(f'{attr_name} no tiene método show()')
            return

        ui.show()
    except Exception:
        logger.exception(f'Error mostrando {attr_name}')


def _activate_payment(view, tipo: str):
    """Activar payment controller pre-creado del factory.

    Args:
        view: TpvView instance
        tipo: 'efectivo'|'multi'|'tarjeta'|'web'
    """
    try:
        # Mapeo tipo → controller attribute
        mapping = {
            'efectivo': '_cash_controller',
            'multi': '_multi_controller',
            'tarjeta': '_tarjeta_controller',
            'web': '_web_controller'
        }

        attr_name = mapping.get(tipo)
        if not attr_name:
            logger.warning(f'Tipo de pago desconocido: {tipo}')
            return

        # Obtener controller pre-creado
        controller = getattr(view, attr_name, None)
        if controller is None:
            logger.warning(f'Controller {attr_name} no disponible')
            return

        # Obtener TicketCarrito
        tc = getattr(view, 'ticket_carrito', None)
        if tc is None:
            logger.warning('ticket_carrito no disponible')
            return

        # Limpiar payment_area
        try:
            for widget in tc.payment_area.winfo_children():
                widget.pack_forget()
        except Exception:
            logger.exception('Error limpiando payment_area')

        # Empaquetar controller pre-creado
        try:
            controller.pack(in_=tc.payment_area, fill="both", expand=True)
        except Exception:
            logger.exception(f'Error empaquetando controller {tipo}')
            return

        # Actualizar total
        try:
            carrito = getattr(view, 'carrito_service', None)
            if carrito:
                resumen = carrito.get_resumen_financiero()
                total = resumen.get('total', 0.0)
                controller.set_total(total)
                logger.debug(f'Payment {tipo} activado con total={total}')
        except Exception:
            logger.exception('Error actualizando total del controller')

    except Exception:
        logger.exception(f'Error activando pago {tipo}')


def _open_tickets_guarded(view):
    """Abrir TicketsUI con check de permisos (placeholder)."""
    try:
        allowed = True
        try:
            checker = getattr(view, '_check_tickets_permission', None)
            if callable(checker):
                allowed = bool(checker())
        except Exception:
            allowed = True

        if not allowed:
            try:
                from kool_tpv.utils.custom_dialog import show_error
                parent = getattr(view, 'container', None) or view.parent
                show_error(parent, 'Sin permiso', 'Acceso no autorizado a TICKETS')
            except Exception:
                logger.exception('Error mostrando diálogo acceso denegado')
            return

        _show_ui(view, '_tickets_ui')
    except Exception:
        logger.exception('Error abriendo TicketsUI')


def _open_config(view):
    """Intentar invocar `open_config` en la vista o en su contenedor/principal."""
    try:
        # Preferir método directo en la view
        if getattr(view, 'open_config', None) and callable(view.open_config):
            view.open_config()
            return

        # Probar en container o parent (main app)
        parent = getattr(view, 'container', None) or getattr(view, 'parent', None)
        if parent and getattr(parent, 'open_config', None) and callable(parent.open_config):
            parent.open_config()
            return

        logger.warning('open_config no disponible en view ni en su contenedor')
    except Exception:
        logger.exception('Error invocando open_config')


def _toggle_print(view):
    """Intentar activar/desactivar impresión mediante `toggle_print` disponible en main/app."""
    try:
        # Preferir método en la view
        if getattr(view, 'toggle_print', None) and callable(view.toggle_print):
            view.toggle_print()
            return

        # Probar en container o parent (main app)
        parent = getattr(view, 'container', None) or getattr(view, 'parent', None)
        if parent and getattr(parent, 'toggle_print', None) and callable(parent.toggle_print):
            parent.toggle_print()
            return

        logger.warning('toggle_print no disponible en view ni en su contenedor')
    except Exception:
        logger.exception('Error invocando toggle_print')


def _attempt_devolucion(view):
    """Intentar abrir devolución con validación de venta activa."""
    try:
        from kool_tpv.utils.custom_dialog import show_error

        sale_active = False
        try:
            carrito = getattr(view, 'carrito_service', None)
            if carrito is not None and hasattr(carrito, 'get_items'):
                for item in (carrito.get_items() or []):
                    try:
                        line_tipo = str(item.get('line_tipo', 'venta')).lower()
                        cantidad = int(item.get('cantidad', 0))
                        if line_tipo != 'devolucion' and cantidad > 0:
                            sale_active = True
                            break
                    except Exception:
                        continue
        except Exception:
            sale_active = False

        if sale_active:
            try:
                parent = getattr(view, 'container', None) or view.parent
                show_error(parent, 'Operación no permitida', 
                          'No se puede devolver si hay una venta en curso')
            except Exception:
                logger.exception('Error mostrando diálogo devolucion bloqueada')
            return

        _execute_action(view, '_devolucion_action', 'ejecutar')
    except Exception:
        logger.exception('Error en _attempt_devolucion')


def rebind_buttons(view):
    """Rebind todos los botones del grid según BUTTON_ACTIONS.

    Args:
        view: Instancia de TpvView con atributo grid_buttons (lista de CTkButton)
    """
    try:
        buttons = getattr(view, 'grid_buttons', [])
        if not buttons:
            logger.warning('No hay grid_buttons en view para rebind')
            return

        rebound_count = 0
        for btn in buttons:
            try:
                text = (btn.cget('text') or '').strip()

                # Normalize original and accentless/cleaned variants to improve matching
                def _normalize(s: str) -> str:
                    if not s:
                        return ''
                    # Remove diacritics
                    s_norm = unicodedata.normalize('NFKD', s)
                    s_norm = ''.join(ch for ch in s_norm if not unicodedata.combining(ch))
                    # Remove punctuation/symbols, keep letters, numbers and spaces
                    s_norm = re.sub(r'[^A-Za-z0-9 ]+', '', s_norm)
                    return s_norm.strip().upper()

                text_norm = _normalize(text)

                action = BUTTON_ACTIONS.get(text.upper()) or BUTTON_ACTIONS.get(text_norm)
                if action:
                    btn.configure(command=lambda v=view, a=action: a(v))
                    rebound_count += 1
                    logger.debug(f'Botón {text} rebound correctamente')
            except Exception:
                logger.exception(f'Error rebinding botón individual')
                continue

        logger.info(f'{rebound_count}/{len(buttons)} botones rebound correctamente')
    except Exception:
        logger.exception('Error en rebind_buttons')


__all__ = ['BUTTON_ACTIONS', 'rebind_buttons']
