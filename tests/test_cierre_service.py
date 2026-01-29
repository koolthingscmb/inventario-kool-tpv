from datetime import datetime
import pytest

from database import connect, crear_base_de_datos, crear_tablas_tickets, ensure_ticket_schema
from modulos.tpv.cierre_service import CierreService


@pytest.fixture(autouse=True)
def init_db(tmp_path):
    # Use the real DB path but ensure tables exist; tests operate on workspace DB
    crear_base_de_datos()
    crear_tablas_tickets()
    ensure_ticket_schema()
    # clean data to ensure deterministic tests
    conn = connect()
    cur = conn.cursor()
    try:
        cur.execute('DELETE FROM ticket_lines')
    except Exception:
        pass
    try:
        cur.execute('DELETE FROM tickets')
    except Exception:
        pass
    try:
        cur.execute('DELETE FROM cierres_caja')
    except Exception:
        pass
    try:
        conn.commit()
    except Exception:
        pass
    finally:
        try:
            conn.close()
        except Exception:
            pass
    yield


def insert_cierre(cur, fecha_hora, cajero):
    cur.execute('INSERT INTO cierres_caja (fecha_hora, total_ingresos, num_ventas, cajero) VALUES (?,?,?,?)',
                (fecha_hora, 0.0, 0, cajero))
    return cur.lastrowid


def insert_ticket(cur, created_at, total, cajero, cierre_id=None):
    cur.execute('INSERT INTO tickets (created_at, total, cajero, cliente) VALUES (?,?,?,?)',
                (created_at, total, cajero, None))
    tid = cur.lastrowid
    if cierre_id is not None:
        cur.execute('UPDATE tickets SET cierre_id=? WHERE id=?', (cierre_id, tid))
    return tid


def test_un_cierre_un_cajero():
    conn = connect()
    cur = conn.cursor()
    try:
        fecha = '2026-01-10T10:00:00'
        cierre_id = insert_cierre(cur, fecha, 'Alice')
        insert_ticket(cur, '2026-01-10T09:00:00', 100.0, 'Alice', cierre_id)
        insert_ticket(cur, '2026-01-10T09:30:00', 200.0, 'Alice', cierre_id)
        conn.commit()

        svc = CierreService()
        res = svc.ventas_por_cajero('2026-01-10', '2026-01-10')
        assert isinstance(res, list)
        assert len(res) == 1
        assert res[0]['nombre'] == 'Alice'
        assert abs(res[0]['total_ventas'] - 300.0) < 0.001
    finally:
        conn.close()


def test_multiples_cierres_mismo_cajero():
    conn = connect()
    cur = conn.cursor()
    try:
        c1 = insert_cierre(cur, '2026-01-11T08:00:00', 'Bob')
        c2 = insert_cierre(cur, '2026-01-12T18:00:00', 'Bob')
        insert_ticket(cur, '2026-01-11T09:00:00', 150.0, 'Bob', c1)
        insert_ticket(cur, '2026-01-12T10:00:00', 250.0, 'Bob', c2)
        conn.commit()

        svc = CierreService()
        res = svc.ventas_por_cajero('2026-01-11', '2026-01-12')
        # Should aggregate both closures for Bob
        assert any(r['nombre'] == 'Bob' and abs(r['total_ventas'] - 400.0) < 0.001 for r in res)
    finally:
        conn.close()


def test_intervalo_sin_cierres():
    svc = CierreService()
    res = svc.ventas_por_cajero('1999-01-01', '1999-01-02')
    assert res == []
