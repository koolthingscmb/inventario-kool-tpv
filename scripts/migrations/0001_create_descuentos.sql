-- Migration: create descuentos table
-- Monetary amounts stored in cents (INTEGER)
CREATE TABLE IF NOT EXISTS descuentos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo TEXT UNIQUE,
    nombre TEXT,
    descripcion TEXT,
    -- tipo: 'directo' or 'porcentaje'
    tipo TEXT,
    -- valor en céntimos cuando tipo='directo'
    valor_cents INTEGER,
    -- valor porcentual (ej. 10 = 10%) cuando tipo='porcentaje'
    valor_porcentaje INTEGER,
    activo INTEGER DEFAULT 1,
    vigencia_inicio TEXT,
    vigencia_fin TEXT,
    condiciones TEXT, -- JSON string for extra rules
    aplicar_limite INTEGER,
    created_by INTEGER,
    created_at TEXT,
    updated_at TEXT
);
