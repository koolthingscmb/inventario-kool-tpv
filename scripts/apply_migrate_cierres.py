#!/usr/bin/env python3
"""Runner para aplicar la migración de cierres.

Ejecuta `scripts/migrate_cierres.sql` contra `kool_tpv/base_datos/kool_bd.db` usando el wrapper Database.
"""
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / 'kool_tpv' / 'base_datos' / 'kool_bd.db'
SQL_FILE = Path(__file__).resolve().parent / 'migrate_cierres.sql'

if not SQL_FILE.exists():
    print(f"ERROR: SQL file not found: {SQL_FILE}")
    sys.exit(1)

from kool_tpv.base_datos.db_wrapper import Database


def main():
    db = Database(str(DB_PATH))
    try:
        db.connect()
    except Exception as e:
        print(f"ERROR connecting to DB {DB_PATH}: {e}")
        sys.exit(1)

    sql = SQL_FILE.read_text()
    try:
        print(f"Applying migration from {SQL_FILE} to {DB_PATH}")
        # Use executescript to allow multiple statements in the SQL file
        try:
            db.connection.executescript(sql)
        except Exception:
            # Fallback: split on ';' and execute statements individually
            for stmt in [s.strip() for s in sql.split(';') if s.strip()]:
                db.execute_query(stmt + ';')
        print("Migration applied successfully.")
    except Exception as e:
        print(f"Migration failed: {e}")
        sys.exit(2)
    finally:
        db.close_connection()


if __name__ == '__main__':
    main()
