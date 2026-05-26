-- Migration: recreate tickets table adding FK on dto_aplicado_id -> descuentos(id)
-- This migration recreates the tickets table with a foreign key constraint
PRAGMA foreign_keys=off;
BEGIN TRANSACTION;

CREATE TABLE IF NOT EXISTS tickets_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    cajero TEXT,
    cliente TEXT,
    cliente_id INTEGER,
    num_ticket TEXT,
    forma_pago TEXT,
    total INTEGER NOT NULL DEFAULT 0,
    pagado INTEGER DEFAULT 0,
    cambio INTEGER DEFAULT 0,
    importe_efectivo INTEGER DEFAULT 0,
    importe_tarjeta INTEGER DEFAULT 0,
    descuento_euros INTEGER DEFAULT 0,
    descuento_tipo TEXT,
    descuento_valor INTEGER DEFAULT 0,
    cierre_id INTEGER,
    tesoro_ganado INTEGER DEFAULT 0,
    tesoro_gastado INTEGER DEFAULT 0,
    tesoro_total_ticket INTEGER DEFAULT 0,
    ticket_text TEXT,
    usuario_id INTEGER,
    num_ventas INTEGER DEFAULT 0,
    subtotal INTEGER DEFAULT 0,
    iva_desglose TEXT DEFAULT '{}',
    importe_web INTEGER,
    dto_aplicado_id INTEGER,
    FOREIGN KEY(dto_aplicado_id) REFERENCES descuentos(id) ON DELETE SET NULL
);

INSERT INTO tickets_new (
    id, created_at, cajero, cliente, cliente_id, num_ticket, forma_pago, total, pagado, cambio,
    importe_efectivo, importe_tarjeta, descuento_euros, descuento_tipo, descuento_valor, cierre_id,
    tesoro_ganado, tesoro_gastado, tesoro_total_ticket, ticket_text, usuario_id, num_ventas, subtotal,
    iva_desglose, importe_web, dto_aplicado_id
)
SELECT
    id, created_at, cajero, cliente, cliente_id, num_ticket, forma_pago, total, pagado, cambio,
    importe_efectivo, importe_tarjeta, descuento_euros, descuento_tipo, descuento_valor, cierre_id,
    tesoro_ganado, tesoro_gastado, tesoro_total_ticket, ticket_text, usuario_id, num_ventas, subtotal,
    iva_desglose, importe_web, dto_aplicado_id
FROM tickets;

DROP TABLE tickets;
ALTER TABLE tickets_new RENAME TO tickets;

COMMIT;
PRAGMA foreign_keys=on;
