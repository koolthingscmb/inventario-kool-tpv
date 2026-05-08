import pytest
from unittest.mock import MagicMock
from decimal import Decimal

from kool_tpv.modulos.fidelizacion.fidelizacion_repository import FidelizacionRepository
from kool_tpv.base_datos.money_adapter import prepare_for_db, read_from_db


@pytest.fixture
def repo_and_mocks():
    mock_db = MagicMock()
    mock_cursor = MagicMock()
    mock_db.connection.cursor.return_value = mock_cursor
    repo = FidelizacionRepository(mock_db)
    return repo, mock_db, mock_cursor


def test_actualizar_cliente_loyalty_executes_update_with_cents(repo_and_mocks):
    repo, mock_db, mock_cursor = repo_and_mocks
    cliente_id = 42
    puntos_otorgar = Decimal('1.50')
    puntos_restar = Decimal('0.25')
    puntos_gastados = Decimal('0.75')
    total_ticket = Decimal('15.00')
    unidades_vendidas = 3
    fecha = '2026-05-08'

    repo.actualizar_cliente_loyalty(
        cliente_id,
        puntos_otorgar,
        puntos_restar,
        puntos_gastados,
        total_ticket,
        unidades_vendidas,
        fecha,
    )

    # Ensure execute was called once
    assert mock_cursor.execute.call_count == 1
    args, kwargs = mock_cursor.execute.call_args
    # params are the second positional argument
    params = args[1]

    # Compute expected cents
    expected_delta_tesoro = int(prepare_for_db(puntos_otorgar - (puntos_restar + puntos_gastados)))
    expected_delta_historico = int(prepare_for_db(puntos_otorgar - puntos_restar))
    expected_delta_gastado = int(prepare_for_db(puntos_gastados))
    expected_total_ticket = int(prepare_for_db(total_ticket))

    assert params[0] == expected_delta_tesoro
    assert params[1] == expected_delta_historico
    assert params[2] == expected_delta_gastado
    assert params[3] == expected_total_ticket
    assert params[4] == unidades_vendidas
    assert params[5] == fecha
    assert params[6] == cliente_id


def test_insertar_movimiento_puntos_saves_cents(repo_and_mocks):
    repo, mock_db, mock_cursor = repo_and_mocks
    cliente_id = 7
    puntos = Decimal('2.35')
    motivo = 'venta'
    ticket_id = 99
    usuario_id = 5

    repo.insertar_movimiento_puntos(cliente_id, puntos, motivo, ticket_id, usuario_id)

    assert mock_cursor.execute.call_count == 1
    args, kwargs = mock_cursor.execute.call_args
    params = args[1]

    # puntos stored as cents
    assert params[1] == int(prepare_for_db(puntos))
    assert params[0] == cliente_id
    assert params[2] == motivo
    assert params[3] == ticket_id
    assert params[4] == usuario_id


def test_recalcular_nivel_cliente_executes_update_with_ids(repo_and_mocks):
    repo, mock_db, mock_cursor = repo_and_mocks
    cliente_id = 13
    repo.recalcular_nivel_cliente(cliente_id)
    assert mock_cursor.execute.call_count == 1
    args, kwargs = mock_cursor.execute.call_args
    params = args[1]
    assert params == (cliente_id, cliente_id)


def test_obtener_tesoro_cliente_returns_decimals(repo_and_mocks):
    repo, mock_db, mock_cursor = repo_and_mocks
    # Return cents values
    mock_cursor.fetchone.return_value = (1000, 2500, 500)
    res = repo.obtener_tesoro_cliente(1)
    assert res['total'] == read_from_db(1000)
    assert res['historico'] == read_from_db(2500)
    assert res['gastado'] == read_from_db(500)


def test_obtener_tesoro_cliente_not_found_returns_zero(repo_and_mocks):
    repo, mock_db, mock_cursor = repo_and_mocks
    mock_cursor.fetchone.return_value = None
    res = repo.obtener_tesoro_cliente(999)
    assert res['total'] == Decimal('0')
    assert res['historico'] == Decimal('0')
    assert res['gastado'] == Decimal('0')
