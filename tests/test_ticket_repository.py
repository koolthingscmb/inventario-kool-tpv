import pytest
from unittest.mock import MagicMock
from decimal import Decimal

from kool_tpv.modulos.ticket.ticket_repository import TicketRepository
from kool_tpv.base_datos.money_adapter import prepare_for_db


@pytest.fixture
def repo_and_cursor():
    mock_db = MagicMock()
    mock_cursor = MagicMock()
    mock_db.connection.cursor.return_value = mock_cursor
    repo = TicketRepository(mock_db)
    return repo, mock_cursor


def test_insert_ticket_uses_cents(repo_and_cursor):
    repo, cur = repo_and_cursor
    tid = repo.insert_ticket(
        created_at='2026-05-08 12:00:00',
        cajero='user',
        cliente='ACME',
        cliente_id=1,
        num_ticket=5,
        subtotal_cents=prepare_for_db(Decimal('10.00')),
        forma_pago='Efectivo',
        total_cents=prepare_for_db(Decimal('12.34')),
        pagado_cents=prepare_for_db(Decimal('20.00')),
        cambio_cents=prepare_for_db(Decimal('7.66')),
        importe_efectivo_cents=prepare_for_db(Decimal('20.00')),
        importe_tarjeta_cents=0,
        descuento_euros_cents=0,
        descuento_tipo=None,
        descuento_valor=None,
        tesoro_ganado_str='0',
        tesoro_gastado_str='0',
        ticket_text_snapshot=None,
    )
    # lastrowid returned from mock default is MagicMock; ensure execute called
    assert cur.execute.call_count == 1
    args, kwargs = cur.execute.call_args
    params = args[1]
    assert isinstance(params[2], str) or params[2] == 'ACME' or params[2] is None
    # total stored as integer cents
    assert params[7] == int(prepare_for_db(Decimal('12.34')))


def test_insert_ticket_line_and_stock(repo_and_cursor):
    repo, cur = repo_and_cursor
    line_id = repo.insert_ticket_line(1, 'SKU1', 'Producto', 2, prepare_for_db(Decimal('5.00')), 21, 'venta', 10)
    assert cur.execute.call_count == 1
    args, _ = cur.execute.call_args
    assert 'INSERT INTO ticket_lines' in args[0]

    # update stock
    repo.update_producto_stock_y_ventas(10, -2, 2)
    assert cur.execute.call_count >= 2
