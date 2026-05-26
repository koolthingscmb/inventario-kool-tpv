#!/usr/bin/env python3
"""Apply migration 0001: create descuentos table if not exists."""
import sqlite3
import os
import sys

ROOT = os.path.dirname(os.path.dirname(__file__))
DB_PATH = os.path.join(ROOT, 'kool_tpv', 'base_datos', 'kool_bd.db')
SQL_PATH = os.path.join(os.path.dirname(__file__), 'migrations', '0001_create_descuentos.sql')

def main():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        sys.exit(1)

    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='descuentos'")
        if cur.fetchone():
            print('Table descuentos already exists, skipping')
            return

        with open(SQL_PATH, 'r', encoding='utf-8') as f:
            sql = f.read()
        cur.executescript(sql)
        conn.commit()
        print('Migration applied: descuentos table created')

if __name__ == '__main__':
    main()
