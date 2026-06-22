"""Migración 008: Cambiar tipo_producto en produccion_disenos de TEXT a INTEGER (FK a produccion_tipos.id).

Estrategia (SQLite-safe):
 1. Crear produccion_disenos_new con tipo_producto INTEGER.
 2. Copiar datos mapeando el texto actual al id correspondiente (case-insensitive).
 3. Eliminar tabla antigua y renombrar la nueva.

Uso:
    python kool_tpv/base_datos/migraciones/008_produccion_disenos_tipo_fk.py [ruta_a_db]
"""
from __future__ import annotations

import sqlite3
import sys
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate(db_path: str):
    db_file = Path(db_path)
    if not db_file.exists():
        raise FileNotFoundError(f"DB not found: {db_path}")

    conn = sqlite3.connect(str(db_file))
    cur = conn.cursor()
    try:
        cur.execute('PRAGMA foreign_keys = OFF')

        # Verificar que la tabla existe
        row = cur.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='produccion_disenos'"
        ).fetchone()
        if not row or not row[0]:
            logger.info("Tabla produccion_disenos no existe — saltando migración 008")
            return

        # Verificar si tipo_producto ya es INTEGER
        cols = cur.execute("PRAGMA table_info('produccion_disenos')").fetchall()
        tipo_col = None
        for c in cols:
            if c[1] == 'tipo_producto':
                tipo_col = c
                break
        if tipo_col and 'INT' in (tipo_col[2] or '').upper():
            logger.info("tipo_producto ya es INTEGER — migración 008 ya aplicada")
            return

        logger.info("Iniciando migración 008: tipo_producto TEXT -> INTEGER (FK)")

        # Crear tabla nueva con tipo_producto INTEGER
        cur.execute("""
            CREATE TABLE produccion_disenos_new (
                codigo TEXT PRIMARY KEY,
                coleccion TEXT NOT NULL,
                nombre TEXT NOT NULL,
                variante TEXT,
                tipo_producto INTEGER,
                coste_camiseta INTEGER,
                coste_taza INTEGER,
                coste_gorra INTEGER,
                coste_calcetin INTEGER,
                coste_libreta INTEGER,
                coste_poster INTEGER,
                coste_cartera INTEGER,
                activo INTEGER DEFAULT 1,
                FOREIGN KEY (tipo_producto) REFERENCES produccion_tipos(id)
            )
        """)
        logger.info("Tabla produccion_disenos_new creada")

        # Copiar datos mapeando tipo_producto de texto a id (case-insensitive)
        cur.execute("""
            INSERT INTO produccion_disenos_new
                (codigo, coleccion, nombre, variante, tipo_producto,
                 coste_camiseta, coste_taza, coste_gorra, coste_calcetin,
                 coste_libreta, coste_poster, coste_cartera, activo)
            SELECT
                d.codigo, d.coleccion, d.nombre, d.variante,
                CASE
                    WHEN d.tipo_producto IS NULL OR d.tipo_producto = '' THEN NULL
                    ELSE (SELECT t.id FROM produccion_tipos t
                          WHERE LOWER(t.nombre) = LOWER(d.tipo_producto)
                          LIMIT 1)
                END,
                d.coste_camiseta, d.coste_taza, d.coste_gorra, d.coste_calcetin,
                d.coste_libreta, d.coste_poster, d.coste_cartera, d.activo
            FROM produccion_disenos d
        """)
        copied = cur.rowcount
        logger.info("Datos copiados: %d filas", copied)

        # Verificar que no haya tipos sin mapear
        unmapped = cur.execute("""
            SELECT d.codigo, d.tipo_producto
            FROM produccion_disenos d
            WHERE d.tipo_producto IS NOT NULL AND d.tipo_producto != ''
              AND NOT EXISTS (
                  SELECT 1 FROM produccion_tipos t
                  WHERE LOWER(t.nombre) = LOWER(d.tipo_producto)
              )
        """).fetchall()
        if unmapped:
            logger.warning("Tipos sin mapear (quedarán como NULL): %s", unmapped)

        # Intercambiar tablas
        cur.execute('DROP TABLE produccion_disenos')
        cur.execute('ALTER TABLE produccion_disenos_new RENAME TO produccion_disenos')
        logger.info("Tabla renombrada: produccion_disenos_new -> produccion_disenos")

        # Recrear índices si los había
        extra_sql = cur.execute(
            "SELECT sql FROM sqlite_master WHERE tbl_name = 'produccion_disenos' AND sql IS NOT NULL AND type IN ('index','trigger')"
        ).fetchall()
        for r in extra_sql:
            if r[0]:
                try:
                    cur.execute(r[0])
                except Exception:
                    logger.exception("Error recreando: %s", r[0])

        conn.commit()
        logger.info("Migración 008 completada correctamente")

    except Exception:
        conn.rollback()
        logger.exception("Migración 008 falló — rollback")
        raise
    finally:
        try:
            cur.execute('PRAGMA foreign_keys = ON')
        except Exception:
            pass
        conn.close()


if __name__ == '__main__':
    db_arg = None
    if len(sys.argv) > 1:
        db_arg = sys.argv[1]
    else:
        here = Path(__file__).resolve().parents[2]
        db_arg = str(here / 'kool_bd.db')

    print(f'Running migration 008 against DB: {db_arg}')
    migrate(db_arg)
