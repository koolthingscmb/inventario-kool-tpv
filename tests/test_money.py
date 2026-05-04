from decimal import Decimal

from kool_tpv.utils.money import from_cents, to_cents


def test_from_cents():
    assert from_cents(5000) == Decimal('50.00')


def test_to_cents_exact_and_rounding():
    assert to_cents(Decimal('50.00')) == 5000
    # 10.567 -> quantize to 2 decimals ROUND_HALF_UP => 10.57 -> 1057 cents
    assert to_cents(Decimal('10.567')) == 1057
