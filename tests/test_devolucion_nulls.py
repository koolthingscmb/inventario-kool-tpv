import pytest
from decimal import Decimal
from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.tpv.devoluciones_service import DevolucionesService


class MockCarrito:
    def __init__(self, items, cliente=None):
        self._items = items
        self._devolucion_active = True
        self._cliente = cliente

    def get_items(self):
        return self._items

    def get_resumen_financiero(self):
        total = sum([Decimal(str(it.get('pvp', 0))) * int(it.get('cantidad', 1)) for it in self._items])
        return {'subtotal': float(total), 'total': float(total)}

    def get_cliente(self):
        return self._cliente


def setup_minimal_schema(db: Database):
    cur = db.connection.cursor()
    cur.executescript("""
    CREATE TABLE configuracion (clave TEXT PRIMARY KEY, valor TEXT);

    CREATE TABLE productos (
        id INTEGER PRIMARY KEY,
        nombre TEXT,
        stock_actual INTEGER DEFAULT 0,
        ventas_totales INTEGER DEFAULT 0
    );

    CREATE TABLE clientes (
        id INTEGER PRIMARY KEY,
        nombre TEXT,
        total_devoluciones INTEGER DEFAULT 0,
        tesoro_total INTEGER DEFAULT 0,
        tesoro_historico INTEGER DEFAULT 0
    );

    CREATE TABLE tickets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT,
        cajero TEXT,
        cliente TEXT,
        cliente_id INTEGER,
        num_ticket TEXT,
        subtotal INTEGER,
        forma_pago TEXT,
        total INTEGER,
        pagado INTEGER,
        cambio INTEGER,
        importe_efectivo INTEGER,
        importe_tarjeta INTEGER,
        descuento_euros INTEGER,
        descuento_tipo TEXT,
        descuento_valor TEXT,
        tesoro_ganado INTEGER,
        tesoro_gastado INTEGER,
        ticket_text TEXT,
        iva_desglose TEXT
    );

    CREATE TABLE ticket_lines (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticket_id INTEGER,
        sku TEXT,
        nombre TEXT,
        cantidad INTEGER,
        precio INTEGER,
        iva INTEGER,
        line_tipo TEXT,
        producto_id INTEGER
    );

    CREATE TABLE devoluciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticket_id INTEGER,
        cliente_id INTEGER,
        cajero TEXT,
        total_cents INTEGER,
        created_at TEXT
    );

    CREATE TABLE points_movements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente_id INTEGER,
        puntos INTEGER,
        motivo TEXT,
        ticket_id INTEGER,
        usuario_id INTEGER,
        created_at TEXT
    );

    CREATE TABLE stock_movements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        producto_id INTEGER,
        cantidad INTEGER,
        motivo TEXT,
        ticket_line_id INTEGER
    );

    CREATE TABLE payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticket_id INTEGER,
        metodo TEXT,
        importe INTEGER,
        created_at TEXT
    );

    CREATE TABLE audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT,
        ticket_id INTEGER,
        usuario TEXT,
        accion TEXT,
        detalles TEXT
    );
    """)
    db.connection.commit()


def test_confirmar_devolucion_persiste_nulls():
    db = Database(':memory:')
    db.connect()
    setup_minimal_schema(db)

    # insertar un producto y cliente
    cur = db.connection.cursor()
    cur.execute('INSERT INTO productos (id, nombre, stock_actual, ventas_totales) VALUES (?, ?, ?, ?)', (1, 'P1', 10, 0))
    cur.execute('INSERT INTO clientes (id, nombre) VALUES (?, ?)', (1, 'Cliente1'))
    db.connection.commit()

    # carrito con una línea de devolución
    item = {'id': 1, 'sku': 'SKU1', 'nombre': 'Producto1', 'pvp': Decimal('10.00'), 'tipo_iva': 21, 'cantidad': 1, 'line_tipo': 'devolucion'}
    carrito = MockCarrito([item], cliente={'id': 1, 'nombre': 'Cliente1'})

    svc = DevolucionesService(db, carrito)

    # ejecutar confirmar_devolucion
    ticket_id, num_ticket = svc.confirmar_devolucion(usuario='tester', cliente_id=1, efectivo=Decimal('0'))

    # comprobar en la BD
    row = db.fetch_one('SELECT forma_pago, importe_efectivo, importe_tarjeta FROM tickets WHERE id = ? LIMIT 1', (ticket_id,))
    assert row is not None
    forma_pago, importe_efectivo, importe_tarjeta = row
    assert forma_pago is None
    assert importe_efectivo is None
    assert importe_tarjeta is None

    db.close_connection()
