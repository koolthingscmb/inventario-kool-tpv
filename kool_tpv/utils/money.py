from decimal import Decimal, ROUND_HALF_UP

def from_cents(cents: int) -> Decimal:
    """Convierte céntimos a euros (Decimal)."""
    return Decimal(str(cents)) / Decimal('100')

def to_cents(euros: Decimal) -> int:
    """Convierte euros (Decimal) a céntimos (int) con redondeo financiero estándar."""
    return int(euros.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP) * 100)
