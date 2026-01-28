#!/usr/bin/env python3
"""
scripts/migracion_cierres_avanzados.py

Añade columnas avanzadas a la tabla `cierres_caja` de forma idempotente.

Uso: ejecutar desde el entorno del proyecto:
    python scripts/migracion_cierres_avanzados.py
"""
from database import connect

TABLE_NAME = 'cierres_caja'
COLUMNS_TO_ADD = [
    ('puntos_ganados', 'REAL'),
    ('puntos_canjeados', 'REAL'),
    ('total_efectivo', 'REAL'),
    ('total_tarjeta', 'REAL'),
]


def table_exists(conn, name):
    cur = conn.cursor()
    try:
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,))
        return cur.fetchone() is not None
    finally:
        try:
            cur.close()
        except Exception:
            pass


def existing_columns(conn, table):
    cur = conn.cursor()
    try:
        cur.execute(f"PRAGMA table_info('{table}')")
        rows = cur.fetchall()
        # PRAGMA table_info returns rows where column name is at index 1
        return {r[1] for r in rows}
    finally:
        try:
            cur.close()
        except Exception:
            pass


def add_column(conn, table, column, coltype):
    cur = conn.cursor()
    try:
        sql = f"ALTER TABLE {table} ADD COLUMN {column} {coltype} DEFAULT 0.0"
        cur.execute(sql)
        conn.commit()
    finally:
        try:
            cur.close()
        except Exception:
            pass


def main():
    conn = connect()
    try:
        if not table_exists(conn, TABLE_NAME):
            print(f"Tabla '{TABLE_NAME}' no encontrada. No se realiza ninguna modificación.")
            return

        exist = existing_columns(conn, TABLE_NAME)
        added = []
        for col, ctype in COLUMNS_TO_ADD:
            if col in exist:
                continue
            try:
                add_column(conn, TABLE_NAME, col, ctype)
                added.append(col)
                # refresh existence set to avoid potential collisions in the same run
                exist.add(col)
            except Exception as e:
                print(f"Error añadiendo columna '{col}': {e}")

        if added:
            print(f"Columnas añadidas a '{TABLE_NAME}': {', '.join(added)}")
        else:
            print(f"No se añadieron columnas. Todas las columnas ya existían en '{TABLE_NAME}'.")

    finally:
        try:
            conn.close()
        except Exception:
            pass


if __name__ == '__main__':
    main()
