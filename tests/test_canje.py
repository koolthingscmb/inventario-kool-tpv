from decimal import Decimal
from kool_tpv.modulos.tpv.carrito.carrito_service import CarritoService


def test_aplicar_canje_updates_resumen():
    cs = CarritoService()
    # add an item with pvp 10.00
    cs.add_item({'id': 'p1', 'nombre': 'Test', 'pvp': '10.00', 'tipo_iva': 21})
    resumen_before = cs.get_resumen_financiero()
    total_before = Decimal(str(resumen_before.get('total', 0)))

    # apply canje 2.00
    cs.aplicar_canje_puntos(Decimal('2.00'))
    resumen_after = cs.get_resumen_financiero()
    puntos = resumen_after.get('puntos_canjeados')
    total_after = Decimal(str(resumen_after.get('total', 0)))

    assert isinstance(puntos, Decimal)
    assert puntos == Decimal('2.00')
    assert total_after == max(Decimal('0.00'), total_before - puntos)


def test_set_get_puntos_canjeados_various_types():
    cs = CarritoService()
    cs.set_puntos_canjeados('3.5')
    assert cs.get_puntos_canjeados() == Decimal('3.5')

    cs.set_puntos_canjeados(1)
    assert cs.get_puntos_canjeados() == Decimal('1')

    cs.set_puntos_canjeados(None)
    assert cs.get_puntos_canjeados() == Decimal('0.00')
