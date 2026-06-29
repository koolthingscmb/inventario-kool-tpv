-- Migración 024: Añadir variante_id a produccion_disenos_stock y actualizar restricción UNIQUE

PRAGMA foreign_keys=OFF;

-- 1. Renombrar tabla actual
ALTER TABLE produccion_disenos_stock RENAME TO produccion_disenos_stock_old;

-- 2. Crear nueva tabla con variante_id y la nueva restricción UNIQUE
CREATE TABLE produccion_disenos_stock (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    diseno_codigo TEXT NOT NULL,
    tipo_id INTEGER NOT NULL,
    color_id INTEGER,
    talla TEXT,
    variante_id INTEGER,
    cantidad INTEGER DEFAULT 0,
    FOREIGN KEY (diseno_codigo) REFERENCES produccion_disenos(codigo),
    FOREIGN KEY (tipo_id) REFERENCES tipos(id),
    FOREIGN KEY (color_id) REFERENCES produccion_colores(id),
    FOREIGN KEY (variante_id) REFERENCES tipos_variantes(id),
    UNIQUE(diseno_codigo, tipo_id, color_id, talla, variante_id)
);

-- 3. Migrar datos existentes (variante_id será NULL por defecto)
INSERT INTO produccion_disenos_stock (id, diseno_codigo, tipo_id, color_id, talla, cantidad)
SELECT id, diseno_codigo, tipo_id, color_id, talla, cantidad
FROM produccion_disenos_stock_old;

-- 4. Eliminar tabla vieja
DROP TABLE produccion_disenos_stock_old;

PRAGMA foreign_keys=ON;
