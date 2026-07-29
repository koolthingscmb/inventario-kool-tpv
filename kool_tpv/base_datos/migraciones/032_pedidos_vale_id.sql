-- Migración 032: Añadir vale_id a pedidos_clientes
-- Permite vincular un vale de devolución a un pedido de cliente
ALTER TABLE pedidos_clientes ADD COLUMN vale_id TEXT;
