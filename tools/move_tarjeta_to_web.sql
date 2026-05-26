-- Optional maintenance script: move importe_tarjeta -> payments(method='web')
-- This script creates `payments` entries for tickets where forma_pago='web'
-- and the amount was mistakenly stored in `importe_tarjeta`.
-- It does NOT modify existing `tickets` rows (unless you uncomment the UPDATE).

BEGIN TRANSACTION;

INSERT INTO payments (ticket_id, method, amount_cents, created_at)
SELECT id, 'web', importe_tarjeta, datetime('now')
FROM tickets
WHERE forma_pago = 'web' AND importe_tarjeta IS NOT NULL AND importe_tarjeta != 0;

-- OPTIONAL: move value into importe_web and clear importe_tarjeta (commented by default)
-- UPDATE tickets SET importe_web = importe_tarjeta, importe_tarjeta = 0
-- WHERE forma_pago = 'web' AND importe_tarjeta IS NOT NULL AND importe_tarjeta != 0;

COMMIT;

-- IMPORTANT: Review inserted rows in `payments` before running any UPDATE.
