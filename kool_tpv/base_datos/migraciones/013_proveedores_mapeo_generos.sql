-- Migración 013: Añadir columna mapeo_generos a la tabla proveedores
-- Esta columna almacenará la configuración JSON para detectar géneros (Hombre, Mujer, etc.) en albaranes.

ALTER TABLE proveedores ADD COLUMN mapeo_generos TEXT DEFAULT '{}';
