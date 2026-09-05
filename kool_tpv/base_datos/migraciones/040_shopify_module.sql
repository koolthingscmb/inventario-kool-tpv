-- Migración 040: Módulo Shopify
-- Tablas para mapeo de productos y log de sincronización

CREATE TABLE IF NOT EXISTS shopify_product_mapping (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    producto_id INTEGER NOT NULL,
    shopify_product_id TEXT NOT NULL,
    handle TEXT,
    status TEXT,
    last_synced_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS shopify_sync_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    producto_id INTEGER,
    accion TEXT NOT NULL, -- 'create', 'update', 'delete'
    resultado TEXT NOT NULL, -- 'success', 'error'
    mensaje TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_shopify_mapping_producto ON shopify_product_mapping(producto_id);
CREATE INDEX IF NOT EXISTS idx_shopify_mapping_external ON shopify_product_mapping(shopify_product_id);
