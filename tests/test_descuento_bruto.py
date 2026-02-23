from decimal import Decimal
from kool_tpv.modulos.tpv.carrito.carrito_service import CarritoService
from kool_tpv.utils.formatter_service import FormatterService


def test_descuento_directo_bruto():
    cs = CarritoService()
    # Producto: llavero 3.90 (precio bruto), IVA 21%
    cs.add_item({'id': 1, 'nombre': 'Llavero', 'pvp': '3.90', 'tipo_iva': 21})

    resumen_before = cs.get_resumen_financiero()
    total_before = Decimal(resumen_before.get('total'))

    # Aplicar descuento directo de 1.00 € (bruto)
    descuento = {'tipo': 'directo', 'valor': Decimal('1.00'), 'euros': Decimal('1.00')}
    cs.aplicar_descuento(descuento)

    resumen_after = cs.get_resumen_financiero()
    total_after = Decimal(resumen_after.get('total'))

    # El total nuevo debe ser total_before - 1.00 (comparar quantized a 2 decimales)
    expected = (total_before - Decimal('1.00')).quantize(Decimal('0.01'))
    actual = Decimal(total_after).quantize(Decimal('0.01'))
    assert actual == expected, f"Esperado {expected} pero obtuve {actual}"

    # Además, el FormatterService debe mostrar 2.90 € para este caso concreto
    fmt = FormatterService()
    assert fmt.format_precio(actual) == '2.90 €'
