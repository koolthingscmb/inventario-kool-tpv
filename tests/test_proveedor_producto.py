from modulos.almacen.producto_service import ProductoService
from database import connect, crear_base_de_datos, crear_tablas_tickets, ensure_product_schema


def setup_module(module):
    crear_base_de_datos()
    crear_tablas_tickets()
    ensure_product_schema()
    # ensure proveedores table exists
    conn = connect()
    cur = conn.cursor()
    try:
        cur.execute('''CREATE TABLE IF NOT EXISTS proveedores (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT)''')
        conn.commit()
    finally:
        conn.close()


def test_crear_producto_con_proveedor_por_nombre():
    svc = ProductoService()
    conn = connect()
    cur = conn.cursor()
    try:
        # crear proveedor
        cur.execute("INSERT INTO proveedores (nombre) VALUES (?)", ("ProveedorA",))
        pid = cur.lastrowid
        conn.commit()

        datos = {'nombre': 'Prod X', 'sku': 'PX001', 'proveedor': 'ProveedorA', 'pvp': 9.9}
        prod_id = svc.guardar_producto(datos, [], [])
        assert prod_id is not None

        # verificar que proveedor_id fue asignado
        cur.execute('SELECT proveedor_id, proveedor FROM productos WHERE id=?', (prod_id,))
        r = cur.fetchone()
        assert r is not None
        assert r[0] == pid
        assert r[1] == 'ProveedorA'
    finally:
        conn.close()


def test_crear_producto_con_proveedor_por_id():
    svc = ProductoService()
    conn = connect()
    cur = conn.cursor()
    try:
        # crear proveedor
        cur.execute("INSERT INTO proveedores (nombre) VALUES (?)", ("ProveedorB",))
        pid = cur.lastrowid
        conn.commit()

        datos = {'nombre': 'Prod Y', 'sku': 'PY001', 'proveedor': str(pid), 'pvp': 5.5}
        prod_id = svc.guardar_producto(datos, [], [])
        assert prod_id is not None

        cur.execute('SELECT proveedor_id, proveedor FROM productos WHERE id=?', (prod_id,))
        r = cur.fetchone()
        assert r is not None
        assert r[0] == pid
        assert r[1] == 'ProveedorB'
    finally:
        conn.close()
