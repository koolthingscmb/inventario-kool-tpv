"""Compatibility shim exposing `save_ticket` to keep older call sites working.

Delegates to the new TicketProcessors implemented under
`kool_tpv.modulos.ticket.*`. Returns `(ticket_id, num_ticket)` to maintain
backwards compatibility with scripts and tests.
"""
from decimal import Decimal
import logging

from kool_tpv.base_datos.money_adapter import prepare_for_db

logger = logging.getLogger(__name__)


def save_ticket(db, carrito_items, resumen, efectivo=0.0, cajero=None, cliente=None, cliente_id=None,
                forma_pago='Efectivo', importe_efectivo=0.0, importe_tarjeta=0.0, descuento_data=None,
                carrito_service=None, fidelizacion_service=None):
    """Persist a ticket using the new processors. Returns (ticket_id, num_ticket).

    This shim keeps the old signature for external scripts/tests.
    """
    # Determine tipo
    tipo_ticket = 'venta'
    try:
        if carrito_service and getattr(carrito_service, '_devolucion_active', False):
            tipo_ticket = 'devolucion'
        else:
            pts = Decimal(str(resumen.get('puntos_canjeados', 0))) if resumen else Decimal('0')
            if pts > Decimal('0'):
                tipo_ticket = 'venta_fidelizacion'
    except Exception:
        logger.exception('Error determinando tipo_ticket en save_ticket')

    # Calculate points when applicable
    puntos_otorgar = Decimal('0')
    puntos_gastados = Decimal('0')
    try:
        if tipo_ticket == 'venta_fidelizacion' and fidelizacion_service:
            puntos_gastados = Decimal(str(resumen.get('puntos_canjeados', 0)))
            puntos_otorgar = fidelizacion_service.calcular_puntos_ganados(carrito_items, puntos_gastados)
    except Exception:
        logger.exception('Error calculando puntos en save_ticket shim')

    # Calcular tesoro_total_ticket (snapshot del tesoro después de esta compra)
    tesoro_total_ticket_cents = 0
    try:
        if cliente_id:
            row = db.fetch_one("SELECT COALESCE(tesoro_total, 0) FROM clientes WHERE id = ?", (cliente_id,))
            tesoro_actual_cents = int(row[0]) if row and row[0] is not None else 0
            tesoro_total_ticket_cents = tesoro_actual_cents + int(puntos_otorgar) - int(puntos_gastados)
    except Exception:
        logger.exception('Error calculando tesoro_total_ticket en save_ticket shim')

    # Build payload (cents)
    def _dec(v, default='0'):
        try:
            return Decimal(str(v))
        except Exception:
            return Decimal(default)

    payload = {
        'created_at': None,
        'num_ticket': None,
        'cajero': cajero,
        'cliente': cliente,
        'cliente_id': cliente_id,
        'subtotal_cents': prepare_for_db(_dec(resumen.get('subtotal', '0'))),
        'total_cents': prepare_for_db(_dec(resumen.get('total', '0'))),
        'pagado_cents': prepare_for_db(_dec(efectivo or 0)),
        'cambio_cents': prepare_for_db(_dec((efectivo or 0)) - _dec(resumen.get('total', '0'))),
        'importe_efectivo_cents': prepare_for_db(_dec(importe_efectivo)),
        'importe_tarjeta_cents': prepare_for_db(_dec(importe_tarjeta)),
        'descuento_euros_cents': prepare_for_db(_dec(descuento_data.get('euros', 0) if descuento_data else 0)),
        'descuento_tipo': (descuento_data.get('tipo') if descuento_data else None),
        'descuento_valor': (descuento_data.get('valor') if descuento_data else None),
        'forma_pago': forma_pago,
        'tesoro_ganado_str': str(puntos_otorgar),
        'tesoro_gastado_str': str(puntos_gastados),
        'tesoro_total_ticket_cents': tesoro_total_ticket_cents,
        'ticket_text_snapshot': None,
        'carrito_items': carrito_items,
        'pagos': [],
    }

    if importe_efectivo:
        payload['pagos'].append(('efectivo', prepare_for_db(_dec(importe_efectivo))))
    if importe_tarjeta:
        payload['pagos'].append(('tarjeta', prepare_for_db(_dec(importe_tarjeta))))

    # Select processor
    processor = None
    try:
        if tipo_ticket == 'venta':
            from kool_tpv.modulos.ticket.venta_processor import VentaProcessor
            processor = VentaProcessor(db)
        elif tipo_ticket == 'venta_fidelizacion':
            from kool_tpv.modulos.ticket.venta_fidelizacion_processor import VentaFidelizacionProcessor
            processor = VentaFidelizacionProcessor(db)
        elif tipo_ticket == 'devolucion':
            from kool_tpv.modulos.ticket.devolucion_processor import DevolucionProcessor
            processor = DevolucionProcessor(db)
        else:
            from kool_tpv.modulos.ticket.venta_processor import VentaProcessor
            processor = VentaProcessor(db)
    except Exception:
        logger.exception('Error creando processor en save_ticket shim')
        raise

    # Execute
    try:
        res = processor.process(**payload)
        # Support processors returning either ticket_id or (ticket_id, num_ticket)
        if isinstance(res, tuple) or isinstance(res, list):
            ticket_id, num_ticket = res[0], (res[1] if len(res) > 1 else None)
        else:
            ticket_id = res
            num_ticket = payload.get('num_ticket')
        return ticket_id, num_ticket
    except Exception:
        logger.exception('Error procesando ticket en save_ticket shim')
        raise
