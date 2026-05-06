from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from kool_tpv.base_datos.db_wrapper import Database

DB_PATH = str(ROOT / 'kool_tpv' / 'base_datos' / 'kool_bd.db')
print('Using DB:', DB_PATH)

db = Database(DB_PATH)
db.connect()

ticket_id = 73
row = db.fetch_one("SELECT id, num_ticket, ticket_text FROM tickets WHERE id = ?", (ticket_id,))
if row:
    ticket_id, num_ticket, ticket_text = row
    print(f"TICKET ID: {ticket_id}, NUM: {num_ticket}")
    print('='*60)
    print(ticket_text)
    print('='*60)
    if ticket_text and '4028.10' in ticket_text:
        print('\nCONFIRMADO: Snapshot contiene 4028.10 (céntimos sin convertir)')
    elif ticket_text and '48.74' in ticket_text:
        print('\nSnapshot correcto: 48.74 €')
    else:
        print('\nNi 4028.10 ni 48.74 encontrados en el snapshot')
else:
    print(f'Ticket id={ticket_id} no encontrado.')

logpath = Path(ROOT / 'logs' / 'application.log')
if logpath.exists():
    print('\n-- Logs relevantes --')
    for l in logpath.read_text(encoding='utf-8', errors='ignore').splitlines()[-1000:]:
        if 'Ticket guardado' in l or 'UPDATE tickets SET ticket_text' in l or 'VERIFICACIÓN SNAPSHOT GUARDADO' in l or 'save_ticket' in l:
            print(l)
else:
    print('\nNo se encontró logs/application.log')
