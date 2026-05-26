import pytest
from decimal import Decimal

from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.base_datos.cierre_service import CierreService
from kool_tpv.modulos.impresion.impresora_service import ImpresoraService


def _prepare_db_with_ticket(db: Database):
    db.connect()
    # Minimal schema needed by CierreService and ImpresoraService
    db.execute_query("""
    CREATE TABLE tickets (
        id INTEGER PRIMARY KEY,
        num_ticket INTEGER,
        created_at TEXT,
        total INTEGER,
        forma_pago TEXT,
        importe_efectivo INTEGER,
        cambio INTEGER,
        importe_tarjeta INTEGER,
        cajero TEXT,
        cierre_id INTEGER
    )
    """)

    db.execute_query("""
    CREATE TABLE ticket_lines (
        id INTEGER PRIMARY KEY,
        ticket_id INTEGER,
        sku TEXT,
        nombre TEXT,
        cantidad INTEGER,
        precio INTEGER,
        iva INTEGER,
        line_tipo TEXT
    )
    """)

    db.execute_query("""
    CREATE TABLE points_movements (
        id INTEGER PRIMARY KEY,
        ticket_id INTEGER,
        puntos INTEGER
    )
    """)

    db.execute_query("""
    CREATE TABLE cierres (
        id INTEGER PRIMARY KEY,
        cierre_num INTEGER,
        fecha_hora TEXT,
        cajero TEXT,
        total_ingresos INTEGER,
        num_ventas INTEGER,
        rango_inicio_ticket INTEGER,
        rango_fin_ticket INTEGER,
        total_efectivo INTEGER,
        total_tarjeta INTEGER,
        total_web INTEGER,
        total_devoluciones INTEGER,
        total_descuentos INTEGER,
        tesoro_ganado REAL,
        tesoro_gastado REAL,
        iva_desglose TEXT,
        base_21 INTEGER,
        iva_21 INTEGER,
        base_4 INTEGER,
        iva_4 INTEGER,
        total_base_imponible INTEGER,
        total_iva INTEGER,
        cierre_text TEXT,
        usuario_id INTEGER
    )
    """)

    db.execute_query("""
    CREATE TABLE cierres_lineas (
        id INTEGER PRIMARY KEY,
        cierre_id INTEGER,
        ticket_id INTEGER,
        ticket_num INTEGER,
        ticket_total INTEGER,
        forma_pago TEXT,
        efectivo INTEGER,
        tarjeta INTEGER
    )
    """)


def test_compute_totals_single_ticket():
    db = Database(':memory:')
    _prepare_db_with_ticket(db)

    # Insert a single ticket: total 1000 cents (10.00 EUR)
    db.execute_query("INSERT INTO tickets (id, num_ticket, created_at, total, forma_pago, importe_efectivo, cambio, importe_tarjeta, cajero) VALUES (?,?,?,?,?,?,?,?,?)",
                     (1, 100, '2026-05-25 10:00:00', 1000, 'efectivo', 1000, 0, 0, 'Tester'))

    # Single line: precio 1000 cents, cantidad 1, IVA 21%
    db.execute_query("INSERT INTO ticket_lines (ticket_id, sku, nombre, cantidad, precio, iva, line_tipo) VALUES (?,?,?,?,?,?,?)",
                     (1, 'SKU1', 'Producto 1', 1, 1000, 21, 'venta'))

    cierre_svc = CierreService(db)
    res = cierre_svc.compute_totals_for_ticket_ids([1])

    # total_ingresos should be 10.0 EUR
    assert isinstance(res, dict)
    assert float(res.get('total_ingresos')) == pytest.approx(10.0)
    # base 21% for a 10.00 gross at 21% VAT is ~8.26 EUR (approx)
    assert float(res.get('base_21')) == pytest.approx(8.26, rel=1e-3)
    # IVA + base should approximately sum to total_ingresos (allow small cent-rounding)
    assert abs((res.get('base_21') + res.get('iva_21')) - res.get('total_ingresos')) < 0.02


def test_generar_cierre_desde_id_outputs_text():
    db = Database(':memory:')
    _prepare_db_with_ticket(db)

    # Insert ticket and line as above
    db.execute_query("INSERT INTO tickets (id, num_ticket, created_at, total, forma_pago, importe_efectivo, cambio, importe_tarjeta, cajero) VALUES (?,?,?,?,?,?,?,?,?)",
                     (1, 101, '2026-05-25 11:00:00', 1000, 'efectivo', 1000, 0, 0, 'Tester'))
    db.execute_query("INSERT INTO ticket_lines (ticket_id, sku, nombre, cantidad, precio, iva, line_tipo) VALUES (?,?,?,?,?,?,?)",
                     (1, 'SKU1', 'Producto 1', 1, 1000, 21, 'venta'))

    cierre_svc = CierreService(db)
    cierre_id = cierre_svc.create_cierre_atomic([1], usuario_id=None, cajero='Tester')
    assert cierre_id is not None

    impresora = ImpresoraService(db=db, imprimir_en_consola=True, modo_impresion='texto')
    texto = impresora.generar_cierre_desde_id(cierre_id)

    assert texto is not None and isinstance(texto, str)
    assert 'CIERRE DE CAJA' in texto
    assert 'Total cierre:' in texto
    # The total amount text should contain '10.00' (formatted by FormatterService)
    assert '10.00' in texto
