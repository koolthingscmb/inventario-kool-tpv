#!/usr/bin/env python3
"""Migración: añadir columna `puntos_total_momento` a la tabla `tickets`.

- Añade `puntos_total_momento` (REAL).
- Idempotente: comprueba PRAGMA table_info('tickets') antes de ALTER TABLE.
- Usa `database.connect()` para conectar.
"""

from database import connect


def _table_exists(cur, name):
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,))
    return cur.fetchone() is not None


def _get_table_columns(cur, name):
    cur.execute(f"PRAGMA table_info('{name}')")
    return [r[1] for r in cur.fetchall()]


def main():
    conn = None
    try:
        conn = connect()
        cur = conn.cursor()

        if not _table_exists(cur, 'tickets'):
            print("Tabla 'tickets' no encontrada en la base de datos.")
            return

        cols = _get_table_columns(cur, 'tickets')

        col_name = 'puntos_total_momento'
        col_type = 'REAL'

        if col_name in cols:
            print(f"La columna '{col_name}' ya existe. No se realizarán cambios.")
            return

        sql = f"ALTER TABLE tickets ADD COLUMN {col_name} {col_type}"
        try:
            cur.execute(sql)
            conn.commit()
            print(f"Añadida columna: {col_name} {col_type}")
        except Exception as e:
            print(f"Error añadiendo columna {col_name}: {e}")
            try:
                conn.rollback()
            except Exception:
                pass

    except Exception as e:
        print("Error durante la migración:", e)
    finally:
        try:
            if conn:
                conn.close()
        except Exception:
            pass


if __name__ == '__main__':
    main()
