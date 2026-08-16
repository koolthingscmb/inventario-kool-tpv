-- Migración 037: Añadir tipo_id y variante_id a produccion_disenos_metodos
-- SQLite no soporta añadir FKs ni múltiples columnas con ALTER TABLE,
-- por lo que recreamos la tabla para asegurar integridad.

PRAGMA foreign_keys = OFF;

CREATE TABLE IF NOT EXISTS "produccion_disenos_metodos_new" (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    diseno_codigo TEXT NOT NULL,
    metodo_id INTEGER NOT NULL,
    tipo_id INTEGER,
    variante_id INTEGER,
    coste INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (diseno_codigo) REFERENCES produccion_disenos(codigo) ON DELETE CASCADE,
    FOREIGN KEY (metodo_id) REFERENCES produccion_metodos(id) ON DELETE CASCADE,
    FOREIGN KEY (tipo_id) REFERENCES tipos(id) ON DELETE SET NULL,
    FOREIGN KEY (variante_id) REFERENCES tipos_variantes(id) ON DELETE SET NULL,
    UNIQUE(diseno_codigo, metodo_id, tipo_id, variante_id)
);

-- Copiar datos existentes de la tabla antigua si existe
INSERT INTO produccion_disenos_metodos_new (id, diseno_codigo, metodo_id, coste)
SELECT id, diseno_codigo, metodo_id, coste FROM produccion_disenos_metodos;

-- Sustituir tabla
DROP TABLE produccion_disenos_metodos;
ALTER TABLE produccion_disenos_metodos_new RENAME TO produccion_disenos_metodos;

-- Índices para rendimiento
CREATE INDEX IF NOT EXISTS idx_disenos_metodos_diseno ON produccion_disenos_metodos(diseno_codigo);
CREATE INDEX IF NOT EXISTS idx_disenos_metodos_metodo ON produccion_disenos_metodos(metodo_id);

PRAGMA foreign_keys = ON;
