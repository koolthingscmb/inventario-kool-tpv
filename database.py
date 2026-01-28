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
    # Use a short timeout to reduce immediate 'database is locked' errors
    conn = sqlite3.connect(path, timeout=5.0)
    try:
        # Enable WAL to improve concurrency between readers and writers
        conn.execute("PRAGMA journal_mode=WAL")
    except Exception:
        # If PRAGMA fails for any reason, continue with the connection
        pass
    # Return rows as sqlite3.Row to allow access by column name
    conn.row_factory = sqlite3.Row
    return conn


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

    # ensure ticket_seq exists for safe ticket numbering
    try:
        cur.execute('''
            CREATE TABLE IF NOT EXISTS ticket_seq (
                name TEXT PRIMARY KEY,
                val INTEGER
            )
        ''')
        cur.execute("INSERT OR IGNORE INTO ticket_seq (name, val) VALUES ('ticket_no', 0)")
    except Exception:
        pass

    # ensure cierres_caja table exists for day closures
    try:
        cur.execute('''
            CREATE TABLE IF NOT EXISTS cierres_caja (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha_hora TEXT NOT NULL,
                total_ingresos REAL DEFAULT 0.0,
                num_ventas INTEGER DEFAULT 0,
                cajero TEXT,
                total_efectivo REAL DEFAULT 0.0,
                total_tarjeta REAL DEFAULT 0.0,
                total_web REAL DEFAULT 0.0,
                puntos_ganados INTEGER DEFAULT 0,
                puntos_canjeados INTEGER DEFAULT 0
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


def close_day(fecha=None, tipo='Z', include_category=False, include_products=False, cajero=None, notas=None):
    if not fecha:
        fecha = datetime.now().date().isoformat()

    conn = connect()
    cur = conn.cursor()
    try:
        # 1. Definir qué tickets entran en el cierre
        ticket_where = "date(created_at)=? AND (cierre_id IS NULL)" if tipo == 'Z' else "date(created_at)=?"

        # 2. Cálculos económicos básicos
        cur.execute(f"SELECT COUNT(*), COALESCE(SUM(total),0) FROM tickets WHERE {ticket_where}", (fecha,))
        num_ventas, total_ingresos = cur.fetchone()

        # 3. Desglose por forma de pago (Lógica Blindada)
        val_efectivo = 0.0; val_tarjeta = 0.0; val_web = 0.0
        cur.execute(f"SELECT forma_pago, SUM(total) FROM tickets WHERE {ticket_where} GROUP BY forma_pago", (fecha,))
        for forma, total in cur.fetchall():
            f = (forma or "").upper()
            if f == 'EFECTIVO':
                val_efectivo = float(total or 0)
            elif f == 'TARJETA':
                val_tarjeta = float(total or 0)
            elif f == 'WEB':
                val_web = float(total or 0)

        # 4. Cálculo de Fidelización
        cur.execute(f"SELECT COALESCE(SUM(puntos_ganados),0), COALESCE(SUM(puntos_canjeados),0) FROM tickets WHERE {ticket_where}", (fecha,))
        pts_ganados, pts_canjeados = cur.fetchone()

        # 5. GUARDADO REAL EN LA BASE DE DATOS (Asegurar que todas las columnas reciban su variable)
        ahora = datetime.now().isoformat()
        cur.execute('''
            INSERT INTO cierres_caja 
            (fecha_hora, total_ingresos, num_ventas, cajero, total_efectivo, total_tarjeta, total_web, puntos_ganados, puntos_canjeados) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (ahora, total_ingresos, num_ventas, cajero, val_efectivo, val_tarjeta, val_web, pts_ganados, pts_canjeados))
        
        cierre_id = cur.lastrowid

        # 6. Marcar tickets como cerrados si es tipo Z
        if tipo == 'Z':
            cur.execute(f"UPDATE tickets SET cierre_id=? WHERE {ticket_where}", (cierre_id, fecha))
        
        conn.commit()
        
        # Devolver el resumen para que la UI lo pinte (usando las mismas variables que acabamos de guardar)
        return {
            "numero": cierre_id, "fecha": fecha, "total": total_ingresos, "count_tickets": num_ventas,
            "total_efectivo": val_efectivo, "total_tarjeta": val_tarjeta, "total_web": val_web,
            "puntos_ganados": pts_ganados, "puntos_canjeados": pts_canjeados, "cierre_id": cierre_id
        }
    finally:
        conn.close()


if __name__ == "__main__":
    crear_base_de_datos()
    ensure_product_schema()