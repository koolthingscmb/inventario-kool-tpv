-- Migración 017: Añadir campos de requerimiento a tipos_variantes
ALTER TABLE tipos_variantes ADD COLUMN requiere_talla INTEGER DEFAULT 0;
ALTER TABLE tipos_variantes ADD COLUMN requiere_color INTEGER DEFAULT 0;
