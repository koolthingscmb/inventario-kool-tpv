from decimal import Decimal

from kool_tpv.modulos.impresion.base_ticket_generator import BaseTicketGenerator


class DummyGenerator(BaseTicketGenerator):
    def generate(self, config, **kwargs):
        return ""


def test_format_currency_int_cents():
    g = DummyGenerator()
    assert g._format_currency(1184) == "11.84 €"


def test_format_currency_float_integral_cents():
    g = DummyGenerator()
    assert g._format_currency(1184.0) == "11.84 €"


def test_format_currency_decimal_integral_cents():
    g = DummyGenerator()
    assert g._format_currency(Decimal('1184')) == "11.84 €"


def test_format_currency_decimal_euros():
    g = DummyGenerator()
    assert g._format_currency(Decimal('11.84')) == "11.84 €"


if __name__ == '__main__':
    g = DummyGenerator()
    cases = [
        (g._format_currency(1184), "11.84 €"),
        (g._format_currency(1184.0), "11.84 €"),
        (g._format_currency(Decimal('1184')), "11.84 €"),
        (g._format_currency(Decimal('11.84')), "11.84 €"),
    ]
    for got, expected in cases:
        if got != expected:
            print(f"FAIL: got={got!r} expected={expected!r}")
            raise SystemExit(1)
    print("OK")
