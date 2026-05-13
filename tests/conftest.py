import pytest
import sqlite3
from decimal import Decimal
from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.almacen.producto_repository import ProductoRepository
from kool_tpv.base_datos.producto_service import ProductoService

_SCHEMA = """
CREATE TABLE IF NOT EXISTS productos (
    id INTEGER PRIMARY KEY,
    nombre TEXT,
    nombre_boton TEXT,
    sku TEXT UNIQUE,
    pvp_variable INTEGER DEFAULT 0,
    tipo_iva INTEGER DEFAULT 21,
    stock_actual INTEGER DEFAULT 0,
    stock_minimo INTEGER DEFAULT 0,
    ventas_totales INTEGER DEFAULT 0,
    categoria INTEGER,
    tipo INTEGER,
    proveedor_id INTEGER,
    activo INTEGER DEFAULT 1,
    descripcion_shopify TEXT,
    notas_internas TEXT,
    titulo TEXT,
    created_at TEXT,
    updated_at TEXT,
    pending_sync INTEGER DEFAULT 0,
    seo_title TEXT,
    seo_description TEXT,
    tipo_shop TEXT,
    etiquetas TEXT,
    shop_link TEXT,
    shopify_taxonomy TEXT
);

CREATE TABLE IF NOT EXISTS precios (
    id INTEGER PRIMARY KEY,
    producto_id INTEGER,
    pvp INTEGER DEFAULT 0,
    coste INTEGER DEFAULT 0,
    activo INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS categorias (
    id INTEGER PRIMARY KEY,
    nombre TEXT
);

CREATE TABLE IF NOT EXISTS tipos (
    id INTEGER PRIMARY KEY,
    nombre TEXT
);

CREATE TABLE IF NOT EXISTS proveedores (
    id INTEGER PRIMARY KEY,
    nombre TEXT
);

CREATE TABLE IF NOT EXISTS ticket_lines (
    id INTEGER PRIMARY KEY,
    ticket_id INTEGER,
    sku TEXT,
    cantidad INTEGER,
    line_tipo TEXT
);

CREATE TABLE IF NOT EXISTS codigos_barras (
    id INTEGER PRIMARY KEY,
    producto_id INTEGER,
    ean TEXT
);

CREATE TABLE IF NOT EXISTS clientes (
    id INTEGER PRIMARY KEY,
    nombre TEXT
);

CREATE TABLE IF NOT EXISTS tickets (
    id INTEGER PRIMARY KEY,
    created_at TEXT,
    cliente_id INTEGER
);
"""


@pytest.fixture
def db_test():
    """DB SQLite en memoria para tests. Se destruye al terminar cada test."""
    db = Database(':memory:')
    db.connect()
    db.connection.executescript(_SCHEMA)
    db.connection.commit()
    yield db
    db.close_connection()


@pytest.fixture
def producto_repo(db_test):
    """ProductoRepository con DB de prueba."""
    return ProductoRepository(db_test)


@pytest.fixture
def producto_service(db_test):
    """ProductoService con DB de prueba."""
    return ProductoService(db_test)
