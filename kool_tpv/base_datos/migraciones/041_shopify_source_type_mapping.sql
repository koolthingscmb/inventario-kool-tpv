-- Migración 041: Mapeo de Fuentes Shopify a Tipos de Producto
-- Permite asociar una fuente externa (ej: AniList) con uno o varios tipos de producto locales.

CREATE TABLE IF NOT EXISTS shopify_source_type_mapping (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL, -- ID de la fuente en SourceManager (ej: 'source_anilist')
    tipo_id INTEGER NOT NULL, -- ID del tipo en la tabla 'tipos'
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tipo_id) REFERENCES tipos(id) ON DELETE CASCADE,
    UNIQUE(source_id, tipo_id)
);

CREATE INDEX IF NOT EXISTS idx_shopify_source_mapping_tipo ON shopify_source_type_mapping(tipo_id);
CREATE INDEX IF NOT EXISTS idx_shopify_source_mapping_source ON shopify_source_type_mapping(source_id);
