-- Migración: eliminar columnas descuento e importe de albaran_lines
-- SQLite no permite DROP COLUMN directamente, se recrea la tabla

PRAGMA foreign_keys = OFF;
BEGIN;

CREATE TABLE albaran_lines_new (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    albaran_id  INTEGER NOT NULL,
    producto_id INTEGER,
    ean         TEXT,
    nombre      TEXT,
    cantidad    INTEGER DEFAULT 1,
    coste       INTEGER DEFAULT 0,
    tipo_iva    INTEGER DEFAULT 21,
    editorial   TEXT DEFAULT '',
    fabricante  TEXT DEFAULT '',
    pvpr_cents  INTEGER DEFAULT 0,
    FOREIGN KEY (albaran_id) REFERENCES albaranes(id) ON DELETE CASCADE
);

INSERT INTO albaran_lines_new
    (id, albaran_id, producto_id, ean, nombre, cantidad, coste, tipo_iva, editorial, fabricante, pvpr_cents)
SELECT
    id, albaran_id, producto_id, ean, nombre, cantidad, coste, tipo_iva, editorial, fabricante, pvpr_cents
FROM albaran_lines;

DROP TABLE albaran_lines;
ALTER TABLE albaran_lines_new RENAME TO albaran_lines;

COMMIT;
PRAGMA foreign_keys = ON;
