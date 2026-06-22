"""Migración 009: Relación N:M entre diseños y tipos de producto.

Estrategia:
 1. Crear tabla intermedia `produccion_disenos_tipos`.
 2. Migrar datos actuales de `produccion_disenos.tipo_producto` a la nueva tabla.
 3. Recrear `produccion_disenos` eliminando la columna `tipo_producto`.

Uso:
    python kool_tpv/base_datos/migraciones/009_produccion_disenos_n_m_tipos.py [ruta_a_db]
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

        # 1. Crear tabla intermedia
        cur.execute("""
            CREATE TABLE IF NOT EXISTS produccion_disenos_tipos (
                diseno_codigo TEXT NOT NULL,
                tipo_id INTEGER NOT NULL,
                PRIMARY KEY (diseno_codigo, tipo_id),
                FOREIGN KEY (diseno_codigo) REFERENCES produccion_disenos(codigo) ON DELETE CASCADE,
                FOREIGN KEY (tipo_id) REFERENCES produccion_tipos(id) ON DELETE CASCADE
            )
        """)
        logger.info("Tabla produccion_disenos_tipos creada")

        # 2. Migrar datos si existe la columna tipo_producto
        cols = [c[1] for c in cur.execute("PRAGMA table_info('produccion_disenos')").fetchall()]
        if 'tipo_producto' in cols:
            cur.execute("""
                INSERT OR IGNORE INTO produccion_disenos_tipos (diseno_codigo, tipo_id)
                SELECT codigo, tipo_producto FROM produccion_disenos
                WHERE tipo_producto IS NOT NULL
            """)
            logger.info("Datos migrados a produccion_disenos_tipos")

            # 3. Recrear produccion_disenos sin la columna tipo_producto
            cur.execute("""
                CREATE TABLE produccion_disenos_new (
                    codigo TEXT PRIMARY KEY,
                    coleccion TEXT NOT NULL,
                    nombre TEXT NOT NULL,
                    variante TEXT,
                    coste_camiseta INTEGER,
                    coste_taza INTEGER,
                    coste_gorra INTEGER,
                    coste_calcetin INTEGER,
                    coste_libreta INTEGER,
                    coste_poster INTEGER,
                    coste_cartera INTEGER,
                    activo INTEGER DEFAULT 1
                )
            """)
            
            # Copiar datos (excepto tipo_producto)
            cur.execute("""
                INSERT INTO produccion_disenos_new
                (codigo, coleccion, nombre, variante, coste_camiseta, coste_taza,
                 coste_gorra, coste_calcetin, coste_libreta, coste_poster, coste_cartera, activo)
                SELECT 
                 codigo, coleccion, nombre, variante, coste_camiseta, coste_taza,
                 coste_gorra, coste_calcetin, coste_libreta, coste_poster, coste_cartera, activo
                FROM produccion_disenos
            """)
            
            cur.execute("DROP TABLE produccion_disenos")
            cur.execute("ALTER TABLE produccion_disenos_new RENAME TO produccion_disenos")
            logger.info("Tabla produccion_disenos recreada sin tipo_producto")

        conn.commit()
        logger.info("Migración 009 completada correctamente")

    except Exception:
        conn.rollback()
        logger.exception("Migración 009 falló")
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
        db_arg = str(here / 'base_datos' / 'kool_bd.db')

    print(f'Running migration 009 against DB: {db_arg}')
    migrate(db_arg)
