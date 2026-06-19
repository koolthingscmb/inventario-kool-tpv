-- Migración: Tabla de stock por color para productos
-- Fecha: 2025-06-19
-- Descripción: Control de stock por color de productos TPV

CREATE TABLE IF NOT EXISTS produccion_stock_colores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    producto_id INTEGER NOT NULL,  -- ID del producto TPV
    color_id INTEGER NOT NULL,
    cantidad INTEGER DEFAULT 0,    -- stock en unidades
    FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE CASCADE,
    FOREIGN KEY (color_id) REFERENCES produccion_colores(id) ON DELETE CASCADE,
    UNIQUE(producto_id, color_id)
);
