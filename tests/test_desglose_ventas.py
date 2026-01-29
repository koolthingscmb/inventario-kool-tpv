import tempfile
import os
import math
from datetime import datetime

import database
from modulos.tpv.cierre_service import CierreService


def setup_temp_db():
    fd, path = tempfile.mkstemp(prefix='test_db_', suffix='.db')
    os.close(fd)
    database.DB_PATH = path
    database.crear_base_de_datos()
    database.crear_tablas_tickets()
    # ensure optional product columns like 'tipo' exist
    try:
        database.ensure_product_schema()
    except Exception:
        pass
    return path


def teardown_temp_db(path):
    try:
        os.remove(path)
    except Exception:
        pass


def insert_ticket_with_lines(conn, created_at_iso, lines):
    cur = conn.cursor()
    total = sum(l['cantidad'] * l['precio'] for l in lines)
    cur.execute('INSERT INTO tickets (created_at, total, cajero, forma_pago) VALUES (?, ?, ?, ?)', (created_at_iso, total, 'TEST', 'EFECTIVO'))
    tid = cur.lastrowid
    for l in lines:
        cur.execute('INSERT INTO ticket_lines (ticket_id, sku, nombre, cantidad, precio, iva) VALUES (?,?,?,?,?,?)', (
            tid, l.get('sku', 'SKU'), l.get('nombre', 'X'), l['cantidad'], l['precio'], l['iva']
        ))
    conn.commit()
    return tid, total


def test_desglose_ventas_multiple_categories_types_articles():
    path = setup_temp_db()
    try:
        conn = database.connect()
        # Ticket A: category Cat1, type Type1
        # product sku P1 (categoria Cat1, tipo Type1)
        conn.execute("INSERT INTO productos (sku, nombre, categoria, tipo) VALUES ('P1','Prod1','Cat1','Type1')")
        conn.execute("INSERT INTO productos (sku, nombre, categoria, tipo) VALUES ('P2','Prod2','Cat2','Type2')")
        # Lines
        created_at = '2026-01-30T10:00:00'
        lines1 = [{'sku':'P1','nombre':'Prod1','cantidad':2,'precio':10.0,'iva':21.0},
                  {'sku':'P2','nombre':'Prod2','cantidad':1,'precio':5.0,'iva':10.0}]
        insert_ticket_with_lines(conn, created_at, lines1)

        svc = CierreService()
        desglose = svc.desglose_ventas('2026-01-30T00:00:00','2026-01-30T23:59:59')
        por_cat = {d['categoria']: d for d in desglose['por_categoria']}
        assert 'Cat1' in por_cat and 'Cat2' in por_cat
        assert math.isclose(por_cat['Cat1']['qty'], 2, abs_tol=0.01)
        assert math.isclose(por_cat['Cat1']['total'], 20.0, abs_tol=0.01)
        conn.close()
    finally:
        teardown_temp_db(path)


def test_desglose_ventas_no_sales():
    path = setup_temp_db()
    try:
        svc = CierreService()
        desglose = svc.desglose_ventas('2100-01-01T00:00:00','2100-01-02T00:00:00')
        assert desglose['por_categoria'] == []
        assert desglose['por_tipo'] == []
        assert desglose['por_articulo'] == []
    finally:
        teardown_temp_db(path)


def test_desglose_ventas_single_article():
    path = setup_temp_db()
    try:
        conn = database.connect()
        conn.execute("INSERT INTO productos (sku, nombre, categoria, tipo) VALUES ('PX','X','C','T')")
        created_at = '2026-02-02T09:00:00'
        lines = [{'sku':'PX','nombre':'X','cantidad':3,'precio':7.0,'iva':21.0}]
        insert_ticket_with_lines(conn, created_at, lines)
        svc = CierreService()
        desglose = svc.desglose_ventas('2026-02-02T00:00:00','2026-02-02T23:59:59')
        assert len(desglose['por_articulo']) == 1
        art = desglose['por_articulo'][0]
        assert math.isclose(art['qty'], 3, abs_tol=0.01)
        assert math.isclose(art['total'], 21.0, abs_tol=0.01)
        conn.close()
    finally:
        teardown_temp_db(path)
