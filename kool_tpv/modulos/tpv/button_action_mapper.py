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
    'STOCK': lambda view: _show_stock(view),
    'CIERRE': lambda view: _show_ui(view, '_cierre_ui'),
    'CIERRES': lambda view: _show_ui(view, '_cierre_ui'),
    'TICKETS': lambda view: _open_tickets_guarded(view),
    'TICKET': lambda view: _open_tickets_guarded(view),
    'DESCUENTO': lambda view: _execute_action(view, 'descuento_action', 'ejecutar'),
    'DEVOLUCIÓN': lambda view: _open_devolucion_subview(view),
    'DEVOLUCION': lambda view: _open_devolucion_subview(view),
    'REALIZAR DEVOLUCIÓN': lambda view: _open_devolucion_subview(view),
    'REALIZAR DEVOLUCION': lambda view: _open_devolucion_subview(view),
    'MULTI': lambda view: _activate_payment(view, 'multi'),
    'MIXTO': lambda view: _activate_payment(view, 'multi'),
    'TARJETA': lambda view: _activate_payment(view, 'tarjeta'),
    'CARD': lambda view: _activate_payment(view, 'tarjeta'),
    'WEB': lambda view: _activate_payment(view, 'web'),
    'CONFIG': lambda view: _open_config(view),
    'PRESENCIA': lambda view: _open_presencia(view),
    'PRINT ON': lambda view: _toggle_print(view),
    'PRINT OFF': lambda view: _toggle_print(view),
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
    """Activar forma de pago usando métodos de ticket_carrito (igual que atajos de teclado).

    Args:
        view: TpvView instance
        tipo: 'efectivo'|'multi'|'tarjeta'|'web'|'devolucion'
    """
    try:
        # Guardia: en modo devolución no se puede cambiar a otro controller de pago
        if tipo != 'devolucion':
            try:
                carrito = getattr(view, 'carrito_service', None)
                if carrito and carrito.get_ticket_type() == 'devolucion':
                    logger.debug('_activate_payment ignorado: modo devolución activo')
                    return
            except Exception:
                pass

        # Obtener controller para callback de finalización
        ctrl = getattr(view, 'controller', None)
        if ctrl is None:
            logger.warning('Controller no disponible')
            return

        finalize = getattr(ctrl, 'finalize_sale', None)
        if finalize is None:
            logger.warning('finalize_sale no disponible')
            return

        # Obtener TicketCarrito
        tc = getattr(view, 'ticket_carrito', None)
        if tc is None:
            logger.warning('ticket_carrito no disponible')
            return

        # Crear wrapper de finalización (igual que en TpvKeyboardShortcuts)
        def _make_wrapper(tipo_pago):
            def wrapper(data: dict):
                if tipo_pago == 'Efectivo':
                    efectivo = data.get('cantidad_entregada', data.get('total', 0.0))
                    finalize(efectivo=efectivo, forma_pago='Efectivo', importe_efectivo=efectivo, importe_tarjeta=0.0)
                elif tipo_pago == 'Tarjeta':
                    finalize(efectivo=None, forma_pago='Tarjeta', importe_efectivo=0.0, importe_tarjeta=data.get('total', 0.0))
                elif tipo_pago == 'Web':
                    finalize(efectivo=None, forma_pago='Web', importe_efectivo=0.0, importe_tarjeta=0.0, importe_web=data.get('total', 0.0))
                elif tipo_pago == 'Multi':
                    finalize(efectivo=None, forma_pago='Multi', importe_efectivo=data.get('efectivo', 0.0), importe_tarjeta=data.get('tarjeta', 0.0))
            return wrapper

        # Guardia: si hay vales activos disponibles y aún no se ha aplicado uno,
        # mostrar primero el controller de vale (para cualquier forma de pago excepto devolucion)
        if tipo != 'devolucion':
            try:
                from kool_tpv.modulos.tpv.vale_devolucion_service import ValeDevolucionService
                carrito = getattr(view, 'carrito_service', None)
                vale_service = ValeDevolucionService()
                ya_aplicado = False
                try:
                    ya_aplicado = carrito and carrito.get_vale_aplicado() is not None
                except Exception:
                    pass
                if vale_service.hay_vales_activos() and not ya_aplicado:
                    vale_ctrl = getattr(view, '_vale_controller', None)
                    if vale_ctrl:
                        # Recordar tipo de pago original para activarlo tras vale
                        try:
                            tc.pending_payment_type = tipo
                        except Exception:
                            pass
                        try:
                            for widget in tc.payment_area.winfo_children():
                                widget.pack_forget()
                        except Exception:
                            pass
                        try:
                            vale_ctrl.pack(in_=tc.payment_area, fill="both", expand=True)
                            resumen = carrito.get_resumen_financiero() if carrito else {}
                            vale_ctrl.set_total(resumen.get('total', 0.0))
                            vale_ctrl.recargar_vales()
                        except Exception:
                            logger.exception('Error activando controller de vale')
                        # Actualizar referencia en ticket_carrito para navegación por zonas
                        try:
                            tc.active_payment_controller = vale_ctrl
                            tc.active_payment_type = 'vale'
                        except Exception:
                            pass
                        logger.info('Payment vale activado (hay vales disponibles)')
                        return
            except Exception:
                pass

        # Activar forma de pago usando métodos de ticket_carrito (igual que atajos de teclado)
        if tipo == 'efectivo':
            tc.activar_pago_efectivo(on_finalizar=_make_wrapper('Efectivo'))
        elif tipo == 'tarjeta':
            tc.activar_pago_tarjeta(on_finalizar=_make_wrapper('Tarjeta'))
        elif tipo == 'web':
            tc.activar_pago_web(on_finalizar=_make_wrapper('Web'))
        elif tipo == 'multi':
            tc.activar_pago_multi(on_finalizar=_make_wrapper('Multi'))
        elif tipo == 'devolucion':
            # Para devolución, usar controller pre-creado del view
            controller = getattr(view, '_devolucion_controller', None)
            if controller:
                try:
                    for widget in tc.payment_area.winfo_children():
                        widget.pack_forget()
                except Exception:
                    pass
                try:
                    controller.pack(in_=tc.payment_area, fill="both", expand=True)
                    carrito = getattr(view, 'carrito_service', None)
                    if carrito:
                        resumen = carrito.get_resumen_financiero()
                        total = resumen.get('total', 0.0)
                        controller.set_total(total)
                except Exception:
                    logger.exception('Error activando devolución')

        logger.info(f'Payment {tipo} activado desde botón')

    except Exception:
        logger.exception(f'Error activando pago {tipo}')


def _open_tickets_guarded(view):
    """Abrir TicketsUI con check de permisos."""
    try:
        from kool_tpv.modulos.tpv.actions.permisos import check_permiso
        parent = None
        try:
            parent = view.winfo_toplevel()
        except Exception:
            parent = view
        carrito_service = getattr(view, 'carrito_service', None)
        if not check_permiso(carrito_service, 'permiso_tickets', parent):
            return

        # Crear o reutilizar la subview de tickets de forma dinámica
        tickets_ui = getattr(view, '_tickets_subview', None)

        exists = False
        try:
            if tickets_ui and getattr(tickets_ui, 'winfo_exists', None):
                exists = bool(tickets_ui.winfo_exists())
        except Exception:
            exists = False

        if not tickets_ui or not exists:
            try:
                from kool_tpv.modulos.tpv.subviews.tickets_subview import TicketsSubView
                db = getattr(view, 'db', None)
                parent = getattr(view, 'center_area', view)

                tickets_ui = TicketsSubView(parent=parent, db=db, view=view)

                try:
                    view._tickets_subview = tickets_ui
                    if getattr(view, 'controller', None):
                        try:
                            view.controller._tickets_subview = tickets_ui
                        except Exception:
                            pass
                except Exception:
                    pass
            except Exception:
                logger.exception('Error creando TicketsSubView dinámicamente')
                return

        try:
            view.push_subview(tickets_ui, "TICKETS")
        except Exception:
            logger.exception('Error mostrando TicketsSubView')
    except Exception:
        logger.exception('Error abriendo TicketsUI')


def _open_presencia(view):
    """Intentar invocar `open_presencia` en la aplicación principal."""
    try:
        app = view.winfo_toplevel()
        if hasattr(app, 'open_presencia') and callable(app.open_presencia):
            # Indicar que venimos desde el TPV
            app.open_presencia(from_tpv=True)
            return

        logger.warning('open_presencia no disponible en la aplicación principal')
    except Exception:
        logger.exception('Error invocando open_presencia')


def _toggle_print(view):
    """Alternar impresión mediante `toggle_print` disponible en main/app."""
    try:
        # Obtener la app principal para llamar a toggle_print
        app = view.winfo_toplevel()
        if hasattr(app, 'toggle_print') and callable(app.toggle_print):
            app.toggle_print()
            return

        logger.warning('toggle_print no disponible en la aplicación principal')
    except Exception:
        logger.exception('Error invocando toggle_print')


def _show_stock(view):
    """Mostrar StockSubView: recrear si la instancia previa fue destruida."""
    try:
        stock_ui = getattr(view, '_stock_ui', None)

        exists = False
        try:
            if stock_ui and getattr(stock_ui, 'winfo_exists', None):
                exists = bool(stock_ui.winfo_exists())
        except Exception:
            exists = False

        if not stock_ui or not exists:
            try:
                from kool_tpv.modulos.tpv.subviews.stock_subview import StockSubView
                carrito_service = getattr(view, 'carrito_service', None)
                db = getattr(view, 'db', None)
                parent = getattr(view, 'center_area', view)

                stock_ui = StockSubView(parent=parent, db=db, carrito_service=carrito_service, view=view)

                try:
                    view._stock_ui = stock_ui
                    if getattr(view, 'controller', None):
                        try:
                            view.controller._stock_ui = stock_ui
                        except Exception:
                            pass
                except Exception:
                    pass
            except Exception:
                logger.exception('Error creando StockSubView dinámicamente')
                return

        try:
            view.push_subview(stock_ui, "STOCK")
        except Exception:
            logger.exception('Error mostrando StockSubView')
    except Exception:
        logger.exception('Error en _show_stock')


def _open_devolucion_subview(view):
    """Abrir la Subview de Devolución (reemplaza el overlay anterior).

    Realiza la misma validación que el overlay: no abrir si hay venta activa.
    Crea `DevolucionSubView` dinámicamente y hace `view.push_subview(..., "DEVOLUCIÓN")`.
    """
    try:
        from kool_tpv.utils.widgets.notificaciones import ToastWidget

        # Comprobar permiso del cajero logueado
        from kool_tpv.modulos.tpv.actions.permisos import check_permiso
        parent = None
        try:
            parent = view.winfo_toplevel()
        except Exception:
            parent = view
        carrito_service = getattr(view, 'carrito_service', None)
        if not check_permiso(carrito_service, 'permiso_devolucion', parent):
            return

        # Validación: impedir devoluciones si hay venta en curso
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
                ToastWidget.show(view, 'NO SE PUEDE DEVOLVER SI HAY UNA VENTA EN CURSO', tipo='error')
            except Exception:
                logger.exception('Error mostrando diálogo devolucion bloqueada')
            return

        # Crear/Reusar la subview de devoluciones
        devol_ui = getattr(view, '_devolucion_subview', None)

        exists = False
        try:
            if devol_ui and getattr(devol_ui, 'winfo_exists', None):
                exists = bool(devol_ui.winfo_exists())
        except Exception:
            exists = False

        if not devol_ui or not exists:
            try:
                from kool_tpv.modulos.tpv.subviews.devolucion_subview import DevolucionSubView
                carrito_service = getattr(view, 'carrito_service', None)
                db = getattr(view, 'db', None)
                parent = getattr(view, 'center_area', view)

                devol_ui = DevolucionSubView(parent=parent, db=db, carrito_service=carrito_service, view=view)

                try:
                    view._devolucion_subview = devol_ui
                    if getattr(view, 'controller', None):
                        try:
                            view.controller._devolucion_subview = devol_ui
                        except Exception:
                            pass
                except Exception:
                    pass
            except Exception:
                logger.exception('Error creando DevolucionSubView dinámicamente')
                return

        try:
            view.push_subview(devol_ui, "DEVOLUCIÓN")
        except Exception:
            logger.exception('Error mostrando DevolucionSubView')
    except Exception:
        logger.exception('Error en _open_devolucion_subview')


def _attempt_devolucion(view):
    """Intentar abrir devolución con validación de venta activa."""
    try:
        from kool_tpv.utils.widgets.notificaciones import ToastWidget

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
                ToastWidget.show(view, 'NO SE PUEDE DEVOLVER SI HAY UNA VENTA EN CURSO', tipo='error')
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
                    # Remove content in parentheses (keyboard shortcuts like "(ALT+1)")
                    s_norm = re.sub(r'\s*\([^)]*\)', '', s)
                    # Remove diacritics
                    s_norm = unicodedata.normalize('NFKD', s_norm)
                    s_norm = ''.join(ch for ch in s_norm if not unicodedata.combining(ch))
                    # Remove punctuation/symbols, keep letters, numbers and spaces
                    s_norm = re.sub(r'[^A-Za-z0-9 ]+', '', s_norm)
                    return s_norm.strip().upper()

                text_norm = _normalize(text)

                # --- LÓGICA ESPECIAL PARA PRINT ON/OFF ---
                if text_norm in ('PRINT ON', 'PRINT OFF'):
                    try:
                        from kool_tpv.base_datos.configuracion_repository import ConfiguracionRepository
                        repo = ConfiguracionRepository(view.db)
                        config = repo.obtener_multiples(['modo_impresion'])
                        is_on = config.get('modo_impresion', 'escpos') == 'escpos'
                        
                        if is_on:
                            btn.configure(text="PRINT ON", text_color="#00FF00") # Verde si imprime
                        else:
                            btn.configure(text="PRINT OFF", text_color="#FF0000") # Rojo si no imprime
                    except Exception:
                        pass

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
