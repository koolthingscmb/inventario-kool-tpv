import pytest
from decimal import Decimal

from kool_tpv.utils.money import from_cents, to_cents, ensure_cents


# --- from_cents ---

def test_from_cents():
    assert from_cents(5000) == Decimal('50.00')


def test_from_cents_zero():
    assert from_cents(0) == Decimal('0.00')


def test_from_cents_one_cent():
    assert from_cents(1) == Decimal('0.01')


# --- to_cents ---

def test_to_cents_exact_and_rounding():
    assert to_cents(Decimal('50.00')) == 5000
    # 10.567 -> quantize to 2 decimals ROUND_HALF_UP => 10.57 -> 1057 cents
    assert to_cents(Decimal('10.567')) == 1057


def test_to_cents_rounding_down():
    # 10.564 -> ROUND_HALF_UP => 10.56 -> 1056 cents
    assert to_cents(Decimal('10.564')) == 1056


def test_to_cents_zero():
    assert to_cents(Decimal('0.00')) == 0


# --- ensure_cents ---

def test_ensure_cents_int_passthrough():
    assert ensure_cents(14400) == 14400


def test_ensure_cents_int_zero():
    assert ensure_cents(0) == 0


def test_ensure_cents_decimal_euros():
    assert ensure_cents(Decimal('144.00')) == 14400


def test_ensure_cents_decimal_small():
    assert ensure_cents(Decimal('1.44')) == 144


def test_ensure_cents_float_euros():
    assert ensure_cents(1.44) == 144


def test_ensure_cents_str_euros():
    assert ensure_cents('144.00') == 14400


def test_ensure_cents_str_comma_separator():
    assert ensure_cents('144,00') == 14400


def test_ensure_cents_bool_raises():
    with pytest.raises(TypeError):
        ensure_cents(True)


def test_ensure_cents_unsupported_type_raises():
    with pytest.raises(TypeError):
        ensure_cents([144])


def test_ensure_cents_invalid_str_raises():
    with pytest.raises(ValueError):
        ensure_cents('no-es-numero')
