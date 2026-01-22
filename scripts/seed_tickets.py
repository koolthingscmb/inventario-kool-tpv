#!/usr/bin/env python3
from datetime import datetime, timedelta
import sys, os
# ensure project root is on sys.path so top-level modules like `database` import correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from database import connect, crear_tablas_tickets, ensure_ticket_schema

NUM_TICKETS = 3
LINES_PER_TICKET = 10

crear_tablas_tickets()
ensure_ticket_schema()

conn = connect()
cur = conn.cursor()

# find next ticket_no
cur.execute('SELECT MAX(ticket_no) FROM tickets')
r = cur.fetchone()
start_no = (r[0] or 0) + 1

now = datetime.now()
created_ids = []
for i in range(NUM_TICKETS):
    created_at = (now + timedelta(seconds=i)).isoformat()
    # prepare lines
    lines = []
    total = 0.0
    for j in range(LINES_PER_TICKET):
        sku = f'SEED-{i+1}-{j+1}'
        nombre = f'Producto semilla {i+1}-{j+1}'
        cantidad = 1
        precio = round(5.0 + j * 0.5, 2)
        iva = 21.0
        lines.append((sku, nombre, cantidad, precio, iva))
        total += cantidad * precio

    ticket_no = start_no + i
    cajero = 'seed'
    cliente = 'cliente_seed'
    forma_pago = 'Efectivo'
    pagado = total
    cambio = 0.0

    cur.execute('''INSERT INTO tickets (created_at, total, cajero, cliente, ticket_no, forma_pago, pagado, cambio) VALUES (?,?,?,?,?,?,?,?)''', (
        created_at, total, cajero, cliente, ticket_no, forma_pago, pagado, cambio
    ))
    ticket_id = cur.lastrowid
    for (sku, nombre, cantidad, precio, iva) in lines:
        cur.execute('''INSERT INTO ticket_lines (ticket_id, sku, nombre, cantidad, precio, iva) VALUES (?,?,?,?,?,?)''', (
            ticket_id, sku, nombre, cantidad, precio, iva
        ))
    created_ids.append(ticket_id)

conn.commit()
cur.close()
conn.close()

print(f'Inserted tickets: {created_ids}')
print(f'Lines per ticket: {LINES_PER_TICKET}, tickets: {NUM_TICKETS}')
