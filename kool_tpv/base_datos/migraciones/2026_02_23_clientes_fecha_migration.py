"""Migración segura: cambiar columna `fecha_ultima_compra` a DATETIME.

Estrategia (SQLite-safe):
 - Leer CREATE TABLE actual de `clientes` desde sqlite_master
 - Generar CREATE TABLE para `clientes_new` donde la definición de la
   columna `fecha_ultima_compra` sea `DATETIME` (si existe). Si no existe,
   la añadimos.
 - Crear `clientes_new`, copiar los datos, eliminar `clientes`, renombrar.
 - Reaplicar índices y triggers asociados a `clientes` (si tenían SQL).

Uso:
    python kool_tpv/base_datos/migraciones/2026_02_23_clientes_fecha_migration.py [ruta_a_db]

Este script no modifica lógica de negocio; actúa solo sobre el esquema.
"""
from __future__ import annotations

import sqlite3
import sys
import re
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
        # Temporarily disable foreign keys while we replace the table
        cur.execute('PRAGMA foreign_keys = OFF')

        row = cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='clientes'").fetchone()
        if not row or not row[0]:
            raise RuntimeError('No CREATE TABLE found for clientes')

        create_sql: str = row[0]
        logger.info('Original CREATE TABLE clientes: %s', create_sql)

        lower_sql = create_sql.lower()
        if 'fecha_ultima_compra' in lower_sql:
            # Replace the column type to DATETIME (case-insensitive)
            def _repl(match):
                # match.group(1) is the 'fecha_ultima_compra ' prefix
                return match.group(1) + 'DATETIME'

            new_create_sql = re.sub(r'(?i)(\bfecha_ultima_compra\b\s+)[a-z0-9_()]+', _repl, create_sql)
        else:
            # Column missing: add it before the closing )
            new_create_sql = create_sql.rstrip()
            # insert before final closing parenthesis
            new_create_sql = new_create_sql[:-1] + ',\n    fecha_ultima_compra DATETIME\n)'

        # Create a new table name clientes_new
        new_create_sql = re.sub(r'CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+clientes', 'CREATE TABLE IF NOT EXISTS clientes_new', new_create_sql, flags=re.IGNORECASE)
        new_create_sql = re.sub(r'CREATE\s+TABLE\s+clientes', 'CREATE TABLE clientes_new', new_create_sql, flags=re.IGNORECASE)

        logger.info('CREATE TABLE for clientes_new prepared')

        # Collect index/trigger SQLs to reapply later (only those with non-null SQL)
        extra_sql_rows = cur.execute("SELECT type, name, sql FROM sqlite_master WHERE tbl_name = 'clientes' AND sql IS NOT NULL AND type IN ('index','trigger')").fetchall()
        extra_sql = [r[2] for r in extra_sql_rows if r[2]]

        # Begin migration
        logger.info('Creating clientes_new table')
        cur.execute(new_create_sql)

        # Gather column names from original table to copy data
        cols = [r[1] for r in cur.execute("PRAGMA table_info('clientes')").fetchall()]
        if not cols:
            raise RuntimeError('PRAGMA table_info returned no columns for clientes')

        cols_list = ', '.join([f'"{c}"' for c in cols])
        copy_sql = f'INSERT INTO clientes_new ({cols_list}) SELECT {cols_list} FROM clientes'
        logger.info('Copying data: %s', copy_sql)
        cur.execute(copy_sql)

        # Drop old table and rename new
        logger.info('Dropping old clientes table')
        cur.execute('DROP TABLE clientes')

        logger.info('Renaming clientes_new -> clientes')
        cur.execute('ALTER TABLE clientes_new RENAME TO clientes')

        # Reapply indexes/triggers if any
        for sql in extra_sql:
            try:
                logger.info('Reapplying SQL: %s', sql)
                cur.execute(sql)
            except Exception:
                logger.exception('Failed reapplying SQL: %s', sql)

        conn.commit()
        logger.info('Migration completed successfully')

    except Exception:
        conn.rollback()
        logger.exception('Migration failed, rolled back')
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
        # default location relative to repository
        here = Path(__file__).resolve().parents[2]
        db_arg = str(here / 'kool_bd.db')

    print(f'Running migration against DB: {db_arg}')
    migrate(db_arg)
