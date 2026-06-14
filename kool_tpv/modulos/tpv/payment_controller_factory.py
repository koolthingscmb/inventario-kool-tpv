"""
payment_controller_factory.py - Factory para payment controllers

Centraliza la creación de los payment controllers del TPV.
Facilita instanciación y configuración consistente.
"""
import logging
from typing import Dict, Callable, Optional, Any

logger = logging.getLogger(__name__)


def create_controllers(
    parent: Any,
    carrito_service: Any,
    on_finalize: Callable,
    view: Any = None,
) -> Dict[str, Any]:
    """Crear todos los payment controllers del TPV.

    Args:
        parent: Widget padre donde se inyectarán los controllers
        carrito_service: Instancia de CarritoService
        on_finalize: Callback unificado para finalizar venta
        view: Instancia de TpvView (opcional, para callbacks de vale)

    Returns:
        Dict con controllers: {
            'cash': PaymentControllerEfectivo,
            'multi': PaymentControllerMulti,
            'tarjeta': PaymentControllerSimple (tarjeta),
            'web': PaymentControllerSimple (web),
            'vale': PaymentControllerVale
        }
    """
    controllers = {}

    # Total inicial (se actualizará dinámicamente)
    try:
        resumen = carrito_service.get_resumen_financiero() if carrito_service else {}
        total = resumen.get('total', 0.0)
    except Exception:
        total = 0.0

    # Wrapper on_finalize para adaptar estructura de callbacks
    def _make_finalize_wrapper(tipo_pago: str) -> Callable:
        """Crear wrapper específico por tipo de pago."""
        def wrapper(data: dict):
            try:
                # Extraer datos según tipo
                if tipo_pago == 'Efectivo':
                    efectivo = data.get('cantidad_entregada', data.get('total', 0.0))
                    on_finalize(
                        efectivo=efectivo,
                        forma_pago='Efectivo',
                        importe_efectivo=efectivo,
                        importe_tarjeta=0.0
                    )
                elif tipo_pago == 'Multi':
                    efectivo_val = data.get('efectivo', 0.0)
                    tarjeta_val = data.get('tarjeta', 0.0)
                    on_finalize(
                        efectivo=None,  # Multi no usa efectivo como pagado total
                        forma_pago='Multi',
                        importe_efectivo=efectivo_val,
                        importe_tarjeta=tarjeta_val
                    )
                elif tipo_pago == 'Tarjeta':
                    # Tarjeta: pasar importe a `importe_tarjeta`
                    on_finalize(
                        efectivo=None,
                        forma_pago='Tarjeta',
                        importe_efectivo=0.0,
                        importe_tarjeta=data.get('total', 0.0)
                    )
                elif tipo_pago == 'Web':
                    # Web: pasar importe a `importe_web` y dejar `importe_tarjeta` a 0
                    on_finalize(
                        efectivo=None,
                        forma_pago='Web',
                        importe_efectivo=0.0,
                        importe_tarjeta=0.0,
                        importe_web=data.get('total', 0.0)
                    )
                elif tipo_pago == 'Devolucion':
                    forma   = data.get('forma_pago', 'Efectivo')
                    total_v = data.get('total', 0.0)
                    if forma == 'Efectivo':
                        on_finalize(
                            efectivo=total_v,
                            forma_pago='Efectivo',
                            importe_efectivo=total_v,
                            importe_tarjeta=0.0
                        )
                    elif forma == 'Tarjeta':
                        on_finalize(
                            efectivo=None,
                            forma_pago='Tarjeta',
                            importe_efectivo=0.0,
                            importe_tarjeta=total_v
                        )
                    else:  # cambio
                        on_finalize(
                            efectivo=None,
                            forma_pago='cambio',
                            importe_efectivo=0.0,
                            importe_tarjeta=0.0
                        )
                else:
                    # Genérico
                    on_finalize(
                        efectivo=None,
                        forma_pago=tipo_pago,
                        importe_efectivo=0.0,
                        importe_tarjeta=0.0
                    )
            except Exception:
                logger.exception(f'Error en finalize wrapper ({tipo_pago})')

        return wrapper

    # Controller efectivo
    try:
        from kool_tpv.utils.widgets.payment_controllers.payment_controller_efectivo import PaymentControllerEfectivo

        controllers['cash'] = PaymentControllerEfectivo(
            parent=parent,
            total=total,
            on_finalizar=_make_finalize_wrapper('Efectivo')
        )
        logger.debug('PaymentControllerEfectivo creado')
    except Exception:
        logger.exception('Error creando PaymentControllerEfectivo')
        controllers['cash'] = None

    # Controller multi
    try:
        from kool_tpv.utils.widgets.payment_controllers.payment_controller_multi import PaymentControllerMulti

        controllers['multi'] = PaymentControllerMulti(
            parent=parent,
            total=total,
            on_finalizar=_make_finalize_wrapper('Multi')
        )
        logger.debug('PaymentControllerMulti creado')
    except Exception:
        logger.exception('Error creando PaymentControllerMulti')
        controllers['multi'] = None

    # Controller tarjeta
    try:
        from kool_tpv.utils.widgets.payment_controllers.payment_controller_simple import PaymentControllerSimple

        controllers['tarjeta'] = PaymentControllerSimple(
            parent=parent,
            tipo_pago='Tarjeta',
            total=total,
            on_finalizar=_make_finalize_wrapper('Tarjeta')
        )
        logger.debug('PaymentControllerSimple (Tarjeta) creado')
    except Exception:
        logger.exception('Error creando PaymentControllerSimple (Tarjeta)')
        controllers['tarjeta'] = None

    # Controller web
    try:
        from kool_tpv.utils.widgets.payment_controllers.payment_controller_simple import PaymentControllerSimple

        controllers['web'] = PaymentControllerSimple(
            parent=parent,
            tipo_pago='Web',
            total=total,
            on_finalizar=_make_finalize_wrapper('Web')
        )
        logger.debug('PaymentControllerSimple (Web) creado')
    except Exception:
        logger.exception('Error creando PaymentControllerSimple (Web)')
        controllers['web'] = None

    # Controller devolución
    try:
        from kool_tpv.utils.widgets.payment_controllers.payment_controller_devolucion import PaymentControllerDevolucion

        controllers['devolucion'] = PaymentControllerDevolucion(
            parent=parent,
            total=total,
            on_finalizar=_make_finalize_wrapper('Devolucion')
        )
        logger.debug('PaymentControllerDevolucion creado')
    except Exception:
        logger.exception('Error creando PaymentControllerDevolucion')
        controllers['devolucion'] = None

    # Controller vale de devolución
    try:
        from kool_tpv.utils.widgets.payment_controllers.payment_controller_vale import PaymentControllerVale

        def _on_usar_vale(vale_data):
            try:
                if carrito_service and hasattr(carrito_service, 'aplicar_vale'):
                    carrito_service.aplicar_vale(vale_data)
                ctrl = getattr(view, 'controller', None) if view else None
                if ctrl and hasattr(ctrl, '_after_vale_applied'):
                    ctrl._after_vale_applied()
            except Exception:
                logger.exception('Error aplicando vale desde controller')

        def _on_omitir_vale():
            try:
                ctrl = getattr(view, 'controller', None) if view else None
                if ctrl and hasattr(ctrl, '_after_vale_omitted'):
                    ctrl._after_vale_omitted()
            except Exception:
                logger.exception('Error omitiendo vale')

        controllers['vale'] = PaymentControllerVale(
            parent=parent,
            total=total,
            on_usar_vale=_on_usar_vale,
            on_omitir=_on_omitir_vale,
        )
        logger.debug('PaymentControllerVale creado')
    except Exception:
        logger.exception('Error creando PaymentControllerVale')
        controllers['vale'] = None

    logger.info(f'Factory creó {sum(1 for c in controllers.values() if c is not None)}/6 controllers')

    return controllers


def create_resumen_controller(parent, ticket_data: dict, on_nueva_venta: Callable) -> Any:
    """Crear controller de resumen post-venta (bajo demanda).

    Args:
        parent: Widget padre (payment_area)
        ticket_data: Dict con datos del ticket (num_ticket, total, forma_pago, etc.)
        on_nueva_venta: Callback cuando se pulsa Enter/botón nueva venta

    Returns:
        PaymentControllerResumen instance o None si falla
    """
    try:
        from kool_tpv.utils.widgets.payment_controllers.payment_controller_resumen import PaymentControllerResumen

        controller = PaymentControllerResumen(
            parent=parent,
            ticket_data=ticket_data,
            on_nueva_venta=on_nueva_venta
        )
        logger.info('PaymentControllerResumen creado')
        return controller
    except Exception:
        logger.exception('Error creando PaymentControllerResumen')
        return None


__all__ = ['create_controllers', 'create_resumen_controller']
