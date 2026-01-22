import os
import sqlite3
from typing import Optional
from datetime import datetime
import json

# Central DB path for the application
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), 'inventario.db'))


def connect(db_path: Optional[str] = None):
    """Return a sqlite3.Connection to the canonical DB path.

    Pass `db_path` to override (used in tests or scripts).
    """
    path = db_path if db_path else DB_PATH
    return sqlite3.connect(path)


def crear_base_de_datos():
    """Create core tables if they don't exist."""
    conn = connect()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            nombre_boton TEXT,
            sku TEXT UNIQUE NOT NULL,
            categoria TEXT,
            proveedor TEXT,
            tipo_iva INTEGER DEFAULT 21,
            stock_actual INTEGER DEFAULT 0,
            ventas_totales INTEGER DEFAULT 0,
            pvp_variable INTEGER DEFAULT 0,
            descripcion_shopify TEXT,
            notas_internas TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS codigos_barras (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto_id INTEGER,
            ean TEXT NOT NULL,
            FOREIGN KEY(producto_id) REFERENCES productos(id) ON DELETE CASCADE
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS precios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto_id INTEGER,
            pvp REAL DEFAULT 0.0,
            coste REAL DEFAULT 0.0,
            fecha_registro TEXT,
            activo INTEGER DEFAULT 1,
            FOREIGN KEY(producto_id) REFERENCES productos(id) ON DELETE CASCADE
        )
    ''')

    conn.commit()
    conn.close()


def crear_tablas_tickets():
    """Create tickets and ticket_lines tables used to store receipts.

    The schema stores a per-day sequential number `ticket_seq` so each
    day's tickets can be numbered starting at 1 (useful for legal/organizational
    purposes). Lines are stored separately in `ticket_lines`.
    """
    conn = connect()
    cur = conn.cursor()

    cur.execute('''
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            total REAL NOT NULL,
            cajero TEXT,
            cliente TEXT,
            ticket_seq INTEGER DEFAULT 0,
            ticket_no INTEGER UNIQUE,
            forma_pago TEXT,
            pagado REAL,
            cambio REAL,
            notas TEXT
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS ticket_lines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id INTEGER NOT NULL,
            sku TEXT,
            nombre TEXT,
            cantidad REAL,
            precio REAL,
            iva REAL,
            FOREIGN KEY(ticket_id) REFERENCES tickets(id) ON DELETE CASCADE
        )
    ''')

    try:
        cur.execute('CREATE INDEX IF NOT EXISTS idx_tickets_created_at ON tickets(created_at)')
    except Exception:
        pass

    # ensure cierres table exists for day closures
    try:
        cur.execute('''
            CREATE TABLE IF NOT EXISTS cierres (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fecha TEXT NOT NULL,
                    fecha_cierre TEXT NOT NULL,
                    tickets_from INTEGER,
                    tickets_to INTEGER,
                    total REAL,
                    resumen_json TEXT,
                    cajero TEXT,
                    notas TEXT,
                    tipo TEXT DEFAULT 'Z',
                    numero INTEGER
            )
        ''')
    except Exception:
        pass

    conn.commit()
    try:
        conn.close()
    except Exception:
        pass


def ensure_ticket_schema():
    """Ensure `tickets` table has `ticket_no` and `forma_pago` columns (migration safe)."""
    conn = connect()
    cur = conn.cursor()
    try:
        cur.execute("PRAGMA table_info(tickets)")
        cols = [r[1] for r in cur.fetchall()]
    except Exception:
        cols = []
    try:
        if 'ticket_no' not in cols:
            cur.execute('ALTER TABLE tickets ADD COLUMN ticket_no INTEGER')
    except Exception:
        pass
    try:
        if 'forma_pago' not in cols:
            cur.execute("ALTER TABLE tickets ADD COLUMN forma_pago TEXT")
    except Exception:
        pass
    try:
        if 'pagado' not in cols:
            cur.execute('ALTER TABLE tickets ADD COLUMN pagado REAL')
    except Exception:
        pass
    try:
        if 'cambio' not in cols:
            cur.execute('ALTER TABLE tickets ADD COLUMN cambio REAL')
    except Exception:
        pass
    try:
        if 'cierre_id' not in cols:
            cur.execute('ALTER TABLE tickets ADD COLUMN cierre_id INTEGER')
    except Exception:
        pass
    try:
        conn.commit()
    except Exception:
        pass
    try:
        cur.close()
    except Exception:
        pass
    try:
        conn.close()
    except Exception:
        pass


def ensure_product_schema():
    """Apply lightweight migrations to ensure product-related columns/tables exist."""
    conn = connect()
    cur = conn.cursor()
    # Add columns to productos if missing
    try:
        cur.execute("PRAGMA table_info(productos)")
        cols = [c[1] for c in cur.fetchall()]
    except Exception:
        cols = []
    extras = {
        'titulo': "TEXT",
        'stock_minimo': "INTEGER DEFAULT 0",
        'activo': "INTEGER DEFAULT 1",
        'tipo': "TEXT",
        'created_at': "TEXT",
        'updated_at': "TEXT",
        'pending_sync': "INTEGER DEFAULT 0",
        'shopify_taxonomy': "TEXT",
    }
    for col, spec in extras.items():
        if col not in cols:
            try:
                cur.execute(f"ALTER TABLE productos ADD COLUMN {col} {spec}")
            except Exception:
                pass

    cur.execute('''
        CREATE TABLE IF NOT EXISTS product_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto_id INTEGER,
            path TEXT,
            FOREIGN KEY(producto_id) REFERENCES productos(id) ON DELETE CASCADE
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS product_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto_id INTEGER,
            usuario TEXT,
            fecha TEXT,
            cambios TEXT,
            FOREIGN KEY(producto_id) REFERENCES productos(id) ON DELETE CASCADE
        )
    ''')

    conn.commit()
    conn.close()


def close_day(fecha: Optional[str] = None, tipo: str = 'Z', include_category: bool = False, include_products: bool = False, cajero: Optional[str] = None, notas: Optional[str] = None):
    """Compute aggregates for `fecha` (YYYY-MM-DD). Insert a `cierres` row and return a summary dict.

    tipo: 'Z' = cierre definitivo (marca tickets como cerrados), 'X' = cierre informativo (no marca tickets)
    """
    conn = connect()
    cur = conn.cursor()
    try:
        if not fecha:
            fecha = datetime.now().date().isoformat()

        # build WHERE clause depending on cierre type
        if tipo == 'Z':
            ticket_where = "date(created_at)=? AND (cierre_id IS NULL)"
        else:
            ticket_where = "date(created_at)=?"

        # aggregates
        cur.execute(f"SELECT MIN(ticket_no), MAX(ticket_no), COUNT(*), COALESCE(SUM(total),0) FROM tickets WHERE {ticket_where}", (fecha,))
        min_no, max_no, count_tickets, sum_total = cur.fetchone()

        cur.execute(f"SELECT forma_pago, COUNT(*), COALESCE(SUM(total),0) FROM tickets WHERE {ticket_where} GROUP BY forma_pago", (fecha,))
        pagos = [{"forma": r[0] or '', "count": r[1], "total": r[2] or 0.0} for r in cur.fetchall()]

        resumen = {
            "fecha": fecha,
            "tickets_from": min_no,
            "tickets_to": max_no,
            "count_tickets": count_tickets,
            "total": float(sum_total or 0.0),
            "por_forma_pago": pagos
        }

        if include_category:
            cur.execute(f'''
                SELECT COALESCE(p.categoria, ''), SUM(tl.cantidad) as qty, SUM(tl.cantidad * tl.precio) as total
                FROM ticket_lines tl
                JOIN tickets t ON tl.ticket_id = t.id
                JOIN productos p ON tl.sku = p.sku
                WHERE {ticket_where}
                GROUP BY p.categoria
            ''', (fecha,))
            resumen['por_categoria'] = [{"categoria": r[0], "qty": r[1], "total": r[2]} for r in cur.fetchall()]

        if include_products:
            cur.execute(f'''
                SELECT tl.nombre, SUM(tl.cantidad) as qty, SUM(tl.cantidad * tl.precio) as total
                FROM ticket_lines tl
                JOIN tickets t ON tl.ticket_id = t.id
                WHERE {ticket_where}
                GROUP BY tl.nombre
                ORDER BY qty DESC
                LIMIT 10
            ''', (fecha,))
            resumen['top_products'] = [{"nombre": r[0], "qty": r[1], "total": r[2]} for r in cur.fetchall()]

        # If tipo Z and no tickets to close, return message
        if tipo == 'Z' and (count_tickets is None or count_tickets == 0):
            resumen['cierre_id'] = None
            resumen['already_closed'] = False
            resumen['message'] = 'No hay tickets pendientes para cerrar.'
            return resumen

        # persist closure
        ahora = datetime.now().isoformat()
        resumen_json = json.dumps(resumen, default=str, ensure_ascii=False)

        cur.execute('INSERT INTO cierres (fecha, fecha_cierre, tickets_from, tickets_to, total, resumen_json, cajero, notas, tipo) VALUES (?,?,?,?,?,?,?,?,?)', (
            fecha, ahora, min_no, max_no, sum_total, resumen_json, cajero, notas, tipo
        ))
        cierre_id = cur.lastrowid
        try:
            cur.execute('UPDATE cierres SET numero=? WHERE id=?', (cierre_id, cierre_id))
        except Exception:
            pass

        # If tipo Z, assign tickets to this cierre (mark them as closed)
        if tipo == 'Z':
            try:
                cur.execute('UPDATE tickets SET cierre_id=? WHERE date(created_at)=? AND (cierre_id IS NULL)', (cierre_id, fecha))
            except Exception:
                pass

        conn.commit()
        resumen['cierre_id'] = cierre_id
        resumen['already_closed'] = False
        resumen['numero'] = cierre_id
        return resumen
    finally:
        try:
            cur.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    crear_base_de_datos()
    ensure_product_schema()