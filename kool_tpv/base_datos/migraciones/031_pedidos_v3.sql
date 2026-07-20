-- Migración 031: Añadir IDs de Tipo y Proveedor a líneas de pedidos
ALTER TABLE pedidos_clientes_lines ADD COLUMN tipo_id INTEGER;
ALTER TABLE pedidos_clientes_lines ADD COLUMN proveedor_id INTEGER;

-- Referencias (aunque SQLite no valida ALTER TABLE foreign keys por defecto)
-- FOREIGN KEY(tipo_id) REFERENCES tipos_producto(id)
-- FOREIGN KEY(proveedor_id) REFERENCES proveedores(id)
