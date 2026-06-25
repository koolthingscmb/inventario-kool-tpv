-- Migración 022: campo variante_id en produccion_stock_colores_tallas
-- Permite configurar la matriz de colores/tallas a nivel de variante específica
ALTER TABLE produccion_stock_colores_tallas ADD COLUMN variante_id INTEGER REFERENCES tipos_variantes(id) ON DELETE CASCADE;
