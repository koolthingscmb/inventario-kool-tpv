import sqlite3
from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.impresion.impresora_service import ImpresoraService


def setup_in_memory_db():
    db = Database(':memory:')
    db.connect()
    conn = db.connection
    cur = conn.cursor()
    # create minimal schema
    cur.execute('''
    CREATE TABLE tickets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        num_ticket INTEGER,
        created_at TEXT,
        cajero TEXT,
        cliente TEXT,
        cliente_id INTEGER,
        subtotal NUMERIC,
        forma_pago TEXT,
        total NUMERIC,
        pagado NUMERIC,
        cambio NUMERIC,
        importe_efectivo NUMERIC,
        importe_tarjeta NUMERIC,
        tesoro_ganado NUMERIC,
        tesoro_gastado NUMERIC,
        ticket_text TEXT
    )
    ''')
    cur.execute('''
    CREATE TABLE ticket_lines (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticket_id INTEGER,
        sku TEXT,
        nombre TEXT,
        cantidad INTEGER,
        precio NUMERIC,
        iva INTEGER,
        line_tipo TEXT
    )
    ''')
    conn.commit()
    return db


def test_generate_ticket_from_cents():
    db = setup_in_memory_db()
    conn = db.connection
    cur = conn.cursor()

    # Insert ticket where monetary fields are stored as integer cents
    cur.execute(
        "INSERT INTO tickets (num_ticket, created_at, cajero, total, forma_pago, importe_efectivo, importe_tarjeta, tesoro_ganado, tesoro_gastado) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (1, '2026-05-04 12:00:00', 'Test', 5000, 'Efectivo', 5000, 0, 0, 0),
    )
    ticket_id = cur.lastrowid

    # Insert two lines: each precio is stored in cents (2500) and cantidad 1 -> total 5000
    cur.execute(
        "INSERT INTO ticket_lines (ticket_id, sku, nombre, cantidad, precio, iva, line_tipo) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (ticket_id, 'SKU1', 'Producto Test', 2, 2500, 21, 'venta'),
    )
    conn.commit()

    impresora = ImpresoraService(db=db, imprimir_en_consola=False)
    texto = impresora.generar_ticket_desde_id(ticket_id)

    assert texto is not None
    # Expect the total to appear as 50.00 € (5000 cents -> 50.00 euros)
    assert '50.00' in texto or '50,00' in texto
    assert '50.00 €' in texto or '50,00 €' in texto
