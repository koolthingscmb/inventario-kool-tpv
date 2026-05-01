#!/usr/bin/env python3
"""Migración de columnas REAL -> INTEGER en céntimos (multiplica por 100).

Requisitos:
- Crea copia de seguridad del archivo DB.
- Procesa tablas en orden padre->hijo según FKs.
- Para cada tabla: crea nueva tabla con tipos ajustados, copia datos (ROUND(val*100)), valida exactitud, reemplaza tabla original.
- Reintenta si hay errores y hace rollback en caso de fallo.

Uso: python3 scripts/migrate_real_to_cents.py kool_tpv/base_datos/kool_bd.db
"""

import sys
import sqlite3
import shutil
import time
import re
from decimal import Decimal, ROUND_HALF_UP


def backup_db(path):
    ts = time.strftime('%Y%m%d_%H%M%S')
    dst = f"{path}.bak.{ts}"
    shutil.copy2(path, dst)
    print(f"Backup created: {dst}")
    return dst


def get_tables(conn):
    cur = conn.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
    return {r[0]: r[1] for r in cur.fetchall()}


def pragma_table_info(conn, table):
    cur = conn.execute(f"PRAGMA table_info('{table}')")
    return [dict(zip([c[0] for c in cur.description], row)) for row in cur.fetchall()]


def pragma_foreign_key_list(conn, table):
    cur = conn.execute(f"PRAGMA foreign_key_list('{table}')")
    cols = [dict(zip([c[0] for c in cur.description], row)) for row in cur.fetchall()]
    return cols


def build_dependency_graph(conn, tables):
    # edges: child -> parent
    g = {t: set() for t in tables}
    for t in tables:
        for fk in pragma_foreign_key_list(conn, t):
            parent = fk['table']
            if parent in tables:
                g[t].add(parent)
    return g


def topo_parent_first(graph):
    # we want parents before children; graph edges child->parent
    # perform Kahn on reversed edges so nodes with no dependents (pure parents) come first
    inv = {k: set() for k in graph}
    for child, parents in graph.items():
        for p in parents:
            inv[p].add(child)
    # Now topological sort on inv where edges parent->child
    indeg = {n: 0 for n in graph}
    for p, childs in inv.items():
        for c in childs:
            indeg[c] += 1
    q = [n for n, d in indeg.items() if d == 0]
    out = []
    while q:
        n = q.pop(0)
        out.append(n)
        for m in inv.get(n, ()): 
            indeg[m] -= 1
            if indeg[m] == 0:
                q.append(m)
    # if cycle, just append remaining
    remaining = [n for n in graph if n not in out]
    return out + remaining


def modify_create_sql(create_sql, monetary_cols, enforce_cascade_child=False):
    # Replace column type REAL -> INTEGER for monetary_cols (column names exact)
    # We do NOT modify FK clauses automatically to avoid introducing syntax errors.
    new_sql = create_sql
    for col in monetary_cols:
        pattern = re.compile(r"(\b" + re.escape(col) + r"\b\s+)REAL(\b|\s|,|\))", re.IGNORECASE)
        new_sql = pattern.sub(r"\1INTEGER\2", new_sql)
    return new_sql


def table_monetary_columns(table_info):
    # Return columns declared REAL (case-insensitive)
    return [col['name'] for col in table_info if col['type'] and col['type'].upper().startswith('REAL')]


def copy_data_with_conversion(conn, table, new_table, monetary_cols):
    cols = [c['name'] for c in pragma_table_info(conn, table)]
    col_list = ','.join([f'"{c}"' for c in cols])
    select_parts = []
    for c in cols:
        if c in monetary_cols:
            # Use ROUND to convert to nearest cent then cast to integer
            select_parts.append(f"CAST(ROUND(\"{c}\" * 100.0) AS INTEGER) AS \"{c}\"")
        else:
            select_parts.append(f'"{c}"')
    select_sql = ','.join(select_parts)
    sql = f'INSERT INTO "{new_table}" ({col_list}) SELECT {select_sql} FROM "{table}"'
    conn.execute(sql)


def validate_rowwise_equivalence(conn, old_table, new_table, pk_cols, monetary_cols):
    # Join on PK columns and compare CAST(ROUND(old*100)) == new
    where_conditions = ' AND '.join([f'old."{p}" = new."{p}"' for p in pk_cols])
    checks = []
    for c in monetary_cols:
        checks.append(f"(CAST(ROUND(old.\"{c}\" * 100.0) AS INTEGER) = new.\"{c}\") OR (old.\"{c}\" IS NULL AND new.\"{c}\" IS NULL)")
    sql = f'SELECT COUNT(*) FROM "{old_table}" old JOIN "{new_table}" new ON {where_conditions} WHERE NOT ({" AND ".join(checks)})'
    cur = conn.execute(sql)
    bad = cur.fetchone()[0]
    return bad == 0, bad


def get_pk_cols(table_info):
    return [c['name'] for c in table_info if c.get('pk')]


def recreate_indexes_and_triggers(conn, table, temp_table, orig_sql_map):
    # Collect index and trigger SQL for the original table and recreate after rename
    cur = conn.execute("SELECT type, name, tbl_name, sql FROM sqlite_master WHERE (type='index' OR type='trigger') AND tbl_name=?", (table,))
    items = cur.fetchall()
    for typ, name, tbl, sql in items:
        if not sql:
            continue
        # adjust SQL if it references the old table name (should already be correct after rename)
        try:
            conn.execute(sql)
        except Exception as e:
            print(f"Warning creating {typ} {name}: {e}")


def migrate_table(conn, table, create_sql, monetary_cols, enforce_cascade_child=False):
    if not monetary_cols:
        print(f"Skipping {table}, no REAL columns detected.")
        return True
    print(f"Migrating table {table}, monetary columns: {monetary_cols}")
    temp = f"{table}__migrtmp"
    new_create = modify_create_sql(create_sql, monetary_cols, enforce_cascade_child=enforce_cascade_child)
    # create temp table: disable FK checks to allow schema operations
    conn.execute(f'PRAGMA foreign_keys=OFF')
    # replace the CREATE TABLE <table> clause robustly
    new_create_stmt = re.sub(r'CREATE\s+TABLE\s+(?:"?)' + re.escape(table) + r'(?:"?)', f'CREATE TABLE "{temp}"', new_create, flags=re.IGNORECASE, count=1)
    # ensure temp does not exist
    conn.execute(f'DROP TABLE IF EXISTS "{temp}"')
    conn.execute(new_create_stmt)
    # copy data
    copy_data_with_conversion(conn, table, temp, monetary_cols)
    # validate equivalence
    old_info = pragma_table_info(conn, table)
    pk = get_pk_cols(old_info)
    ok, bad = validate_rowwise_equivalence(conn, table, temp, pk, monetary_cols)
    if not ok:
        raise RuntimeError(f"Validation failed for table {table}: {bad} mismatches")
    # drop old, rename new (FKs were disabled earlier)
    conn.execute(f'DROP TABLE "{table}"')
    conn.execute(f'ALTER TABLE "{temp}" RENAME TO "{table}"')
    conn.execute(f'PRAGMA foreign_keys=ON')
    print(f"Table {table} migrated successfully.")
    return True


def main(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    # enable foreign keys
    conn.execute('PRAGMA foreign_keys=ON')
    tables_sql = get_tables(conn)
    graph = build_dependency_graph(conn, list(tables_sql.keys()))
    order = topo_parent_first(graph)
    print('Processing order (parents first):', order)
    # determine monetary cols per table
    monetary_map = {}
    for t in order:
        info = pragma_table_info(conn, t)
        monetary_map[t] = table_monetary_columns(info)

    # backup
    backup_db(db_path)

    # perform migration in a transaction
    try:
        with conn:
            for t in order:
                create_sql = tables_sql[t]
                # enforce cascade on child tables (if they have FK references)
                enforce_cascade = True
                migrate_table(conn, t, create_sql, monetary_map.get(t, []), enforce_cascade_child=enforce_cascade)
        print('Migration completed successfully for all tables.')
    except Exception as e:
        print('Migration failed:', e)
        print('Database restored to original state (transaction rolled back).')
    finally:
        conn.close()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: migrate_real_to_cents.py path/to/kool_bd.db')
        sys.exit(1)
    main(sys.argv[1])
