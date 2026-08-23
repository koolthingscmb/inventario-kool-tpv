-- Migración 039: Agrupación de tallas en producción (Relación N:M)
-- Permite que las tallas sean compartidas por varios grupos.

-- 1. Tabla de grupos (Hombre, Mujer, Niño...)
CREATE TABLE IF NOT EXISTS produccion_tallas_grupos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL UNIQUE
);

-- 2. Tabla de asociación (Qué tallas pertenecen a qué grupo)
CREATE TABLE IF NOT EXISTS produccion_tallas_grupo_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    grupo_id INTEGER NOT NULL,
    talla_id INTEGER NOT NULL,
    FOREIGN KEY(grupo_id) REFERENCES produccion_tallas_grupos(id) ON DELETE CASCADE,
    FOREIGN KEY(talla_id) REFERENCES produccion_tallas(id) ON DELETE CASCADE,
    UNIQUE(grupo_id, talla_id)
);

-- 3. Vincular las variantes al grupo de tallas que deben usar
ALTER TABLE tipos_variantes ADD COLUMN grupo_talla_id INTEGER REFERENCES produccion_tallas_grupos(id) ON DELETE SET NULL;
