from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.base_datos.money_adapter import read_from_db
from decimal import Decimal

if __name__ == '__main__':
    db = Database('staging/kool_bd_staging.db')
    db.connect()
    rows = db.fetch_all("SELECT sku,nombre,cantidad,precio,iva,line_tipo FROM ticket_lines WHERE ticket_id = 73")
    print('DB ROWS:')
    for r in rows:
        print(r)
        raw = r[3]
        print(' raw type', type(raw), 'raw repr', repr(raw))
        try:
            cents = int(raw)
            euros = read_from_db(cents)
            print(' read_from_db ->', euros, type(euros))
        except Exception as e:
            print(' read_from_db error', e)
