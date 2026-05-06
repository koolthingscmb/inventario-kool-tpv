from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.base_datos.money_adapter import read_from_db
from decimal import Decimal

if __name__ == '__main__':
    db = Database('staging/kool_bd_staging.db')
    db.connect()
    row = db.fetch_one("SELECT id, num_ticket, created_at, cajero, cliente, cliente_id, subtotal, total, pagado, cambio, importe_efectivo, importe_tarjeta, tesoro_ganado, tesoro_gastado FROM tickets WHERE id = 73")
    print('TICKET ROW:')
    print(row)
    # show raw numeric fields
    names = ['id','num_ticket','created_at','cajero','cliente','cliente_id','subtotal','total','pagado','cambio','importe_efectivo','importe_tarjeta','tesoro_ganado','tesoro_gastado']
    for n,v in zip(names, row):
        print(n, '=>', repr(v), type(v))
    # try read_from_db on subtotal/total if ints
    for field in ('subtotal','total'):
        val = row[6] if field=='subtotal' else row[7]
        try:
            print(field, 'raw->', val, type(val))
            print(field, 'as int->', int(val))
            print(field, 'read_from_db->', read_from_db(int(val)))
        except Exception as e:
            print('cannot convert', field, e)
