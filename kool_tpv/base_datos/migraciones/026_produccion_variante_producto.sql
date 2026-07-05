-- Mapeo entre variantes de producción y productos del TPV
-- Permite que al completar una orden de producción se incremente el stock del producto TPV asociado.
-- Incluye optionalmente extras y colecciones para mapeos más complejos.

CREATE TABLE IF NOT EXISTS produccion_variantes_productos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    variante_id INTEGER NOT NULL,
    producto_id INTEGER NOT NULL,
    extra_id INTEGER,
    coleccion_id INTEGER,
    ratio INTEGER DEFAULT 1,
    activo INTEGER DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (variante_id) REFERENCES tipos_variantes(id) ON DELETE CASCADE,
    FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE CASCADE,
    FOREIGN KEY (extra_id) REFERENCES produccion_extras(id) ON DELETE SET NULL,
    FOREIGN KEY (coleccion_id) REFERENCES produccion_colecciones(id) ON DELETE SET NULL
);
