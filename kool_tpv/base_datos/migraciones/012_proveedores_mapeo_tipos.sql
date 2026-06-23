-- Migración: Añadir columna mapeo_tipos a proveedores
-- Fecha: 2026-06-23
-- Descripción: JSON con mapeo de palabras clave → tipos internos (Camiseta, Sudadera, etc)

ALTER TABLE proveedores ADD COLUMN mapeo_tipos TEXT;
