-- Migración: Añadir columna coste_medio a produccion_stock_colores_tallas
-- Fecha: 2026-06-23
-- Descripción: Almacena el coste medio de adquisición de la base textil.

ALTER TABLE produccion_stock_colores_tallas ADD COLUMN coste_medio INTEGER DEFAULT 0;
