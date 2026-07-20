-- Migración 029: Tabla pedidos_clientes para pedidos especiales y reservas
CREATE TABLE IF NOT EXISTS pedidos_clientes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_id INTEGER,
    contacto_nombre TEXT,
    contacto_telefono TEXT,
    producto_id INTEGER,
    info TEXT,
    descripcion TEXT,
    cantidad_solicitada INTEGER DEFAULT 1,
    estado TEXT DEFAULT 'pendiente', -- pendiente, en_stock, avisado, entregado, cancelado
    fecha_pedido DATETIME DEFAULT CURRENT_TIMESTAMP,
    fecha_aviso DATETIME,
    fecha_entrega DATETIME,
    notas TEXT,
    usuario_id INTEGER,
    FOREIGN KEY(cliente_id) REFERENCES clientes(id) ON DELETE SET NULL,
    FOREIGN KEY(producto_id) REFERENCES productos(id) ON DELETE SET NULL
);

-- Índices para mejorar la búsqueda y filtros
CREATE INDEX IF NOT EXISTS idx_pedidos_estado ON pedidos_clientes(estado);
CREATE INDEX IF NOT EXISTS idx_pedidos_cliente ON pedidos_clientes(cliente_id);
CREATE INDEX IF NOT EXISTS idx_pedidos_producto ON pedidos_clientes(producto_id);
