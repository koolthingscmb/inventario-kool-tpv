#!/usr/bin/env python3
"""Migración para crear `niveles_fidelidad` y relacionarla con `clientes`.

Operaciones:
- Crear tabla `niveles_fidelidad` si no existe.
- Insertar filas iniciales si la tabla está vacía.
- Alterar/rehacer la tabla `clientes` para añadir `id_nivel` y renombrar
  columnas: `puntos_fidelidad` -> `tesoro_total`, `total_gastado` -> `tesoro_gastado_total`,
  `puntos_activados` -> `fidelidad_activa`.

La migración es lo más idempotente posible: detecta el estado actual y actúa
con cuidado para no perder datos.
"""
import sqlite3
import sys
from database import connect


def ensure_niveles_table(conn: sqlite3.Connection):
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS niveles_fidelidad (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            level INTEGER NOT NULL UNIQUE,
            nombre_nivel TEXT NOT NULL,
            grafismo_nivel TEXT,
            gasto_minimo REAL NOT NULL DEFAULT 0.0
        )
    ''')
    conn.commit()

    # Insert defaults if empty
    cur.execute('SELECT COUNT(1) FROM niveles_fidelidad')
    count = cur.fetchone()[0]
    if count == 0:
        cur.executemany(
            'INSERT INTO niveles_fidelidad (level, nombre_nivel, grafismo_nivel, gasto_minimo) VALUES (?, ?, ?, ?)',
            [
                (1, 'Errante sombrío', '///', 0.0),
                (2, 'Guardián del Tesoro', '/////', 100.0),
                (3, 'Maestro del Tesoro', '//////', 300.0),
                (4, 'Señor del Oro', '///////', 600.0),
            ]
        )
        conn.commit()
    cur.close()


def table_columns(conn: sqlite3.Connection, table: str):
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    cols = [(r[1], r[2]) for r in cur.fetchall()]
    cur.close()
    return cols


def migrar_clientes(conn: sqlite3.Connection):
    cur = conn.cursor()
    # Ensure clients table exists (if not, create minimal compatible table)
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='clientes'")
    if not cur.fetchone():
        cur.execute('''
            CREATE TABLE clientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                telefono TEXT,
                email TEXT,
                dni TEXT,
                direccion TEXT,
                ciudad TEXT,
                cp TEXT,
                tags TEXT,
                puntos_fidelidad REAL DEFAULT 0,
                total_gastado REAL DEFAULT 0.0,
                notas_internas TEXT,
                fecha_alta TEXT
            )
        ''')
        conn.commit()

    cols = table_columns(conn, 'clientes')
    col_names = [c[0] for c in cols]

    # If id_nivel already exists and target columns already exist, we're done
    needs_rebuild = False
    target_cols = ['tesoro_total', 'tesoro_gastado_total', 'fidelidad_activa', 'id_nivel']
    for tc in target_cols:
        if tc not in col_names:
            needs_rebuild = True
            break

    if not needs_rebuild:
        print('clientes table already has target columns; skipping rebuild.')
        cur.close()
        return True

    # Build new clientes table with desired schema
    # We'll preserve existing columns where possible and map old names to new ones
    try:
        # Create temporary table with new schema
        cur.execute('''
            CREATE TABLE IF NOT EXISTS clientes_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                telefono TEXT,
                email TEXT,
                dni TEXT,
                direccion TEXT,
                ciudad TEXT,
                cp TEXT,
                tags TEXT,
                tesoro_total REAL DEFAULT 0.0,
                tesoro_gastado_total REAL DEFAULT 0.0,
                fidelidad_activa INTEGER DEFAULT 0,
                notas_internas TEXT,
                fecha_alta TEXT,
                id_nivel INTEGER DEFAULT NULL,
                FOREIGN KEY (id_nivel) REFERENCES niveles_fidelidad(id)
            )
        ''')
        conn.commit()

        # Copy data from old to new mapping columns when present
        # Build select list with fallback defaults
        select_cols = []
        # nombre
        select_cols.append('COALESCE(nombre, "") AS nombre')
        for c in ['telefono', 'email', 'dni', 'direccion', 'ciudad', 'cp', 'tags']:
            if c in col_names:
                select_cols.append(c)
            else:
                select_cols.append('NULL AS %s' % c)

        # puntos_fidelidad -> tesoro_total
        if 'puntos_fidelidad' in col_names:
            select_cols.append('CAST(puntos_fidelidad AS REAL) AS tesoro_total')
        else:
            select_cols.append('0.0 AS tesoro_total')

        # total_gastado -> tesoro_gastado_total
        if 'total_gastado' in col_names:
            select_cols.append('CAST(total_gastado AS REAL) AS tesoro_gastado_total')
        else:
            select_cols.append('0.0 AS tesoro_gastado_total')

        # puntos_activados -> fidelidad_activa
        if 'puntos_activados' in col_names:
            select_cols.append('CASE WHEN COALESCE(puntos_activados,0)<>0 THEN 1 ELSE 0 END AS fidelidad_activa')
        else:
            select_cols.append('0 AS fidelidad_activa')

        # notas_internas, fecha_alta
        if 'notas_internas' in col_names:
            select_cols.append('notas_internas')
        else:
            select_cols.append('NULL AS notas_internas')
        if 'fecha_alta' in col_names:
            select_cols.append('fecha_alta')
        else:
            select_cols.append('NULL AS fecha_alta')

        # id_nivel: try to preserve if exists
        if 'id_nivel' in col_names:
            select_cols.append('id_nivel')
        else:
            select_cols.append('NULL AS id_nivel')

        select_sql = ', '.join(select_cols)
        insert_sql = f'INSERT INTO clientes_new (nombre, telefono, email, dni, direccion, ciudad, cp, tags, tesoro_total, tesoro_gastado_total, fidelidad_activa, notas_internas, fecha_alta, id_nivel) SELECT {select_sql} FROM clientes'

        cur.execute('BEGIN')
        cur.execute(insert_sql)
        cur.execute('COMMIT')

        # Drop old table and rename new
        cur.execute('ALTER TABLE clientes RENAME TO clientes_old')
        cur.execute('ALTER TABLE clientes_new RENAME TO clientes')
        conn.commit()

        # Optionally keep clientes_old for backup; we leave it as is.
        print('Clientes table rebuilt to include niveles_fidelidad relation and renamed columns.')
        cur.close()
        return True
    except Exception as e:
        conn.rollback()
        print('Error migrating clientes table:', e)
        cur.close()
        return False


if __name__ == '__main__':
    db = None
    try:
        arg = sys.argv[1] if len(sys.argv) > 1 else None
        if arg:
            db = connect(arg)
        else:
            db = connect()
        ok = True
        ensure_niveles_table(db)
        ok = migrar_clientes(db) and ok
        if ok:
            print('Migración niveles_fidelidad completada correctamente.')
            sys.exit(0)
        else:
            print('Migración niveles_fidelidad falló.')
            sys.exit(2)
    finally:
        try:
            if db:
                db.close()
        except Exception:
            pass
