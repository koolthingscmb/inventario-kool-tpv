import tempfile
import os
import json
import math
from datetime import datetime

import database
from modulos.tpv.cierre_service import CierreService


def setup_temp_db():
    fd, path = tempfile.mkstemp(prefix='test_db_', suffix='.db')
    os.close(fd)
    database.DB_PATH = path
    # create schema
    database.crear_base_de_datos()
    database.crear_tablas_tickets()
    return path


def teardown_temp_db(path):
    try:
        os.remove(path)
    except Exception:
        pass


def insert_ticket_with_lines(conn, created_at_iso, lines):
    cur = conn.cursor()
    # compute total as sum(quantity * price) (price includes IVA)
    total = sum(l['cantidad'] * l['precio'] for l in lines)
    cur.execute('INSERT INTO tickets (created_at, total, cajero, forma_pago) VALUES (?, ?, ?, ?)', (created_at_iso, total, 'TEST', 'EFECTIVO'))
    tid = cur.lastrowid
    for l in lines:
        cur.execute('INSERT INTO ticket_lines (ticket_id, sku, nombre, cantidad, precio, iva) VALUES (?,?,?,?,?,?)', (
            tid, l.get('sku', 'SKU'), l.get('nombre', 'X'), l['cantidad'], l['precio'], l['iva']
        ))
    conn.commit()
    return tid, total


def test_desglose_multiple_iva_and_sums():
    path = setup_temp_db()
    try:
        conn = database.connect()
        # ticket 1: IVA 21%, price includes IVA
        created_at = '2026-01-29T10:00:00'
        lines1 = [
            {'cantidad': 1, 'precio': 22.0, 'iva': 21.0},
            {'cantidad': 2, 'precio': 21.0, 'iva': 21.0},
        ]
        # ticket 2: IVA 10%
        created_at2 = '2026-01-29T11:00:00'
        lines2 = [
            {'cantidad': 1, 'precio': 11.0, 'iva': 10.0},
        ]
        tid1, tot1 = insert_ticket_with_lines(conn, created_at, lines1)
        tid2, tot2 = insert_ticket_with_lines(conn, created_at2, lines2)

        svc = CierreService()
        impuestos = svc.desglose_impuestos_periodo('2026-01-29T00:00:00', '2026-01-29T23:59:59')
        # should contain both 21 and 10
        tasas = sorted([i['iva'] for i in impuestos])
        assert 10.0 in tasas and 21.0 in tasas

        # Sum totals by service equals tickets totals
        total_lines = sum(i['total'] for i in impuestos)
        tickets_total = tot1 + tot2
        assert math.isclose(total_lines, tickets_total, abs_tol=0.01)

        # Each line: base + cuota == total (within tolerance)
        for i in impuestos:
            assert math.isclose(i['base'] + i['cuota'], i['total'], abs_tol=0.01)

        conn.close()
    finally:
        teardown_temp_db(path)


def test_desglose_no_sales_returns_empty():
    path = setup_temp_db()
    try:
        svc = CierreService()
        impuestos = svc.desglose_impuestos_periodo('2100-01-01T00:00:00', '2100-01-02T00:00:00')
        assert impuestos == []
    finally:
        teardown_temp_db(path)


def test_desglose_ticket_method():
    path = setup_temp_db()
    try:
        conn = database.connect()
        created_at = '2026-02-01T09:00:00'
        lines = [
            {'cantidad': 3, 'precio': 10.0, 'iva': 21.0},
        ]
        tid, tot = insert_ticket_with_lines(conn, created_at, lines)
        svc = CierreService()
        impuestos = svc.desglose_impuestos_ticket(tid)
        assert len(impuestos) == 1
        imp = impuestos[0]
        assert math.isclose(imp['total'], tot, abs_tol=0.01)
        assert math.isclose(imp['base'] + imp['cuota'], imp['total'], abs_tol=0.01)
        conn.close()
    finally:
        teardown_temp_db(path)
