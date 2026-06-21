-- Migración: Géneros y tallas para producción
-- Fecha: 2026-06-21
-- Descripción: Tablas para géneros, tallas, y sus relaciones con tipos

-- Añadir requiere_genero a produccion_tipos
ALTER TABLE produccion_tipos ADD COLUMN requiere_genero INTEGER DEFAULT 0;

-- Tabla de géneros
CREATE TABLE IF NOT EXISTS produccion_generos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL UNIQUE,
    orden INTEGER DEFAULT 0,
    activo INTEGER DEFAULT 1
);

-- Tabla de tallas
CREATE TABLE IF NOT EXISTS produccion_tallas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    orden INTEGER DEFAULT 0,
    activo INTEGER DEFAULT 1
);

-- Relación género → tallas (N:M)
CREATE TABLE IF NOT EXISTS produccion_genero_tallas (
    genero_id INTEGER NOT NULL,
    talla_id INTEGER NOT NULL,
    PRIMARY KEY (genero_id, talla_id),
    FOREIGN KEY (genero_id) REFERENCES produccion_generos(id),
    FOREIGN KEY (talla_id) REFERENCES produccion_tallas(id)
);

-- Relación tipo → géneros (N:M)
CREATE TABLE IF NOT EXISTS produccion_tipos_generos (
    tipo_id INTEGER NOT NULL,
    genero_id INTEGER NOT NULL,
    PRIMARY KEY (tipo_id, genero_id),
    FOREIGN KEY (tipo_id) REFERENCES produccion_tipos(id),
    FOREIGN KEY (genero_id) REFERENCES produccion_generos(id)
);

-- Relación tipo → colores (N:M)
CREATE TABLE IF NOT EXISTS produccion_tipos_colores (
    tipo_id INTEGER NOT NULL,
    color_id INTEGER NOT NULL,
    PRIMARY KEY (tipo_id, color_id),
    FOREIGN KEY (tipo_id) REFERENCES produccion_tipos(id),
    FOREIGN KEY (color_id) REFERENCES produccion_colores(id)
);

-- === DATOS DE PRUEBA ===

-- Géneros
INSERT OR IGNORE INTO produccion_generos (id, nombre, orden, activo) VALUES
    (1, 'STANDARD', 1, 1),
    (2, 'INFANTIL', 2, 1),
    (3, 'MUJER', 3, 1),
    (4, 'OVERSIZED', 4, 1),
    (5, 'BABY', 5, 1),
    (6, 'TIRANTES', 6, 1);

-- Tallas
INSERT OR IGNORE INTO produccion_tallas (id, nombre, orden, activo) VALUES
    (1,  'XS',    1,  1),
    (2,  'S',     2,  1),
    (3,  'M',     3,  1),
    (4,  'L',     4,  1),
    (5,  'XL',    5,  1),
    (6,  '2XL',   6,  1),
    (7,  '3XL',   7,  1),
    (8,  '4XL',   8,  1),
    (9,  '5XL',   9,  1),
    (10, '1-2',   10, 1),
    (11, '3-4',   11, 1),
    (12, '5-6',   12, 1),
    (13, '7-8',   13, 1),
    (14, '9-11',  14, 1),
    (15, '12-13', 15, 1),
    (16, '0-3',   16, 1),
    (17, '3-6',   17, 1),
    (18, '6-12',  18, 1),
    (19, '12-18', 19, 1),
    (20, '18-24', 20, 1);

-- Relaciones género → tallas

-- STANDARD: S, M, L, XL, 2XL, 3XL, 4XL, 5XL
INSERT OR IGNORE INTO produccion_genero_tallas (genero_id, talla_id) VALUES
    (1, 2), (1, 3), (1, 4), (1, 5), (1, 6), (1, 7), (1, 8), (1, 9);

-- INFANTIL: 1-2, 3-4, 5-6, 7-8, 9-11, 12-13
INSERT OR IGNORE INTO produccion_genero_tallas (genero_id, talla_id) VALUES
    (2, 10), (2, 11), (2, 12), (2, 13), (2, 14), (2, 15);

-- MUJER: XS, S, M, L, XL, 2XL
INSERT OR IGNORE INTO produccion_genero_tallas (genero_id, talla_id) VALUES
    (3, 1), (3, 2), (3, 3), (3, 4), (3, 5), (3, 6);

-- OVERSIZED: XS, S, M, L, XL, 2XL, 3XL
INSERT OR IGNORE INTO produccion_genero_tallas (genero_id, talla_id) VALUES
    (4, 1), (4, 2), (4, 3), (4, 4), (4, 5), (4, 6), (4, 7);

-- BABY: 0-3, 3-6, 6-12, 12-18, 18-24
INSERT OR IGNORE INTO produccion_genero_tallas (genero_id, talla_id) VALUES
    (5, 16), (5, 17), (5, 18), (5, 19), (5, 20);

-- TIRANTES: S, M, L, XL, 2XL, 3XL
INSERT OR IGNORE INTO produccion_genero_tallas (genero_id, talla_id) VALUES
    (6, 2), (6, 3), (6, 4), (6, 5), (6, 6), (6, 7);

-- CAMISETA (tipo_id=1) → todos los géneros
INSERT OR IGNORE INTO produccion_tipos_generos (tipo_id, genero_id) VALUES
    (1, 1), (1, 2), (1, 3), (1, 4), (1, 5), (1, 6);

-- Marcar CAMISETA como requiere_genero
UPDATE produccion_tipos SET requiere_genero = 1 WHERE id = 1;
