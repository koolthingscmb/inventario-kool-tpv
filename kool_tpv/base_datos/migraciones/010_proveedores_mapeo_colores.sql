-- Migración: Añadir columna mapeo_colores a proveedores
-- Fecha: 2026-06-23
-- Descripción: JSON con mapeo de colores del proveedor → colores internos

ALTER TABLE proveedores ADD COLUMN mapeo_colores TEXT;
