-- Migración 015: Tabla tipos_variantes
-- Permite definir variantes para cada tipo de producto (ej: Lámina A4, A3...)
-- con costes y precios específicos.

CREATE TABLE IF NOT EXISTS tipos_variantes (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo_id             INTEGER NOT NULL,
    nombre              TEXT NOT NULL,
    coste_base          INTEGER DEFAULT 0,
    precio_recomendado  INTEGER DEFAULT 0,
    activo              INTEGER DEFAULT 1,
    shopify_variant_id  TEXT,
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(tipo_id) REFERENCES tipos(id) ON DELETE CASCADE
);

-- Índice para búsquedas rápidas por tipo
CREATE INDEX IF NOT EXISTS idx_tipos_variantes_tipo ON tipos_variantes(tipo_id);
