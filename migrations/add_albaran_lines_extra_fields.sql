-- Migración: Añadir campos extra a albaran_lines
-- Fecha: 2024-06-04

-- Añadir columnas opcionales para datos de proveedor
ALTER TABLE albaran_lines ADD COLUMN editorial TEXT;
ALTER TABLE albaran_lines ADD COLUMN fabricante TEXT;
ALTER TABLE albaran_lines ADD COLUMN pvpr_cents INTEGER DEFAULT 0;

-- Actualizar totales existentes (si es necesario)
UPDATE albaran_lines SET pvpr_cents = 0 WHERE pvpr_cents IS NULL;
