#!/usr/bin/env python3
"""Apply migration 0004: recreate tickets table with FK ON DELETE CASCADE and index."""
import sqlite3
import os
import sys
import shutil

ROOT = os.path.dirname(os.path.dirname(__file__))
DB_PATH = os.path.join(ROOT, 'kool_tpv', 'base_datos', 'kool_bd.db')
SQL_PATH = os.path.join(os.path.dirname(__file__), 'migrations', '0004_recreate_tickets_fk_cascade.sql')

def fk_action(conn):
    cur = conn.cursor()
    try:
        rows = cur.execute("PRAGMA foreign_key_list('tickets')").fetchall()
        return rows
    except Exception:
        return []

def backup_db(db_path):
    bak = db_path + '.bak_before_0004'
    shutil.copy2(db_path, bak)
    return bak

def main():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        sys.exit(1)

    with sqlite3.connect(DB_PATH) as conn:
        rows = fk_action(conn)
        # If there is already a fk with CASCADE on dto_aplicado_id, skip
        for r in rows:
            if r[3] == 'dto_aplicado_id' and 'CASCADE' in (r[6] or '').upper():
                print('tickets already has FK ON DELETE CASCADE on dto_aplicado_id, skipping')
                return

        bak = backup_db(DB_PATH)
        print(f'Backup created: {bak}')

        with open(SQL_PATH, 'r', encoding='utf-8') as f:
            sql = f.read()
        conn.executescript(sql)
        print('Migration applied: tickets recreated with FK ON DELETE CASCADE and index created')

if __name__ == '__main__':
    main()
