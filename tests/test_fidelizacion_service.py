import pytest
from unittest.mock import MagicMock
from decimal import Decimal

from kool_tpv.modulos.clientes.fidelizacion_service import FidelizacionService


@pytest.fixture
def service():
    mock_db = MagicMock()
    svc = FidelizacionService(mock_db)
    # default global porcentaje
    svc.config_service.get_fide_porcentaje_global = MagicMock(return_value=Decimal('2.5'))
    return svc


def make_fetch_one_side_effect(mapping):
    def _side_effect(query, params):
        pid = params[0]
        return mapping.get(pid)
    return _side_effect


def test_obtener_porcentaje_producto_con_valor_especifico(service):
    # Producto con valor específico (porcentaje)
    service.db.fetch_one.side_effect = make_fetch_one_side_effect({
        1: ('porcentaje', '10', None, None)
    })
    pct = service.obtener_porcentaje_producto(1)
    assert isinstance(pct, Decimal)
    assert pct.quantize(Decimal('0.01')) == Decimal('10.00')


def test_obtener_porcentaje_producto_fallback_a_tipo(service):
    # Producto sin valor pero con porcentaje en tipo
    service.db.fetch_one.side_effect = make_fetch_one_side_effect({
        2: (None, None, '7', None)
    })
    pct = service.obtener_porcentaje_producto(2)
    assert pct.quantize(Decimal('0.01')) == Decimal('7.00')


def test_obtener_porcentaje_producto_fallback_a_global(service):
    # Producto inexistente -> usar global
    service.db.fetch_one.side_effect = make_fetch_one_side_effect({})
    pct = service.obtener_porcentaje_producto(999)
    assert pct.quantize(Decimal('0.01')) == Decimal('2.50')


def test_obtener_fidelizacion_producto_con_fijo(service):
    # Producto con tipo fijo y valor
    service.db.fetch_one.side_effect = make_fetch_one_side_effect({
        3: ('fijo', '0.75', None, None)
    })
    cfg = service.obtener_fidelizacion_producto(3)
    assert cfg['tipo'] == 'fijo'
    assert cfg['valor'].quantize(Decimal('0.01')) == Decimal('0.75')


def test_obtener_fidelizacion_producto_usa_tipo(service):
    # Producto sin valor, usa tipo.pct
    service.db.fetch_one.side_effect = make_fetch_one_side_effect({
        4: (None, None, '8', None)
    })
    cfg = service.obtener_fidelizacion_producto(4)
    assert cfg['tipo'] == 'porcentaje'
    assert cfg['valor'].quantize(Decimal('0.01')) == Decimal('8.00')


def test_obtener_fidelizacion_producto_usa_categoria(service):
    # Producto sin valor ni tipo, usa categoria.pct
    service.db.fetch_one.side_effect = make_fetch_one_side_effect({
        5: (None, None, None, '6')
    })
    cfg = service.obtener_fidelizacion_producto(5)
    assert cfg['valor'].quantize(Decimal('0.01')) == Decimal('6.00')


def test_calcular_puntos_ganados_sin_canje(service):
    # Single percentage item
    service.db.fetch_one.side_effect = make_fetch_one_side_effect({
        10: (None, None, '10', None)
    })
    items = [{'id': 10, 'pvp': Decimal('10.00'), 'cantidad': 2}]
    pts = service.calcular_puntos_ganados(items, puntos_canjeados=Decimal('0'))
    assert pts.quantize(Decimal('0.01')) == Decimal('2.00')


def test_calcular_puntos_ganados_con_fijo(service):
    # Single fixed item
    service.db.fetch_one.side_effect = make_fetch_one_side_effect({
        11: ('fijo', '0.50', None, None)
    })
    items = [{'id': 11, 'pvp': Decimal('5.00'), 'cantidad': 3}]
    pts = service.calcular_puntos_ganados(items)
    assert pts.quantize(Decimal('0.01')) == Decimal('1.50')


def test_calcular_puntos_ganados_multiple_combinado(service):
    # Multiple items percentage + fixed
    service.db.fetch_one.side_effect = make_fetch_one_side_effect({
        20: (None, None, '5', None),
        21: ('fijo', '1.00', None, None)
    })
    items = [
        {'id': 20, 'pvp': Decimal('20.00'), 'cantidad': 1},  # 5% of 20 = 1.00
        {'id': 21, 'pvp': Decimal('0.00'), 'cantidad': 2}    # fixed 1.00 *2 =2.00
    ]
    pts = service.calcular_puntos_ganados(items)
    assert pts.quantize(Decimal('0.01')) == Decimal('3.00')


def test_calcular_puntos_ganados_con_canje(service):
    # Factor de pago aplicado
    service.db.fetch_one.side_effect = make_fetch_one_side_effect({
        30: (None, None, '10', None)
    })
    items = [{'id': 30, 'pvp': Decimal('10.00'), 'cantidad': 2}]  # bruto = 20
    pts = service.calcular_puntos_ganados(items, puntos_canjeados=Decimal('5'))
    # factor = (20-5)/20 = 0.75 -> base points = 2.00 * 0.75 = 1.50
    assert pts.quantize(Decimal('0.01')) == Decimal('1.50')


def test_calcular_puntos_ganados_devolucion_no_aplica_canje(service):
    # Devolucion items should not apply factor_pago
    service.db.fetch_one.side_effect = make_fetch_one_side_effect({
        40: (None, None, '10', None)
    })
    items = [
        {'id': 40, 'pvp': Decimal('10.00'), 'cantidad': 2, 'line_tipo': 'devolucion'}
    ]
    pts = service.calcular_puntos_ganados(items, puntos_canjeados=Decimal('5'))
    # bruto = 20, but devolucion ignores factor -> points = 2.00
    assert pts.quantize(Decimal('0.01')) == Decimal('2.00')


def test_calcular_puntos_ganados_manejo_valores_no_numericos(service):
    # Non-numeric pvp or cantidad should not raise and contribute 0
    service.db.fetch_one.side_effect = make_fetch_one_side_effect({
        50: (None, None, '10', None)
    })
    items = [
        {'id': 50, 'pvp': 'invalid', 'cantidad': 2},
        {'id': None, 'pvp': Decimal('5.00'), 'cantidad': 1},
    ]
    pts = service.calcular_puntos_ganados(items)
    assert isinstance(pts, Decimal)
    assert pts.quantize(Decimal('0.01')) == Decimal('0.00')


def test_obtener_porcentaje_producto_on_exception_uses_global(service):
    # Simular que obtener_fidelizacion_producto lanza excepción
    service.obtener_fidelizacion_producto = MagicMock(side_effect=Exception('DB error'))
    service.config_service.get_fide_porcentaje_global = MagicMock(return_value=Decimal('4.25'))
    pct = service.obtener_porcentaje_producto(123)
    assert pct.quantize(Decimal('0.01')) == Decimal('4.25')


def test_obtener_porcentaje_producto_on_exception_and_config_fails_returns_zero(service):
    service.obtener_fidelizacion_producto = MagicMock(side_effect=Exception('DB error'))
    service.config_service.get_fide_porcentaje_global = MagicMock(side_effect=Exception('config fail'))
    pct = service.obtener_porcentaje_producto(321)
    assert pct == Decimal('0')


def test_obtener_fidelizacion_producto_db_error_returns_zero_dict(service):
    service.db.fetch_one.side_effect = Exception('boom')
    cfg = service.obtener_fidelizacion_producto(77)
    assert cfg['tipo'] == 'porcentaje'
    assert cfg['valor'] == Decimal('0')


def test_calcular_puntos_ganados_empty_items_returns_zero(service):
    pts = service.calcular_puntos_ganados([])
    assert pts == Decimal('0')


def test_calcular_puntos_total_bruto_exception_handles_and_returns_zero(service):
    # pvp value that will cause Decimal conversion to fail
    service.db.fetch_one.side_effect = make_fetch_one_side_effect({
        60: (None, None, '10', None)
    })
    items = [{'id': 60, 'pvp': object(), 'cantidad': 1}]
    pts = service.calcular_puntos_ganados(items)
    assert pts.quantize(Decimal('0.01')) == Decimal('0.00')


def test_calcular_puntos_item_exception_logged_and_continues(service):
    # Make obtener_fidelizacion_producto return bad valor that breaks calculation
    service.obtener_fidelizacion_producto = MagicMock(return_value={'tipo': 'porcentaje', 'valor': 'not-a-number'})
    items = [{'id': 70, 'pvp': Decimal('10.00'), 'cantidad': 1}]
    pts = service.calcular_puntos_ganados(items)
    assert pts.quantize(Decimal('0.01')) == Decimal('0.00')
