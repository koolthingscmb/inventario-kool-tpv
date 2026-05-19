from decimal import Decimal, ROUND_HALF_UP
from typing import NewType, Union

# Aliases de tipo: contrato explícito entre capas
CentsInt = NewType('CentsInt', int)       # int almacenado en BD, representa céntimos
EurosDecimal = Decimal                    # Decimal en euros, usado en lógica de negocio


def from_cents(cents: int) -> Decimal:
    """Convierte céntimos a euros (Decimal)."""
    return Decimal(str(cents)) / Decimal('100')


def to_cents(euros: Decimal) -> int:
    """Convierte euros (Decimal) a céntimos (int) con redondeo financiero estándar."""
    return int(euros.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP) * 100)


def ensure_cents(val: Union[int, float, Decimal, str]) -> int:
    """Garantiza que el valor devuelto es un entero de céntimos.

    - int/bool  → se devuelve tal cual (ya son céntimos).
    - Decimal / float / str → se interpreta como euros y se convierte con to_cents().

    Raises:
        TypeError: si el tipo no es convertible.
        ValueError: si el valor no es numérico.
    """
    if isinstance(val, bool):
        raise TypeError(f"ensure_cents: bool no es un valor monetario válido ({val!r})")
    if isinstance(val, int):
        return val
    if isinstance(val, float):
        return to_cents(Decimal(str(val)))
    if isinstance(val, Decimal):
        return to_cents(val)
    if isinstance(val, str):
        try:
            return to_cents(Decimal(val.strip().replace(',', '.')))
        except Exception as exc:
            raise ValueError(f"ensure_cents: no se puede convertir '{val}' a céntimos") from exc
    raise TypeError(f"ensure_cents: tipo no soportado {type(val).__name__}")
