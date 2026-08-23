-- Migración 036: Añadir usuario_id a stock_movements para trazabilidad de ajustes manuales y albaranes.
ALTER TABLE stock_movements ADD COLUMN usuario_id INTEGER REFERENCES usuarios(id);
