-- Migración 016: Añadir variante_id a produccion_lineas
ALTER TABLE produccion_lineas ADD COLUMN variante_id INTEGER REFERENCES tipos_variantes(id);
