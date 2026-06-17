-- Migración 004: Control de Presencia
CREATE TABLE IF NOT EXISTS presencia (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id        INTEGER NOT NULL,
    entrada           DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    salida            DATETIME,
    duracion_minutos  INTEGER,
    estado            TEXT DEFAULT 'activa', -- 'activa' o 'completada'
    notas             TEXT,
    FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
);

CREATE INDEX IF NOT EXISTS idx_presencia_usuario ON presencia(usuario_id);
CREATE INDEX IF NOT EXISTS idx_presencia_estado ON presencia(estado);
