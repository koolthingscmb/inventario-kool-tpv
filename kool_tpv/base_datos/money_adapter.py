"""Money adapter for DB boundary conversions.

This module re-uses the existing helpers in `kool_tpv.utils.money` and
exposes a small, explicit API intended to be used at the database boundary:

- `prepare_for_db(value)` -> int (cents)
- `read_from_db(value)` -> Decimal (euros)

Usage:
    from kool_tpv.base_datos.money_adapter import prepare_for_db, read_from_db

    # when inserting/updating DB (accepts Decimal/float/str in euros or int cents)
    cents = prepare_for_db(Decimal('12.34'))

    # when reading from DB
    euros = read_from_db(row['total'])

The adapter treats `int` inputs as already-cent amounts (no double-conversion).
"""
from decimal import Decimal
from typing import Optional, Union

from kool_tpv.utils.money import to_cents, from_cents

MoneyInput = Union[Decimal, float, int, str]


def prepare_for_db(amount: Optional[MoneyInput]) -> int:
    """Convert an amount to integer cents for DB storage.

    - If `amount` is ``int`` it is assumed to be already in cents and returned.
    - If ``None`` returns 0.
    - Otherwise convert from euros using `to_cents`.
    """
    if amount is None:
        return 0
    if isinstance(amount, int):
        return amount
    # Ensure Decimal-safe conversion for floats/strings
    return to_cents(Decimal(str(amount)))


def read_from_db(value: Optional[Union[int, str]]) -> Decimal:
    """Convert a DB value (céntimos) to Decimal euros.

    Accepts numeric-like DB values (int or numeric string). Returns a
    `Decimal` representing euros with two decimals.
    """
    if value is None:
        return Decimal('0.00')
    return from_cents(int(value))


def calcular_descuento_porcentaje(importe: MoneyInput, porcentaje: Union[int, float, Decimal]) -> int:
    """Calcula descuento en céntimos desde un importe base y porcentaje.

    Args:
        importe: Importe base (euros o céntimos)
        porcentaje: Porcentaje de descuento (ej: 30 para 30%)

    Returns:
        Descuento en céntimos (siempre int)

    Example:
        >>> calcular_descuento_porcentaje(Decimal('7.69'), 30)
        231  # 2.31€ de descuento en céntimos
    """
    # Convertir importe a Decimal euros si viene en céntimos
    if isinstance(importe, int):
        base_euros = read_from_db(importe)
    else:
        base_euros = Decimal(str(importe))

    porcentaje_dec = Decimal(str(porcentaje))
    descuento_euros = base_euros * (porcentaje_dec / Decimal('100'))

    return prepare_for_db(descuento_euros)


def calcular_importe_con_descuento(importe: MoneyInput, descuento: MoneyInput) -> int:
    """Calcula importe final restando descuento, resultado en céntimos.

    Args:
        importe: Importe base (euros o céntimos)
        descuento: Descuento a aplicar (euros o céntimos)

    Returns:
        Importe final en céntimos

    Example:
        >>> calcular_importe_con_descuento(Decimal('7.69'), Decimal('2.31'))
        538  # 5.38€ en céntimos
    """
    importe_cents = prepare_for_db(importe)
    descuento_cents = prepare_for_db(descuento)
    return max(0, importe_cents - descuento_cents)


__all__ = ["prepare_for_db", "read_from_db", "calcular_descuento_porcentaje", "calcular_importe_con_descuento"]
