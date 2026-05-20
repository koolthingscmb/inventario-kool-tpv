from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Optional


def _quantize(v: Decimal) -> Decimal:
    return v.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def calculate_resumen(items: List[Dict], puntos_canjeados: Decimal = Decimal('0.00'), descuento: Optional[Dict] = None) -> Dict:
    """Calcular resumen financiero usando redondeo por línea.

    items: lista de dict con keys `pvp` (Decimal/number), `cantidad` (int), `tipo_iva` (int), `line_tipo` ('venta'|'devolucion'|'tesoro')
    Devuelve dict con las mismas claves que `CarritoService.get_resumen_financiero()` esperaba.
    """
    total_bruto_pvp = Decimal('0.00')
    subtotal = Decimal('0.00')
    iva_desglose: Dict[int, Decimal] = {}
    gross_pvp_by_type: Dict[int, Decimal] = {}

    # Calcular base e IVA por línea con quantize por unidad
    for item in (items or []):
        try:
            pvp_dec = Decimal(str(item.get('pvp', 0)))
        except Exception:
            pvp_dec = Decimal('0.00')
        try:
            cantidad = int(item.get('cantidad', 0))
        except Exception:
            cantidad = 0
        try:
            tipo = int(item.get('tipo_iva', 21))
        except Exception:
            tipo = 21

        iva_rate = Decimal(tipo) / Decimal('100') if tipo != 0 else Decimal('0')
        sign = Decimal('-1') if str(item.get('line_tipo', 'venta')) == 'devolucion' else Decimal('1')
        line_bruto = _quantize(pvp_dec * Decimal(cantidad) * sign)
        total_bruto_pvp += line_bruto
        gross_pvp_by_type[tipo] = gross_pvp_by_type.get(tipo, Decimal('0.00')) + line_bruto

        # Base unitaria sin IVA, cuantizar por unidad
        try:
            base_unit = _quantize(pvp_dec / (Decimal('1') + iva_rate)) if iva_rate != Decimal('0') else _quantize(pvp_dec)
        except Exception:
            base_unit = Decimal('0.00')

        base_line = base_unit * Decimal(cantidad) * sign
        # IVA por línea: diferencia entre bruto y base
        iva_unit = pvp_dec - base_unit
        iva_line = _quantize(iva_unit * Decimal(cantidad) * sign)

        # Accumulate
        subtotal += _quantize(base_line)
        iva_desglose[tipo] = iva_desglose.get(tipo, Decimal('0.00')) + iva_line

    # Garantizar claves comunes
    iva_desglose.setdefault(4, Decimal('0.00'))
    iva_desglose.setdefault(21, Decimal('0.00'))

    total_iva = sum(iva_desglose.values(), Decimal('0.00'))
    total = _quantize(total_bruto_pvp)
    subtotal = _quantize(total - total_iva)

    puntos = Decimal('0.00')
    try:
        puntos = Decimal(str(puntos_canjeados or 0))
    except Exception:
        puntos = Decimal('0.00')

    # Si hay descuento y/o puntos canjeados, calcular descuento bruto y repartir proporcionalmente
    descuento_euros = Decimal('0.00')
    descuento_tipo = None
    descuento_valor = None
    if descuento:
        descuento_tipo = descuento.get('tipo')
        if descuento_tipo == 'porcentaje':
            try:
                valor_pct = Decimal(str(descuento.get('valor', '0')))
            except Exception:
                valor_pct = Decimal('0.00')
            descuento_euros = _quantize((subtotal + total_iva) * valor_pct / Decimal('100'))
        else:
            try:
                descuento_euros = Decimal(str(descuento.get('euros', '0')))
            except Exception:
                descuento_euros = Decimal('0.00')
        descuento_valor = descuento.get('valor')

    total_descuento_bruto = descuento_euros + puntos

    if total_descuento_bruto > Decimal('0.00'):
        gross_by_type = {tipo: gross_pvp_by_type.get(tipo, Decimal('0.00')) for tipo in iva_desglose}

        total_gross_abs = sum((abs(v) for v in gross_by_type.values()), Decimal('0.00'))
        if total_gross_abs == Decimal('0.00'):
            subtotal_con_descuento = Decimal('0.00')
            iva_desglose_nuevo = {k: Decimal('0.00') for k in gross_by_type.keys()}
            total_iva_nuevo = Decimal('0.00')
        else:
            iva_desglose_nuevo = {}
            total_iva_nuevo = Decimal('0.00')
            if len(gross_by_type) == 1:
                tipo, gross_orig = next(iter(gross_by_type.items()))
                tipo_pct = Decimal(tipo)
                sign = Decimal('1') if gross_orig >= Decimal('0') else Decimal('-1')
                nueva_gross = gross_orig - (sign * total_descuento_bruto)
                try:
                    nueva_base = nueva_gross / (Decimal('1') + (tipo_pct / Decimal('100')))
                    nueva_cuota = nueva_gross - nueva_base
                except Exception:
                    nueva_base = Decimal('0.00')
                    nueva_cuota = Decimal('0.00')
                iva_desglose_nuevo[tipo] = _quantize(nueva_cuota)
                total_iva_nuevo = iva_desglose_nuevo[tipo]
                subtotal_con_descuento = _quantize(nueva_base)
            else:
                new_base_by_type = {}
                for tipo, gross_orig in gross_by_type.items():
                    try:
                        proporcion = (abs(gross_orig) / total_gross_abs)
                        descuento_para_tipo = (total_descuento_bruto * proporcion)
                        sign = Decimal('1') if gross_orig >= Decimal('0') else Decimal('-1')
                        nueva_gross = gross_orig - (sign * descuento_para_tipo)
                        tipo_pct = Decimal(tipo)
                        nueva_base = nueva_gross / (Decimal('1') + (tipo_pct / Decimal('100')))
                        nueva_cuota = nueva_gross - nueva_base
                    except Exception:
                        nueva_base = Decimal('0.00')
                        nueva_cuota = Decimal('0.00')
                    new_base_by_type[tipo] = _quantize(nueva_base)
                    iva_desglose_nuevo[tipo] = _quantize(nueva_cuota)
                    total_iva_nuevo += iva_desglose_nuevo[tipo]

                subtotal_con_descuento = sum(new_base_by_type.values(), Decimal('0.00'))

        subtotal = subtotal_con_descuento
        iva_desglose = iva_desglose_nuevo
        total_iva = total_iva_nuevo
        total = subtotal + total_iva

    descuento_aplicado = (((subtotal + total_iva) - total) if (subtotal + total_iva) - total > Decimal('0.00') else Decimal('0.00'))

    return {
        'subtotal': subtotal,
        'iva_desglose': iva_desglose,
        'total_iva': total_iva,
        'total': total,
        'puntos_canjeados': puntos,
        'descuento_euros': descuento_aplicado,
        'descuento_tipo': descuento_tipo,
        'descuento_valor': descuento_valor,
        'total_bruto_original': (subtotal + total_iva),
    }
