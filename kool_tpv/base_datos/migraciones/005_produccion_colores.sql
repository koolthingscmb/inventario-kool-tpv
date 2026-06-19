-- Migración: Tabla de colores para producción
-- Fecha: 2025-06-19
-- Descripción: Colores disponibles para productos de producción

CREATE TABLE IF NOT EXISTS produccion_colores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL UNIQUE,  -- ej: Negro, Blanco, Rojo
    codigo_hex TEXT               -- opcional para UI (ej: #000000)
);
