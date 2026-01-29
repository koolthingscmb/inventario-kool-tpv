import os
import tempfile
import sqlite3
import database
from modulos.tpv.fidelizacion_service import FidelizacionService


def setup_temp_db():
    tf = tempfile.NamedTemporaryFile(delete=False)
    tf.close()
    db_path = tf.name
    # point global DB to temp file
    old = database.DB_PATH
    database.DB_PATH = db_path
    # create tables
    database.crear_base_de_datos()
    database.crear_tablas_tickets()
    # ensure ticket schema migrations (cliente_id and other columns)
    try:
        database.ensure_ticket_schema()
    except Exception:
        pass
    # ensure puntos columns exist for tests
    conn = database.connect()
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(tickets)")
        cols = [r[1] for r in cur.fetchall()]
        if 'puntos_ganados' not in cols:
            try:
                cur.execute("ALTER TABLE tickets ADD COLUMN puntos_ganados REAL DEFAULT 0")
            except Exception:
                pass
        if 'puntos_canjeados' not in cols:
            try:
                cur.execute("ALTER TABLE tickets ADD COLUMN puntos_canjeados REAL DEFAULT 0")
            except Exception:
                pass
        if 'puntos_total_momento' not in cols:
            try:
                cur.execute("ALTER TABLE tickets ADD COLUMN puntos_total_momento REAL DEFAULT 0")
            except Exception:
                pass
        conn.commit()
    finally:
        try:
            conn.close()
        except Exception:
            pass
    return db_path, old


def teardown_temp_db(db_path, old):
    try:
        os.unlink(db_path)
    except Exception:
        pass
    database.DB_PATH = old


def test_desglose_clientes_registrados():
    db_path, old = setup_temp_db()
    try:
        conn = database.connect()
        cur = conn.cursor()
        # create clientes table minimal
        cur.execute('''CREATE TABLE IF NOT EXISTS clientes (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, puntos_fidelidad REAL DEFAULT 0)''')
        # insert clients
        cur.execute("INSERT INTO clientes (nombre) VALUES ('Alice')")
        cur.execute("INSERT INTO clientes (nombre) VALUES ('Bob')")
        alice_id = cur.lastrowid - 1
        bob_id = cur.lastrowid
        # insert tickets with points
        cur.execute("INSERT INTO tickets (created_at, total, cajero, cliente, cliente_id, puntos_ganados, puntos_canjeados) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    ('2026-01-10T10:00:00', 10.0, 'T1', 'Alice', alice_id, 5.0, 0.0))
        cur.execute("INSERT INTO tickets (created_at, total, cajero, cliente, cliente_id, puntos_ganados, puntos_canjeados) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    ('2026-01-11T11:00:00', 20.0, 'T1', 'Bob', bob_id, 2.0, 1.0))
        conn.commit()
        svc = FidelizacionService()
        res = svc.desglose_puntos_periodo('2026-01-09', '2026-01-12')
        assert abs(res['puntos_otorgados'] - 7.0) < 1e-6
        assert abs(res['puntos_gastados'] - 1.0) < 1e-6
        names = [c['nombre'] for c in res['clientes_otorgados']]
        assert 'Alice' in names and 'Bob' in names
    finally:
        try:
            conn.close()
        except Exception:
            pass
        teardown_temp_db(db_path, old)


def test_desglose_clientes_no_relacionados():
    db_path, old = setup_temp_db()
    try:
        conn = database.connect()
        cur = conn.cursor()
        cur.execute('''CREATE TABLE IF NOT EXISTS clientes (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, puntos_fidelidad REAL DEFAULT 0)''')
        # insert a ticket with a client name that doesn't exist in clientes
        cur.execute("INSERT INTO tickets (created_at, total, cajero, cliente, puntos_ganados, puntos_canjeados) VALUES (?, ?, ?, ?, ?, ?)",
                    ('2026-01-15T12:00:00', 15.0, 'T1', 'Unknown', 3.0, 0.0))
        conn.commit()
        svc = FidelizacionService()
        res = svc.desglose_puntos_periodo('2026-01-14', '2026-01-16')
        assert abs(res['puntos_otorgados'] - 3.0) < 1e-6
        assert res['clientes_otorgados'][0]['cliente_id'] is None
    finally:
        try:
            conn.close()
        except Exception:
            pass
        teardown_temp_db(db_path, old)


def test_desglose_periodo_sin_transacciones():
    db_path, old = setup_temp_db()
    try:
        # no tickets inserted
        svc = FidelizacionService()
        res = svc.desglose_puntos_periodo('2000-01-01', '2000-01-02')
        assert res['puntos_otorgados'] == 0
        assert res['puntos_gastados'] == 0
        assert res['clientes_otorgados'] == []
        assert res['clientes_gastados'] == []
    finally:
        teardown_temp_db(db_path, old)
