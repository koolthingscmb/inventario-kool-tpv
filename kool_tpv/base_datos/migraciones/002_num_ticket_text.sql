BEGIN TRANSACTION;

CREATE TABLE tickets_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    cajero TEXT,
    cliente TEXT,
    cliente_id INTEGER,
    num_ticket TEXT,
    forma_pago TEXT,
    total REAL NOT NULL,
    pagado REAL,
    cambio REAL,
    importe_efectivo REAL DEFAULT 0.0,
    importe_tarjeta REAL DEFAULT 0.0,
    descuento_euros REAL,
    descuento_tipo TEXT,
    descuento_valor REAL,
    cierre_id INTEGER,
    tesoro_ganado REAL DEFAULT 0,
    tesoro_gastado REAL DEFAULT 0,
    tesoro_total_ticket REAL DEFAULT 0,
    ticket_text TEXT,
    usuario_id INTEGER,
    num_ventas INTEGER DEFAULT 0,
    subtotal REAL DEFAULT 0.0
);

INSERT INTO tickets_new
SELECT
    id, created_at, cajero, cliente, cliente_id,
    CAST(num_ticket AS TEXT),
    forma_pago, total, pagado, cambio,
    importe_efectivo, importe_tarjeta,
    descuento_euros, descuento_tipo, descuento_valor,
    cierre_id, tesoro_ganado, tesoro_gastado,
    tesoro_total_ticket, ticket_text,
    usuario_id, num_ventas, subtotal
FROM tickets;

-- Drop triggers that reference tickets to avoid errors when replacing table
DROP TRIGGER IF EXISTS trg_ticket_lines_after_delete;
DROP TRIGGER IF EXISTS trg_ticket_lines_after_insert;
DROP TRIGGER IF EXISTS trg_ticket_lines_after_update_ticketid;

DROP TABLE tickets;
ALTER TABLE tickets_new RENAME TO tickets;

COMMIT;
