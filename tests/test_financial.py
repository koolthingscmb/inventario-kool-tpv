"""
Tests unitarios para kool_tpv.modulos.tpv.carrito.financial.calculate_resumen.

Todos los precios de entrada (pvp) son en euros (Decimal).
Los resultados esperados también están en euros (Decimal).
"""
import pytest
from decimal import Decimal

from kool_tpv.modulos.tpv.carrito.financial import calculate_resumen


# --- helpers ---

def _item(pvp, cantidad=1, tipo_iva=21, line_tipo='venta'):
    return {'pvp': Decimal(str(pvp)), 'cantidad': cantidad, 'tipo_iva': tipo_iva, 'line_tipo': line_tipo}


def _dec(v):
    return Decimal(str(v))


# --- carrito vacío ---

def test_empty_cart_returns_zeros():
    r = calculate_resumen([])
    assert r['total'] == Decimal('0.00')
    assert r['subtotal'] == Decimal('0.00')
    assert r['total_iva'] == Decimal('0.00')


# --- venta simple sin IVA ---

def test_single_item_no_iva():
    items = [_item(pvp='10.00', tipo_iva=0)]
    r = calculate_resumen(items)
    assert r['total'] == _dec('10.00')
    assert r['subtotal'] == _dec('10.00')
    assert r['total_iva'] == _dec('0.00')


# --- venta simple con IVA 21% ---

def test_single_item_iva_21():
    # PVP 1.21 € con IVA 21% → base = 1.00 €, IVA = 0.21 €, total = 1.21 €
    items = [_item(pvp='1.21', tipo_iva=21)]
    r = calculate_resumen(items)
    assert r['total'] == _dec('1.21')
    assert r['subtotal'] == _dec('1.00')
    assert r['total_iva'] == _dec('0.21')


# --- cantidad > 1 ---

def test_multiple_quantity():
    # 3 uds x 1.21 € → total = 3.63 €
    items = [_item(pvp='1.21', cantidad=3, tipo_iva=21)]
    r = calculate_resumen(items)
    assert r['total'] == _dec('3.63')


# --- devolución ---

def test_devolucion_item_negativo():
    items = [_item(pvp='1.21', tipo_iva=21, line_tipo='devolucion')]
    r = calculate_resumen(items)
    assert r['total'] == _dec('-1.21')
    assert r['subtotal'] == _dec('-1.00')


# --- puntos canjeados ---

def test_puntos_canjeados_descuenta_total():
    items = [_item(pvp='10.00', tipo_iva=0)]
    r = calculate_resumen(items, puntos_canjeados=_dec('2.00'))
    assert r['total'] == _dec('8.00')
    assert r['puntos_canjeados'] == _dec('2.00')


def test_puntos_canjeados_no_negative_total():
    items = [_item(pvp='1.00', tipo_iva=0)]
    r = calculate_resumen(items, puntos_canjeados=_dec('5.00'))
    assert r['total'] == _dec('0.00')


# --- descuento porcentaje ---

def test_descuento_porcentaje():
    # PVP 12.10 € (IVA 21% incluido) con 10% descuento → total ≈ 10.89 €
    items = [_item(pvp='12.10', tipo_iva=21)]
    r = calculate_resumen(items, descuento={'tipo': 'porcentaje', 'valor': Decimal('10')})
    # total = 12.10 - (12.10 * 10%) = 12.10 - 1.21 = 10.89
    assert r['total'] == _dec('10.89')
    assert r['total'] < _dec('12.10')


# --- descuento directo ---

def test_descuento_directo():
    # PVP 12.10 € con descuento directo de 2.10 € → total = 10.00 €
    items = [_item(pvp='12.10', tipo_iva=21)]
    r = calculate_resumen(items, descuento={'tipo': 'directo', 'euros': _dec('2.10'), 'valor': _dec('2.10')})
    assert r['total'] == _dec('10.00')


# --- mezcla IVA 4% y 21% ---

def test_mixed_iva_rates():
    items = [
        _item(pvp='1.04', tipo_iva=4),
        _item(pvp='1.21', tipo_iva=21),
    ]
    r = calculate_resumen(items)
    assert r['total'] == _dec('2.25')
    assert 4 in r['iva_desglose']
    assert 21 in r['iva_desglose']
