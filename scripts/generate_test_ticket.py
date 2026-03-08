#!/usr/bin/env python3
import sys
import logging
from pathlib import Path

# Asegurar que el paquete kool_tpv sea importable
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.impresion.impresora_service import ImpresoraService
from kool_tpv.modulos.impresion.ticket_type import TicketType

logging.basicConfig(level=logging.INFO)

DB_PATH = str(ROOT / 'kool_tpv' / 'base_datos' / 'kool_bd.db')

def main():
    db = Database(DB_PATH)
    db.connect()

    # Forzar valores de header/footer en la tabla configuracion
    try:
        db.execute_query("INSERT OR REPLACE INTO configuracion (clave, valor) VALUES (?, ?)", ('ticket_header_venta', 'HEADER CHANGED {num_ticket}'))
        db.execute_query("INSERT OR REPLACE INTO configuracion (clave, valor) VALUES (?, ?)", ('ticket_footer_venta', 'FOOTER CHANGED {fecha}'))
        print('WROTE CONFIG: ticket_header_venta / ticket_footer_venta')
    except Exception as e:
        print('Error writing config:', e)

    service = ImpresoraService(db=db, imprimir_en_consola=False, modo_impresion='texto')

    # Recargar explícitamente (simula la recarga antes de imprimir)
    service.config = service._load_config_from_db()

    # Datos de ticket de ejemplo
    ticket_data = {
        'num_ticket': 'TEST123',
        'fecha': '2026-02-26',
        'hora': '12:00',
        'cajero': 'tester',
        'subtotal': 10.0,
        'iva_desglose': {21: 2.0},
        'total': 12.0,
        'forma_pago': 'Efectivo',
        'entregado': 12.0,
        'cambio': 0.0,
        'importe_efectivo': 12.0,
    }

    items = [
        {'nombre': 'Producto A', 'cantidad': 1, 'precio': 10.0, 'total': 10.0},
        {'nombre': 'Producto B', 'cantidad': 1, 'precio': 0.0, 'total': 0.0, 'line_tipo': 'devolucion'},
    ]

    # Generar ticket en texto y mostrar tal cual
    texto = service.ticket_generator.generate(service.config, ticket_data, items)
    print('--- TICKET OUTPUT START ---')
    print(texto)
    print('--- TICKET OUTPUT END ---')

if __name__ == '__main__':
    main()
