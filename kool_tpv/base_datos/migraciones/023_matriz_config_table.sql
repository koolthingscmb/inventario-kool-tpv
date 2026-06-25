-- Migración 023: Nueva tabla de configuración de matriz para Tipos y Variantes
-- Separa la configuración de la matriz del stock físico.

CREATE TABLE IF NOT EXISTS produccion_tipo_color_tallas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo_id INTEGER NOT NULL,
    variante_id INTEGER,
    color_id INTEGER,
    talla_id INTEGER,
    FOREIGN KEY(tipo_id) REFERENCES tipos(id) ON DELETE CASCADE,
    FOREIGN KEY(variante_id) REFERENCES tipos_variantes(id) ON DELETE CASCADE,
    FOREIGN KEY(color_id) REFERENCES produccion_colores(id) ON DELETE CASCADE,
    FOREIGN KEY(talla_id) REFERENCES produccion_tallas(id) ON DELETE CASCADE
);

-- Eliminar el campo variante_id de la tabla de stock (limpieza)
ALTER TABLE produccion_stock_colores_tallas DROP COLUMN variante_id;
