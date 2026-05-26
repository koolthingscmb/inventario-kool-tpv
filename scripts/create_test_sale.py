"""Script de prueba: crea una venta con pago web y muestra filas insertadas."""
import logging
from decimal import Decimal
from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.base_datos.money_adapter import prepare_for_db, read_from_db
from kool_tpv.modulos.ticket.venta_processor import VentaProcessor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = 'kool_tpv/base_datos/kool_bd.db'

def main():
    db = Database(DB_PATH)
    db.connect()

    vp = VentaProcessor(db)

    carrito_items = [
        {
            'sku': 'TEST123',
            'nombre': 'Articulo prueba web',
            'cantidad': 1,
            'pvp': '9.99',
            'tipo_iva': 21,
            'line_tipo': 'venta',
            'id': None,  # evitar tocar productos reales
        }
    ]

    subtotal_cents = prepare_for_db(Decimal('9.99'))
    total_cents = subtotal_cents
    pagos = [('web', int(total_cents))]

    try:
        res = vp.process(
            carrito_items=carrito_items,
            resumen={'total': '9.99', 'iva_desglose': {}},
            created_at=None,
            cajero='TEST-USER',
            cliente='Cliente Prueba Web',
            cliente_id=None,
            subtotal_cents=subtotal_cents,
            forma_pago='Web',
            total_cents=total_cents,
            pagado_cents=total_cents,
            cambio_cents=0,
            importe_efectivo_cents=None,
            importe_tarjeta_cents=None,
            importe_web_cents=total_cents,
            descuento_euros_cents=0,
            descuento_tipo=None,
            descuento_valor=None,
            puntos_otorgar_cents=0,
            puntos_gastados_cents=0,
            ticket_text_snapshot=None,
            iva_desglose_json='{}',
            pagos=pagos,
        )
        ticket_id, num_ticket = res
        logger.info('Ticket creado: id=%s num_ticket=%s', ticket_id, num_ticket)

        t = db.fetch_one('SELECT id, num_ticket, importe_efectivo, importe_tarjeta, importe_web, total, forma_pago FROM tickets WHERE id = ?', (ticket_id,))
        print('\n--- tickets row ---')
        if t:
            # total comes as integer cents; convert
            print(dict(t))
            try:
                total_eur = read_from_db(t['total'])
            except Exception:
                total_eur = None
            print('total (euros):', total_eur)
        else:
            print('No se encontró ticket')

        payments = db.fetch_all('SELECT metodo, importe FROM payments WHERE ticket_id = ?', (ticket_id,))
        print('\n--- payments rows ---')
        for p in payments or []:
            print(dict(p))

    except Exception as e:
        logger.exception('Error creando venta de prueba: %s', e)

if __name__ == '__main__':
    main()
