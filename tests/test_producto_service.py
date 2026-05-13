import pytest
from decimal import Decimal

from kool_tpv.base_datos.producto_service import _safe_decimal_from_db


# ── Tests de _safe_decimal_from_db ────────────────────────────────────────────

def test_safe_decimal_from_db_none():
    """None → Decimal('0.00')"""
    assert _safe_decimal_from_db(None) == Decimal('0.00')


def test_safe_decimal_from_db_cero():
    """0 → Decimal('0.00')"""
    assert _safe_decimal_from_db(0) == Decimal('0.00')


def test_safe_decimal_from_db_centimos():
    """1899 céntimos → Decimal('18.99')"""
    assert _safe_decimal_from_db(1899) == Decimal('18.99')


def test_safe_decimal_from_db_valor_grande():
    """10000 céntimos → Decimal('100.00')"""
    assert _safe_decimal_from_db(10000) == Decimal('100.00')


def test_safe_decimal_from_db_string_invalido():
    """Cadena no numérica → Decimal('0.00') sin excepción."""
    resultado = _safe_decimal_from_db('no-es-numero')
    assert isinstance(resultado, Decimal)
    assert resultado == Decimal('0.00')


# ── Tests de buscar_productos_paginados ───────────────────────────────────────

def test_buscar_productos_paginados_estructura_salida(producto_service, db_test):
    """buscar_productos_paginados devuelve pvp como Decimal y 10 claves."""
    db_test.execute_query(
        "INSERT INTO productos (id, nombre, sku, stock_actual, activo) VALUES (?, ?, ?, ?, ?)",
        (1, 'Producto Test', 'SKU-TEST', 5, 1)
    )
    db_test.execute_query(
        "INSERT INTO precios (producto_id, pvp, activo) VALUES (?, ?, ?)",
        (1, 2500, 1)  # 25.00€
    )

    resultado = producto_service.buscar_productos_paginados(limit=50, offset=0)

    assert len(resultado) == 1
    item = resultado[0]
    # pvp debe estar normalizado a Decimal por el Service
    assert isinstance(item['pvp'], Decimal)
    assert item['pvp'] == Decimal('25.00')
    # Verificar las 10 claves
    esperadas = {'id', 'sku', 'nombre', 'categoria', 'tipo', 'ean', 'pvp', 'stock_actual', 'ventas', 'estado'}
    assert set(item.keys()) == esperadas


def test_buscar_productos_paginados_filtro_termino(producto_service, db_test):
    """buscar_productos_paginados filtra por término de búsqueda."""
    db_test.execute_query(
        "INSERT INTO productos (id, nombre, sku, activo) VALUES (?, ?, ?, ?)",
        (1, 'Zapatilla Nike', 'ZN', 1)
    )
    db_test.execute_query(
        "INSERT INTO productos (id, nombre, sku, activo) VALUES (?, ?, ?, ?)",
        (2, 'Camiseta Adidas', 'CA', 1)
    )

    resultado = producto_service.buscar_productos_paginados(termino_busqueda='Nike', limit=50, offset=0)

    assert len(resultado) == 1
    assert resultado[0]['nombre'] == 'Zapatilla Nike'


def test_buscar_productos_paginados_sin_resultados(producto_service):
    """buscar_productos_paginados devuelve lista vacía si no hay coincidencias."""
    resultado = producto_service.buscar_productos_paginados(termino_busqueda='NOEXISTE', limit=50, offset=0)
    assert resultado == []


def test_buscar_productos_paginados_pvp_none_es_decimal_cero(producto_service, db_test):
    """Producto sin precio en tabla precios → pvp = Decimal('0.00')."""
    db_test.execute_query(
        "INSERT INTO productos (id, nombre, sku, activo) VALUES (?, ?, ?, ?)",
        (1, 'Sin Precio', 'SINPVP', 1)
    )
    # No insertamos precio

    resultado = producto_service.buscar_productos_paginados(limit=50, offset=0)

    assert len(resultado) == 1
    assert resultado[0]['pvp'] == Decimal('0.00')


# ── Tests de get_producto_para_carrito ────────────────────────────────────────

def test_get_producto_para_carrito_normaliza_pvp(producto_service, db_test):
    """get_producto_para_carrito devuelve pvp como Decimal y calcula total_linea."""
    db_test.execute_query(
        "INSERT INTO productos (id, nombre, sku, tipo_iva, activo) VALUES (?, ?, ?, ?, ?)",
        (1, 'Producto', 'SKU-001', 21, 1)
    )
    db_test.execute_query(
        "INSERT INTO precios (producto_id, pvp, activo) VALUES (?, ?, ?)",
        (1, 2500, 1)  # 25.00€
    )

    resultado = producto_service.get_producto_para_carrito(1, cantidad=2)

    assert resultado is not None
    assert isinstance(resultado['pvp'], Decimal)
    assert resultado['pvp'] == Decimal('25.00')
    assert resultado['cantidad'] == 2
    assert resultado['sku'] == 'SKU-001'
    assert isinstance(resultado['total_linea'], Decimal)
    assert resultado['total_linea'] == Decimal('50.00')  # 25.00 * 2


def test_get_producto_para_carrito_cantidad_por_defecto(producto_service, db_test):
    """get_producto_para_carrito con cantidad=1 por defecto."""
    db_test.execute_query(
        "INSERT INTO productos (id, nombre, sku, tipo_iva, activo) VALUES (?, ?, ?, ?, ?)",
        (1, 'Producto', 'SKU-002', 10, 1)
    )
    db_test.execute_query(
        "INSERT INTO precios (producto_id, pvp, activo) VALUES (?, ?, ?)",
        (1, 1000, 1)  # 10.00€
    )

    resultado = producto_service.get_producto_para_carrito(1)

    assert resultado['cantidad'] == 1
    assert resultado['total_linea'] == Decimal('10.00')


def test_get_producto_para_carrito_id_inexistente(producto_service):
    """get_producto_para_carrito con ID inexistente devuelve estructura mínima válida."""
    resultado = producto_service.get_producto_para_carrito(9999, cantidad=1)

    # No debe lanzar excepción; pvp debe ser Decimal
    assert isinstance(resultado['pvp'], Decimal)
    assert isinstance(resultado['total_linea'], Decimal)


# ── Tests de listar_productos ─────────────────────────────────────────────────

def test_listar_productos_normaliza_pvp(producto_service, db_test):
    """listar_productos devuelve pvp como Decimal (normalizado desde céntimos)."""
    db_test.execute_query(
        "INSERT INTO productos (id, nombre, sku, stock_actual, tipo_iva) VALUES (?, ?, ?, ?, ?)",
        (1, 'Producto', 'P1', 3, 21)
    )
    db_test.execute_query(
        "INSERT INTO precios (producto_id, pvp, activo) VALUES (?, ?, ?)",
        (1, 999, 1)  # 9.99€
    )

    resultado = producto_service.listar_productos()

    assert len(resultado) == 1
    assert isinstance(resultado[0]['pvp'], Decimal)
    assert resultado[0]['pvp'] == Decimal('9.99')
