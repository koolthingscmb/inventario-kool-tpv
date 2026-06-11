"""Fórmulas de cálculo de campos derivados para importación de albaranes CSV.

Funciones puras que calculan COSTE y PVPR a partir de los datos del proveedor.
Se aplican en el validador según las flags del mapeo JSON del proveedor.

Flags del mapeo que activan cada fórmula:
    - "calcular_coste_desde_precio_dto": true
        → COSTE = precio_base × (1 - dto_porcentaje / 100)
    - "calcular_pvpr_desde_precio_iva": true
        → PVPR = precio_base × (1 + tipo_iva / 100)
"""
from decimal import Decimal, ROUND_HALF_UP
import logging

logger = logging.getLogger(__name__)


def calcular_coste_neto(precio_base: Decimal, dto_porcentaje: Decimal) -> Decimal:
    """Calcula el coste neto aplicando el descuento del proveedor.

    Args:
        precio_base: Precio sin descuento (euros), ej: Decimal('12.50')
        dto_porcentaje: Porcentaje de descuento, ej: Decimal('30') para 30%

    Returns:
        Coste neto en euros con 2 decimales, ej: Decimal('8.75')

    Example:
        >>> calcular_coste_neto(Decimal('12.50'), Decimal('30'))
        Decimal('8.75')
    """
    try:
        precio = Decimal(str(precio_base))
        dto = Decimal(str(dto_porcentaje))
        factor = Decimal('1') - (dto / Decimal('100'))
        coste = (precio * factor).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return coste
    except Exception:
        logger.exception(f'Error calculando coste neto: precio={precio_base}, dto={dto_porcentaje}')
        return Decimal('0.00')


def calcular_pvpr(precio_base: Decimal, tipo_iva: int) -> Decimal:
    """Calcula el PVP recomendado añadiendo el IVA al precio base.

    Args:
        precio_base: Precio sin IVA (euros), ej: Decimal('12.50')
        tipo_iva: Porcentaje de IVA, ej: 4, 10 o 21

    Returns:
        PVPR en euros con 2 decimales, ej: Decimal('15.13') para IVA 21%

    Example:
        >>> calcular_pvpr(Decimal('12.50'), 21)
        Decimal('15.13')
    """
    try:
        precio = Decimal(str(precio_base))
        iva = Decimal(str(tipo_iva))
        factor = Decimal('1') + (iva / Decimal('100'))
        pvpr = (precio * factor).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return pvpr
    except Exception:
        logger.exception(f'Error calculando PVPR: precio={precio_base}, iva={tipo_iva}')
        return Decimal('0.00')


def aplicar_formulas(fila: dict, mapeo: dict) -> dict:
    """Aplica las fórmulas de cálculo a una fila según las flags del mapeo.

    Modifica 'coste' y/o 'pvpr' en la fila si las flags correspondientes
    están activas en el mapeo del proveedor.

    Args:
        fila: Diccionario de datos de una línea CSV (output del parser)
        mapeo: Configuración JSON del proveedor

    Returns:
        Fila con 'coste' y/o 'pvpr' calculados si aplica
    """
    if not mapeo:
        return fila

    precio_base = Decimal(str(fila.get('precio_base', 0.0) or 0.0))
    dto = Decimal(str(fila.get('descuento', 0.0) or 0.0))
    tipo_iva = int(fila.get('tipo_iva', 21) or 21)

    if mapeo.get('calcular_coste_desde_precio_dto'):
        fila['coste'] = float(calcular_coste_neto(precio_base, dto))
        logger.debug(f'Coste calculado: {precio_base} × (1 - {dto}/100) = {fila["coste"]}')

    if mapeo.get('calcular_pvpr_desde_precio_iva'):
        fila['pvpr'] = float(calcular_pvpr(precio_base, tipo_iva))
        logger.debug(f'PVPR calculado: {precio_base} × (1 + {tipo_iva}/100) = {fila["pvpr"]}')

    return fila
