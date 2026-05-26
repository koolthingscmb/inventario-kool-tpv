#!/usr/bin/env python3
"""Apply migration 0003: recreate tickets table with FK on dto_aplicado_id."""
import sqlite3
import os
import sys

ROOT = os.path.dirname(os.path.dirname(__file__))
DB_PATH = os.path.join(ROOT, 'kool_tpv', 'base_datos', 'kool_bd.db')
SQL_PATH = os.path.join(os.path.dirname(__file__), 'migrations', '0003_recreate_tickets_with_fk.sql')

def fk_exists(conn):
    cur = conn.cursor()
    try:
        fks = cur.execute("PRAGMA foreign_key_list('tickets')").fetchall()
        return len(fks) > 0
    except Exception:
        return False

def backup_db(db_path):
    import shutil
    bak = db_path + '.bak_before_0003'
    shutil.copy2(db_path, bak)
    return bak

def main():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        sys.exit(1)

    with sqlite3.connect(DB_PATH) as conn:
        if fk_exists(conn):
            print('Foreign key already present on tickets, skipping')
            return

        bak = backup_db(DB_PATH)
        print(f'Backup created: {bak}')

        with open(SQL_PATH, 'r', encoding='utf-8') as f:
            sql = f.read()
        conn.executescript(sql)
        print('Migration applied: tickets recreated with FK on dto_aplicado_id')

if __name__ == '__main__':
    main()
