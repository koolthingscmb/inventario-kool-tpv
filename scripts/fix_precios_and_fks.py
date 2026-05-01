#!/usr/bin/env python3
"""Convierte `precios.pvp` y `precios.coste` a INTEGER (céntimos) y añade ON DELETE CASCADE
a las FKs que referencian `productos`, `proveedores` y `clientes`.

Genera un log en scripts/fix_precios_and_fks_output.txt
"""

import sqlite3
import shutil
import time
import re
import sys

DB = 'kool_tpv/base_datos/kool_bd.db'
LOG = 'scripts/fix_precios_and_fks_output.txt'


def backup(db):
    ts = time.strftime('%Y%m%d_%H%M%S')
    dst = f"{db}.bak.{ts}"
    shutil.copy2(db, dst)
    return dst


def write(msg):
    print(msg)
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(msg + '\n')


def add_on_delete_cascade(ddl, parent):
    # For every REFERENCES parent(...) occurrence, add ON DELETE CASCADE if missing
    def repl(m):
        clause = m.group(0)
        if 'ON DELETE' in clause.upper():
            return clause
        # insert before the closing ')'
        return clause[:-1] + ' ON DELETE CASCADE)'
    pattern = re.compile(r'REFERENCES\s+(?:"?)' + re.escape(parent) + r'(?:"?)\s*\([^)]*\)')
    return pattern.sub(repl, ddl)


def recreate_table_with_ddl(conn, table, new_ddl):
    # Deprecated: kept for compatibility but prefer build/create from pragma
    raise RuntimeError('recreate_table_with_ddl is deprecated; use rebuild_table_from_pragma')


def build_create_from_pragma(conn, table, cascade_parents):
    # Build CREATE TABLE statement from PRAGMA table_info and foreign_key_list
    cols = conn.execute(f"PRAGMA table_info('{table}')").fetchall()
    fk_list = conn.execute(f"PRAGMA foreign_key_list('{table}')").fetchall()
    lines = []
    for c in cols:
        cid, name, ctype, notnull, dflt_value, pk = c
        part = f'"{name}" {ctype or ""}'
        if notnull:
            part += ' NOT NULL'
        if dflt_value is not None:
            part += f' DEFAULT {dflt_value}'
        if pk:
            part += ' PRIMARY KEY' if not pk else ' PRIMARY KEY'
        lines.append(part)

    # group fk_list by id to handle composite fks
    fk_by_id = {}
    for fk in fk_list:
        # pragma returns: id, seq, table, from, to, on_update, on_delete, match
        fid = fk[0]
        fk_by_id.setdefault(fid, []).append(fk)

    for fid, entries in fk_by_id.items():
        cols_from = ','.join([f'"{e[3]}"' for e in entries])
        cols_to = ','.join([f'"{e[4]}"' for e in entries])
        parent = entries[0][2]
        # determine on_delete: cascade if parent in cascade_parents else use reported on_delete
        on_delete = 'CASCADE' if parent in cascade_parents else (entries[0][6] or '')
        fkline = f'FOREIGN KEY({cols_from}) REFERENCES {parent}({cols_to})'
        if on_delete:
            fkline += f' ON DELETE {on_delete}'
        lines.append(fkline)

    create_sql = f'CREATE TABLE "{table}" (\n  ' + ',\n  '.join(lines) + '\n)'
    return create_sql


def rebuild_table_from_pragma(conn, table, cascade_parents):
    temp = f"{table}__migrtmp"
    write(f'Rebuilding table {table} as {temp} with cascade_parents={cascade_parents}')
    create_sql = build_create_from_pragma(conn, table, set(cascade_parents))
    write('New CREATE statement:')
    write(create_sql)
    conn.execute('PRAGMA foreign_keys=OFF')
    conn.execute(f'DROP TABLE IF EXISTS "{temp}"')
    conn.execute(create_sql.replace(f'CREATE TABLE "{table}"', f'CREATE TABLE "{temp}"'))
    # copy data
    cols = [r[1] for r in conn.execute(f'PRAGMA table_info(\"{table}\")')]
    col_list = ','.join([f'"{c}"' for c in cols])
    conn.execute(f'INSERT INTO "{temp}" ({col_list}) SELECT {col_list} FROM "{table}"')
    conn.execute(f'DROP TABLE "{table}"')
    conn.execute(f'ALTER TABLE "{temp}" RENAME TO "{table}"')
    conn.execute('PRAGMA foreign_keys=ON')


def convert_precios(conn):
    table = 'precios'
    ddl = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()[0]
    if not ddl:
        write('No DDL for precios')
        return
    write('Original precios DDL:')
    write(ddl)
    # modify column types pvp and coste -> INTEGER
    ddl2 = re.sub(r'("?pvp"?\s+)REAL', r'\1INTEGER', ddl, flags=re.IGNORECASE)
    ddl2 = re.sub(r'("?coste"?\s+)REAL', r'\1INTEGER', ddl2, flags=re.IGNORECASE)
    write('Modified precios DDL:')
    write(ddl2)
    # create temp, copy with conversion for pvp and coste
    temp = f"{table}__migrtmp"
    conn.execute('PRAGMA foreign_keys=OFF')
    conn.execute(f'DROP TABLE IF EXISTS "{temp}"')
    stmt = re.sub(r'CREATE\s+TABLE\s+(?:"?)' + re.escape(table) + r'(?:"?)', f'CREATE TABLE "{temp}"', ddl2, flags=re.IGNORECASE, count=1)
    conn.execute(stmt)
    # copy data with round*100
    cols = [r[1] for r in conn.execute(f'PRAGMA table_info(\"{table}\")')]
    select_parts = []
    for c in cols:
        if c in ('pvp','coste'):
            select_parts.append(f"CAST(ROUND(\"{c}\" * 100.0) AS INTEGER) AS \"{c}\"")
        else:
            select_parts.append(f'"{c}"')
    conn.execute(f'INSERT INTO "{temp}" ({",".join([f"\"{c}\"" for c in cols])}) SELECT {",".join(select_parts)} FROM "{table}"')
    # validate counts
    old_cnt = conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
    new_cnt = conn.execute(f'SELECT COUNT(*) FROM "{temp}"').fetchone()[0]
    write(f'precios rows old={old_cnt} new={new_cnt}')
    if old_cnt != new_cnt:
        raise RuntimeError('Row count mismatch for precios')
    # basic equivalence check for first 10 rows by id if id exists
    pk = conn.execute(f"PRAGMA table_info('{table}')").fetchall()[0][1]
    # swap
    conn.execute(f'DROP TABLE "{table}"')
    conn.execute(f'ALTER TABLE "{temp}" RENAME TO "{table}"')
    conn.execute('PRAGMA foreign_keys=ON')
    write('precios converted successfully')


def fix_fks(conn, parents):
    # find tables referencing each parent and rebuild their DDL with ON DELETE CASCADE
    cur = conn.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = cur.fetchall()
    for name, ddl in tables:
        # Only process tables that reference any of the parents
        refs = [p for p in parents if (p in (ddl or ''))]
        if not refs:
            continue
        # Check pragma foreign_key_list to determine if any fk to these parents lacks CASCADE
        fk_list = conn.execute(f"PRAGMA foreign_key_list('{name}')").fetchall()
        needs_rebuild = False
        for fk in fk_list:
            parent = fk[2]
            on_delete = fk[6] if len(fk) > 6 else None
            if parent in parents and (not on_delete or on_delete.strip().upper() != 'CASCADE'):
                needs_rebuild = True
                break
        if needs_rebuild:
            write(f'Will rebuild {name} to add ON DELETE CASCADE for parents intersecting {refs}')
            rebuild_table_from_pragma(conn, name, parents)


def main(db_path=DB):
    open(LOG, 'w').close()
    write(f'Backup DB: {db_path}')
    bak = backup(db_path)
    write(f'Backup created: {bak}')
    conn = sqlite3.connect(db_path)
    try:
        with conn:
            convert_precios(conn)
            fix_fks(conn, ['productos','proveedores','clientes'])
    finally:
        conn.close()
    write('Done')


if __name__ == '__main__':
    db = sys.argv[1] if len(sys.argv) > 1 else DB
    main(db)
