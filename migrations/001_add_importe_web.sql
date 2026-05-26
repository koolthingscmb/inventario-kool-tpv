-- Migration 001: Add `importe_web` column to `tickets` table
-- NOTE: This migration only adds a nullable INTEGER column.
-- Do NOT run this against production without a backup.

BEGIN TRANSACTION;

ALTER TABLE tickets ADD COLUMN importe_web INTEGER;

COMMIT;

-- After applying: new tickets with forma_pago='web' should store the web amount
-- in `importe_web` (in cents). Existing rows are not modified by this file.
