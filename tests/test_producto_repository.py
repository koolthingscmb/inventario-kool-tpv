import pytest
from decimal import Decimal


def test_get_by_id_producto_existe(producto_repo, db_test):
    """get_by_id devuelve el producto cuando existe."""
    db_test.execute_query(
        "INSERT INTO productos (id, nombre, sku) VALUES (?, ?, ?)",
        (1, 'Test Product', 'TEST-SKU-001')
    )

    resultado = producto_repo.get_by_id(1)

    assert resultado is not None
    assert resultado['nombre'] == 'Test Product'
    assert resultado['sku'] == 'TEST-SKU-001'


def test_get_by_id_producto_no_existe(producto_repo):
    """get_by_id devuelve None si el producto no existe."""
    resultado = producto_repo.get_by_id(999)
    assert resultado is None


def test_get_by_sku(producto_repo, db_test):
    """get_by_sku devuelve el producto correcto."""
    db_test.execute_query(
        "INSERT INTO productos (id, nombre, sku) VALUES (?, ?, ?)",
        (1, 'Test Product', 'SKU-123')
    )

    resultado = producto_repo.get_by_sku('SKU-123')

    assert resultado is not None
    assert resultado['id'] == 1


def test_get_by_sku_no_existe(producto_repo):
    """get_by_sku devuelve None si el SKU no existe."""
    resultado = producto_repo.get_by_sku('NO-EXISTE')
    assert resultado is None


def test_listar_con_resumen_devuelve_estructura(producto_repo, db_test):
    """listar_con_resumen devuelve dict con las claves esperadas y pvp raw."""
    db_test.execute_query(
        "INSERT INTO productos (id, nombre, sku, stock_actual, tipo_iva) VALUES (?, ?, ?, ?, ?)",
        (1, 'Producto A', 'PROD-A', 10, 21)
    )
    db_test.execute_query(
        "INSERT INTO precios (producto_id, pvp, activo) VALUES (?, ?, ?)",
        (1, 1999, 1)  # 19.99€ en céntimos
    )

    resultado = producto_repo.listar_con_resumen('')

    assert len(resultado) == 1
    item = resultado[0]
    assert item['nombre'] == 'Producto A'
    assert item['pvp'] == 1999   # RAW sin normalizar
    assert item['stock_actual'] == 10
    assert 'categoria' in item
    assert 'tipo' in item
    assert 'ventas' in item


def test_listar_con_resumen_filtra_por_termino(producto_repo, db_test):
    """listar_con_resumen filtra por nombre correctamente."""
    db_test.execute_query(
        "INSERT INTO productos (id, nombre, sku) VALUES (?, ?, ?)",
        (1, 'Zapatilla Nike', 'ZAPN')
    )
    db_test.execute_query(
        "INSERT INTO productos (id, nombre, sku) VALUES (?, ?, ?)",
        (2, 'Camiseta Adidas', 'CAMA')
    )

    resultado = producto_repo.listar_con_resumen('Nike')

    assert len(resultado) == 1
    assert resultado[0]['nombre'] == 'Zapatilla Nike'


def test_buscar_sin_filtros_devuelve_todos(producto_repo, db_test):
    """buscar sin filtros devuelve todos los productos."""
    db_test.execute_query(
        "INSERT INTO productos (id, nombre, sku, stock_actual, activo) VALUES (?, ?, ?, ?, ?)",
        (1, 'Alpha', 'A', 5, 1)
    )
    db_test.execute_query(
        "INSERT INTO productos (id, nombre, sku, stock_actual, activo) VALUES (?, ?, ?, ?, ?)",
        (2, 'Beta', 'B', 0, 1)
    )

    resultado = producto_repo.buscar(limit=50, offset=0)

    assert len(resultado) == 2


def test_buscar_filtra_por_estado_activo(producto_repo, db_test):
    """buscar con estado 'activo' solo devuelve productos con stock > 0."""
    db_test.execute_query(
        "INSERT INTO productos (id, nombre, sku, stock_actual, activo) VALUES (?, ?, ?, ?, ?)",
        (1, 'Product Alpha', 'ALPHA', 10, 1)
    )
    db_test.execute_query(
        "INSERT INTO productos (id, nombre, sku, stock_actual, activo) VALUES (?, ?, ?, ?, ?)",
        (2, 'Product Beta', 'BETA', 0, 1)
    )

    resultado = producto_repo.buscar(estados=['activo'], limit=50, offset=0)

    assert len(resultado) == 1
    assert resultado[0]['nombre'] == 'Product Alpha'
    assert resultado[0]['estado'] == 'Activo'


def test_buscar_filtra_por_estado_sin_stock(producto_repo, db_test):
    """buscar con estado 'sin_stock' solo devuelve activos sin stock."""
    db_test.execute_query(
        "INSERT INTO productos (id, nombre, sku, stock_actual, activo) VALUES (?, ?, ?, ?, ?)",
        (1, 'Con Stock', 'CS', 5, 1)
    )
    db_test.execute_query(
        "INSERT INTO productos (id, nombre, sku, stock_actual, activo) VALUES (?, ?, ?, ?, ?)",
        (2, 'Sin Stock', 'SS', 0, 1)
    )

    resultado = producto_repo.buscar(estados=['sin_stock'], limit=50, offset=0)

    assert len(resultado) == 1
    assert resultado[0]['nombre'] == 'Sin Stock'
    assert resultado[0]['estado'] == 'Sin Stock'


def test_buscar_filtra_por_estado_archivado(producto_repo, db_test):
    """buscar con estado 'archivado' solo devuelve productos inactivos."""
    db_test.execute_query(
        "INSERT INTO productos (id, nombre, sku, stock_actual, activo) VALUES (?, ?, ?, ?, ?)",
        (1, 'Activo', 'ACT', 5, 1)
    )
    db_test.execute_query(
        "INSERT INTO productos (id, nombre, sku, stock_actual, activo) VALUES (?, ?, ?, ?, ?)",
        (2, 'Archivado', 'ARCH', 0, 0)
    )

    resultado = producto_repo.buscar(estados=['archivado'], limit=50, offset=0)

    assert len(resultado) == 1
    assert resultado[0]['nombre'] == 'Archivado'
    assert resultado[0]['estado'] == 'Archivado'


def test_buscar_filtra_por_termino(producto_repo, db_test):
    """buscar filtra por nombre/sku."""
    db_test.execute_query(
        "INSERT INTO productos (id, nombre, sku, activo) VALUES (?, ?, ?, ?)",
        (1, 'Zapatilla', 'ZAP', 1)
    )
    db_test.execute_query(
        "INSERT INTO productos (id, nombre, sku, activo) VALUES (?, ?, ?, ?)",
        (2, 'Camiseta', 'CAM', 1)
    )

    resultado = producto_repo.buscar(termino='Zapat', limit=50, offset=0)

    assert len(resultado) == 1
    assert resultado[0]['sku'] == 'ZAP'


def test_buscar_paginacion(producto_repo, db_test):
    """buscar respeta limit y offset."""
    for i in range(5):
        db_test.execute_query(
            "INSERT INTO productos (id, nombre, sku, activo) VALUES (?, ?, ?, ?)",
            (i + 1, f'Producto {i + 1:02d}', f'P{i + 1}', 1)
        )

    pagina1 = producto_repo.buscar(limit=3, offset=0)
    pagina2 = producto_repo.buscar(limit=3, offset=3)

    assert len(pagina1) == 3
    assert len(pagina2) == 2


def test_buscar_estructura_salida_10_claves(producto_repo, db_test):
    """buscar devuelve exactamente las 10 claves requeridas por busqueda_ui."""
    db_test.execute_query(
        "INSERT INTO productos (id, nombre, sku, stock_actual, activo) VALUES (?, ?, ?, ?, ?)",
        (1, 'Producto Test', 'TEST', 5, 1)
    )

    resultado = producto_repo.buscar(limit=1, offset=0)

    assert len(resultado) == 1
    claves = set(resultado[0].keys())
    esperadas = {'id', 'sku', 'nombre', 'categoria', 'tipo', 'ean', 'pvp', 'stock_actual', 'ventas', 'estado'}
    assert claves == esperadas


def test_get_ventas_por_producto_id(producto_repo, db_test):
    """get_ventas_por_producto_id devuelve el historial correcto."""
    db_test.execute_query(
        "INSERT INTO productos (id, sku, nombre) VALUES (?, ?, ?)",
        (1, 'SKU-001', 'Test')
    )
    db_test.execute_query(
        "INSERT INTO tickets (id, created_at, cliente_id) VALUES (?, ?, ?)",
        (100, '2026-05-10', None)
    )
    db_test.execute_query(
        "INSERT INTO ticket_lines (ticket_id, sku, cantidad) VALUES (?, ?, ?)",
        (100, 'SKU-001', 5)
    )

    resultado = producto_repo.get_ventas_por_producto_id(1, limite=20)

    assert len(resultado) == 1
    assert resultado[0]['cantidad'] == 5
    assert resultado[0]['ticket_id'] == 100
