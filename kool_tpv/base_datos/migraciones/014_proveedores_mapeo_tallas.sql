-- Migración 014: Añadir columna mapeo_tallas a la tabla proveedores
-- Esta columna almacenará la configuración JSON para mapear tallas del proveedor → tallas internas (XS, S, M, L, XL, etc.)

ALTER TABLE proveedores ADD COLUMN mapeo_tallas TEXT DEFAULT '{}';
