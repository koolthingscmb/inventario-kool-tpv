#!/usr/bin/env python3
"""
Audit SQL schema & integrity for kool_bd.db
Genera:
 - listado tablas + columns (tipo declarado)
 - columnas con tipo REAL
 - foreign keys por tabla
 - conteo de filas por tabla
 - conteo de registros huérfanos por FK (si posible)
 - evaluación sobre viabilidad de migración monetaria (centavos)
"""
import sqlite3
import sys
from collections import defaultdict

DB_PATH = sys.argv[1] if len(sys.argv) > 1 else "kool_tpv/base_datos/kool_bd.db"

def get_tables(conn):
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
    return [r[0] for r in cur.fetchall()]

def pragma_table_info(conn, table):
    cur = conn.execute(f"PRAGMA table_info('{table}')")
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]

def pragma_foreign_key_list(conn, table):
    cur = conn.execute(f"PRAGMA foreign_key_list('{table}')")
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]

def count_rows(conn, table):
    try:
        return conn.execute(f"SELECT COUNT(*) FROM '{table}'").fetchone()[0]
    except Exception:
        return None

def orphan_count_for_fk(conn, child_table, fk):
    parent = fk['table']
    child_col = fk['from']
    parent_col = fk['to']
    try:
        q = f"SELECT COUNT(*) FROM {child_table} WHERE {child_col} IS NOT NULL AND {child_col} NOT IN (SELECT {parent_col} FROM {parent})"
        return conn.execute(q).fetchone()[0]
    except Exception:
        return None

def analyze(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = None
    report_lines = []
    report_lines.append(f"DB PATH: {db_path}")
    tables = get_tables(conn)
    report_lines.append(f"Found {len(tables)} tables\n")

    monetary_candidates = []
    fk_map = defaultdict(list)

    for t in tables:
        report_lines.append(f"--- TABLE: {t} ---")
        tinfo = pragma_table_info(conn, t)
        if not tinfo:
            report_lines.append("  (no columns returned or table inaccessible)")
            continue
        for col in tinfo:
            cname = col['name']
            ctype = (col['type'] or '').upper()
            nn = col.get('notnull',0)
            dflt = col.get('dflt_value')
            pk = col.get('pk',0)
            report_lines.append(f"  - {cname} : {ctype}  NOTNULL={nn}  PK={pk}  DEFAULT={dflt}")
            if 'REAL' in ctype or cname.lower() in ('total','subtotal','precio','importe','coste','pvp','pagado','cambio','importe_efectivo','importe_tarjeta','descuento_euros','puntos','puntos_mov','tesoro_total','tesoro_ganado','tesoro_gastado'):
                monetary_candidates.append((t, cname, ctype))
        fks = pragma_foreign_key_list(conn, t)
        if fks:
            report_lines.append("  Foreign Keys:")
            for fk in fks:
                fk_map[t].append(fk)
                report_lines.append(f"    - child_col={fk['from']} -> parent={fk['table']}.{fk['to']} (on_update={fk.get('on_update')}, on_delete={fk.get('on_delete')})")
        cnt = count_rows(conn, t)
        report_lines.append(f"  Rows: {cnt}")
        report_lines.append("")

    report_lines.append("\n=== MONETARY-LIKE COLUMNS (by declared TYPE or name heuristic) ===")
    for t,c,typ in monetary_candidates:
        report_lines.append(f"- {t}.{c}  declared_type={typ}")

    report_lines.append("\n=== ORPHAN CHECKS (per FK) ===")
    for child, fks in fk_map.items():
        for fk in fks:
            orphan = orphan_count_for_fk(conn, child, fk)
            report_lines.append(f"- {child}.{fk['from']} -> {fk['table']}.{fk['to']} : orphan_count = {orphan}")

    report_lines.append("\n=== TABLES DECLARING REAL (monetary risk) ===")
    tables_with_real = set()
    for t,c,typ in monetary_candidates:
        if 'REAL' in (typ or '').upper() or typ=='':
            tables_with_real.add(t)
    for t in sorted(tables_with_real):
        report_lines.append(f"- {t}")

    conn.close()
    return "\n".join(report_lines)

if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser(description='Audit kool_bd.db schema and integrity')
    p.add_argument('db', nargs='?', default=DB_PATH, help='Path to sqlite DB')
    args = p.parse_args()
    out = analyze(args.db)
    print(out)
