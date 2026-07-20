-- Migración 030: Refactorización a Pedidos Cabecera + Líneas para permitir múltiples productos
-- Primero eliminamos las tablas viejas de la migración 029 si existen
DROP TABLE IF EXISTS pedidos_clientes_lines;
DROP TABLE IF EXISTS pedidos_clientes;

CREATE TABLE IF NOT EXISTS pedidos_clientes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_id INTEGER,
    contacto_nombre TEXT,
    contacto_telefono TEXT,
    contacto_email TEXT,
    estado TEXT DEFAULT 'pendiente',
    fecha_pedido DATETIME DEFAULT CURRENT_TIMESTAMP,
    notas_generales TEXT,
    usuario_id INTEGER,
    FOREIGN KEY(cliente_id) REFERENCES clientes(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS pedidos_clientes_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pedido_id INTEGER,
    producto_id INTEGER,
    nombre_manual TEXT,
    tipo_manual TEXT,
    proveedor_manual TEXT,
    cantidad INTEGER DEFAULT 1,
    estado_linea TEXT DEFAULT 'pendiente',
    fecha_en_stock DATETIME,
    FOREIGN KEY(pedido_id) REFERENCES pedidos_clientes(id) ON DELETE CASCADE,
    FOREIGN KEY(producto_id) REFERENCES productos(id) ON DELETE SET NULL
);

-- Índices para rendimiento
CREATE INDEX IF NOT EXISTS idx_pedidos_cab_estado ON pedidos_clientes(estado);
CREATE INDEX IF NOT EXISTS idx_pedidos_lin_pedido ON pedidos_clientes_lines(pedido_id);
CREATE INDEX IF NOT EXISTS idx_pedidos_lin_producto ON pedidos_clientes_lines(producto_id);
