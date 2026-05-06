#!/usr/bin/env python3
import argparse
import logging
import sys
from pathlib import Path

# Ensure project root is on path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.impresion.impresora_service import ImpresoraService
from kool_tpv.utils.formatter_service import FormatterService


def setup_logger(path):
    h = logging.FileHandler(path, encoding='utf-8')
    fmt = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    h.setFormatter(fmt)
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.addHandler(h)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--db', required=True, help='Path to sqlite db file')
    p.add_argument('--log', required=True, help='Path to output log file')
    p.add_argument('--ticket-id', type=int, help='Ticket id to inspect (optional)')
    args = p.parse_args()

    setup_logger(args.log)
    logger = logging.getLogger(__name__)
    logger.info('Starting diag against DB: %s', args.db)

    db = Database(args.db)
    db.connect()

    conn = db.connection
    cur = conn.cursor()

    # determine ticket id
    ticket_id = args.ticket_id
    if not ticket_id:
        cur.execute('SELECT id FROM tickets ORDER BY id DESC LIMIT 1')
        row = cur.fetchone()
        if not row:
            logger.error('No tickets found in DB')
            return
        ticket_id = row[0]

    logger.info('Using ticket id: %s', ticket_id)

    # fetch raw ticket row
    raw = db.fetch_one('''SELECT id, num_ticket, created_at, cajero, cliente, cliente_id, total, forma_pago, importe_efectivo, importe_tarjeta, tesoro_ganado, tesoro_gastado FROM tickets WHERE id = ?''', (ticket_id,))
    logger.info('RAW TICKET ROW: %s', raw)

    # instrument FormatterService.format_precio
    orig_fmt = FormatterService.format_precio

    def fmt_wrapper(self, precio):
        logger.debug('FORMATTER INPUT: %r (type=%s)', precio, type(precio))
        try:
            res = orig_fmt(self, precio)
        except Exception as e:
            logger.exception('Formatter raised')
            raise
        logger.debug('FORMATTER OUTPUT: %r', res)
        return res

    FormatterService.format_precio = fmt_wrapper

    impresora = ImpresoraService(db=db, imprimir_en_consola=False)

    # instrument generator if available
    try:
        orig_gen = impresora.ticket_generator.generate

        def gen_wrapper(config, ticket_data, items, cliente_data=None):
            logger.info('GENERATOR RECEIVED ticket_data.total: %r (type=%s)', ticket_data.get('total'), type(ticket_data.get('total')))
            if items and len(items) > 0:
                logger.info('GENERATOR RECEIVED item[0].pvp: %r (type=%s)', items[0].get('pvp'), type(items[0].get('pvp')))
            return orig_gen(config, ticket_data, items, cliente_data)

        impresora.ticket_generator.generate = gen_wrapper
    except Exception:
        logger.exception('Could not instrument ticket_generator.generate')

    try:
        texto = impresora.generar_ticket_desde_id(ticket_id)
        logger.info('FINAL TICKET TEXT (preview 2000 chars):\n%s', texto[:2000])
    except Exception:
        logger.exception('Error generating ticket')

    logger.info('Diag finished')


if __name__ == '__main__':
    main()
