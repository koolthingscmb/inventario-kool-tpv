-- Migración 025: Tabla intermedia tipos_variantes_metodos
-- Relaciona variantes con métodos de impresión disponibles

CREATE TABLE IF NOT EXISTS tipos_variantes_metodos (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    variante_id INTEGER NOT NULL,
    metodo_id   INTEGER NOT NULL,
    FOREIGN KEY(variante_id) REFERENCES tipos_variantes(id) ON DELETE CASCADE,
    FOREIGN KEY(metodo_id)   REFERENCES produccion_metodos(id) ON DELETE CASCADE,
    UNIQUE(variante_id, metodo_id)
);

CREATE INDEX IF NOT EXISTS idx_tipos_variantes_metodos_variante ON tipos_variantes_metodos(variante_id);
CREATE INDEX IF NOT EXISTS idx_tipos_variantes_metodos_metodo ON tipos_variantes_metodos(metodo_id);
