import sqlite3
from database import connect

conn = connect()
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print('PRAGMA table_info(productos):')
try:
    cur.execute("PRAGMA table_info(productos);")
    for r in cur.fetchall():
        print(dict(r))
except Exception as e:
    print('Error PRAGMA productos:', e)

print('\nProductos sample:')
try:
    cur.execute("SELECT proveedor, sku, nombre FROM productos LIMIT 20;")
    for r in cur.fetchall():
        print(dict(r))
except Exception as e:
    print('Error selecting productos:', e)

print('\nTickets in range:')
try:
    cur.execute("SELECT id, created_at, cierre_id, cliente FROM tickets WHERE created_at BETWEEN '2026-01-01' AND '2026-01-29' LIMIT 20;")
    rows = cur.fetchall()
    if not rows:
        print('No tickets in range')
    for r in rows:
        print(dict(r))
except Exception as e:
    print('Error selecting tickets:', e)

print('\nTicket_lines sample:')
try:
    cur.execute("SELECT id, ticket_id, sku, cantidad, precio FROM ticket_lines LIMIT 20;")
    for r in cur.fetchall():
        print(dict(r))
except Exception as e:
    print('Error selecting ticket_lines:', e)

print('\nCierres_caja in range:')
try:
    cur.execute("SELECT * FROM cierres_caja WHERE fecha_hora BETWEEN '2026-01-01' AND '2026-01-29';")
    rows = cur.fetchall()
    if not rows:
        print('No cierres in range')
    for r in rows:
        print(dict(r))
except Exception as e:
    print('Error selecting cierres_caja:', e)

print('\nProveedores sample:')
try:
    cur.execute("SELECT id, nombre FROM proveedores LIMIT 20;")
    for r in cur.fetchall():
        print(dict(r))
except Exception as e:
    print('Error selecting proveedores:', e)

conn.close()
