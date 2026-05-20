-- Migración 003: tabla devoluciones + columna total_devoluciones en clientes

-- Columna total_devoluciones en clientes (céntimos, igual que el resto de importes)
ALTER TABLE clientes ADD COLUMN total_devoluciones INTEGER DEFAULT 0;

-- Tabla devoluciones: un registro por cada devolución confirmada
CREATE TABLE IF NOT EXISTS devoluciones (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id   INTEGER NOT NULL,
    cliente_id  INTEGER,
    cajero      TEXT,
    total_cents INTEGER NOT NULL DEFAULT 0,
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(ticket_id)  REFERENCES tickets(id),
    FOREIGN KEY(cliente_id) REFERENCES clientes(id)
);
