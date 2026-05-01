#!/usr/bin/env python3
"""Genera un informe de estado final de kool_bd.db:
- Lista columnas declaradas REAL sospechosas de contener valores monetarios.
- Lista FKs que NO declaran ON DELETE CASCADE entre tablas dependientes y padres.

Salida: scripts/certify_db_state_report.txt
"""

import sqlite3
import sys
import re

DB = 'kool_tpv/base_datos/kool_bd.db'
OUT = 'scripts/certify_db_state_report.txt'

MONETARY_NAME_HEURISTIC = ['precio', 'coste', 'total', 'iva', 'descuento', 'tesoro', 'importe', 'pvp']


def is_monetary_name(col):
    name = col.lower()
    return any(name == h or name.endswith('_'+h) or h in name for h in MONETARY_NAME_HEURISTIC)


def main(db_path=DB):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
    tables = cur.fetchall()

    real_columns = []
    fk_without_cascade = []

    for row in tables:
        t = row['name']
        ddl = row['sql'] or ''
        info = conn.execute(f"PRAGMA table_info('{t}')").fetchall()
        for col in info:
            cname = col['name']
            ctype = (col['type'] or '').upper()
            if ctype.startswith('REAL') or ctype == 'REAL':
                # only report if heuristic suspects monetary
                if is_monetary_name(cname):
                    real_columns.append((t, cname, col['type']))
            else:
                # still flag if name suggests monetary but type not INTEGER
                if is_monetary_name(cname) and not ctype.startswith('INT') and ctype != 'INTEGER':
                    real_columns.append((t, cname, col['type'] or '<empty>'))

        # check FKs via pragma
        fk_list = conn.execute(f"PRAGMA foreign_key_list('{t}')").fetchall()
        for fk in fk_list:
            parent = fk['table']
            on_delete = fk['on_delete'] if 'on_delete' in fk.keys() else None
            # Some sqlite versions return '' instead of None
            has_cascade = False
            if on_delete and on_delete.strip().upper() == 'CASCADE':
                has_cascade = True
            else:
                # fallback: check DDL text for cascade mention between t and parent
                pattern = re.compile(r"FOREIGN KEY\s*\([^)]*\)\s*REFERENCES\s+" + re.escape(parent) + r"[^(]*ON\s+DELETE\s+CASCADE", re.IGNORECASE)
                if pattern.search(ddl or ''):
                    has_cascade = True
            if not has_cascade:
                fk_without_cascade.append((t, fk['from'], parent, on_delete))

    # write report
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write('DB PATH: ' + db_path + '\n')
        f.write('\n=== MONETARY-LIKE COLUMNS STILL NOT INTEGER OR SUSPICIOUS ===\n')
        if not real_columns:
            f.write('None detected. All monetary-like columns appear INTEGER or acceptable types.\n')
        else:
            for t, c, ctype in real_columns:
                f.write(f'- {t}.{c} declared_type={ctype}\n')

        f.write('\n=== FOREIGN KEYS WITHOUT ON DELETE CASCADE (child.table, child_col -> parent) ===\n')
        if not fk_without_cascade:
            f.write('None detected. All FKs to parents include ON DELETE CASCADE where applicable.\n')
        else:
            for t, child_col, parent, on_delete in fk_without_cascade:
                f.write(f'- {t}.{child_col} -> {parent}  on_delete={on_delete}\n')

        f.write('\n=== DDL CHECK (per-table CREATE statements) ===\n')
        for row in tables:
            t = row['name']
            f.write(f'--- TABLE: {t} ---\n')
            f.write((row['sql'] or '').strip() + '\n\n')

    conn.close()
    print(f'Report written to {OUT}')


if __name__ == '__main__':
    db = sys.argv[1] if len(sys.argv) > 1 else DB
    main(db)
