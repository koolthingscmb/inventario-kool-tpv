"""
Tests para BaseTicketGenerator._format_currency.

Contrato nuevo (sin heurística):
  - int          → céntimos  → se divide entre 100
  - Decimal      → euros     → se formatea directamente
  - float        → euros     → se convierte a Decimal y se formatea
  - str          → euros     → se convierte a Decimal y se formatea
"""
import pytest
from decimal import Decimal

from kool_tpv.modulos.impresion.base_ticket_generator import BaseTicketGenerator


class DummyGenerator(BaseTicketGenerator):
    def generate(self, config, **kwargs):
        return ""


# --- contrato int = céntimos ---

def test_format_currency_int_cents():
    g = DummyGenerator()
    assert g._format_currency(1184) == "11.84 €"


def test_format_currency_int_zero():
    g = DummyGenerator()
    assert g._format_currency(0) == "0.00 €"


def test_format_currency_int_large():
    """14400 céntimos = 144,00 € — el bug original que causaba 1.44 €."""
    g = DummyGenerator()
    assert g._format_currency(14400) == "144.00 €"


# --- contrato Decimal = euros (ya NO heurística) ---

def test_format_currency_decimal_euros():
    g = DummyGenerator()
    assert g._format_currency(Decimal('11.84')) == "11.84 €"


def test_format_currency_decimal_integral_is_euros():
    """Decimal('1184') ahora se interpreta como 1184 euros, NO como céntimos."""
    g = DummyGenerator()
    assert g._format_currency(Decimal('1184')) == "1184.00 €"


def test_format_currency_decimal_144():
    """Decimal('144.00') debe mostrar 144.00 €, no 1.44 € (bug original)."""
    g = DummyGenerator()
    assert g._format_currency(Decimal('144.00')) == "144.00 €"


# --- contrato float = euros ---

def test_format_currency_float_euros():
    g = DummyGenerator()
    assert g._format_currency(11.84) == "11.84 €"


def test_format_currency_float_integral_is_euros():
    """float 1184.0 ahora se interpreta como euros, NO como céntimos."""
    g = DummyGenerator()
    assert g._format_currency(1184.0) == "1184.00 €"


# --- contrato str = euros ---

def test_format_currency_str_euros():
    g = DummyGenerator()
    assert g._format_currency('11.84') == "11.84 €"
