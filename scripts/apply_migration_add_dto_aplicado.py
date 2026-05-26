#!/usr/bin/env python3
"""Apply migration 0002: add dto_aplicado_id to tickets."""
import sqlite3
import os
import sys

ROOT = os.path.dirname(os.path.dirname(__file__))
DB_PATH = os.path.join(ROOT, 'kool_tpv', 'base_datos', 'kool_bd.db')
SQL_PATH = os.path.join(os.path.dirname(__file__), 'migrations', '0002_add_dto_aplicado_id_to_tickets.sql')

def main():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        sys.exit(1)

    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        # Check if column already exists
        cur.execute("PRAGMA table_info(tickets)")
        cols = [r[1] for r in cur.fetchall()]
        if 'dto_aplicado_id' in cols:
            print('Column dto_aplicado_id already exists on tickets, skipping')
            return

        with open(SQL_PATH, 'r', encoding='utf-8') as f:
            sql = f.read()
        cur.executescript(sql)
        conn.commit()
        print('Migration applied: dto_aplicado_id added to tickets')

if __name__ == '__main__':
    main()
