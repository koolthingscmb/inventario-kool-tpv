#!/usr/bin/env python3
import logging
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.impresion.impresora_service import ImpresoraService

logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(message)s')

DB_PATH = str(ROOT / 'kool_tpv' / 'base_datos' / 'kool_bd.db')

def main():
    db = Database(DB_PATH)
    db.connect()

    # Obtener último ticket id
    try:
        row = db.fetch_one("SELECT MAX(id) FROM tickets")
        ticket_id = row[0] if row and row[0] is not None else None
    except Exception:
        ticket_id = None

    if not ticket_id:
        print('No hay tickets en la BD para generar.')
        return

    service = ImpresoraService(db=db, imprimir_en_consola=False, modo_impresion='texto')

    # Llamar a generar_ticket_desde_id para que se impriman los logs añadidos
    texto = service.generar_ticket_desde_id(int(ticket_id))
    print('--- GENERAR_TICKET_DESDE_ID RETURNED ---')
    print(texto)

if __name__ == '__main__':
    main()
