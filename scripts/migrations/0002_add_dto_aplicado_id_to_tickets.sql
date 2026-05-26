-- Migration: add dto_aplicado_id column to tickets
-- Adds a nullable integer column referencing descuentos.id (no FK enforced)
PRAGMA foreign_keys=off;
BEGIN TRANSACTION;
ALTER TABLE tickets ADD COLUMN dto_aplicado_id INTEGER;
COMMIT;
PRAGMA foreign_keys=on;
