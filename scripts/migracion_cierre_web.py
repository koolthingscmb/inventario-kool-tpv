#!/usr/bin/env python3
"""Migración: añadir columna `total_web` (REAL) a la tabla `cierres_caja`.

Idempotente: comprueba PRAGMA table_info(cierres_caja) y sólo añade la columna si no existe.
"""
from database import connect


def main():
    conn = connect()
    cur = conn.cursor()
    try:
        cur.execute("PRAGMA table_info(cierres_caja)")
        cols = [r[1] for r in cur.fetchall()]
        if 'total_web' in cols:
            print("La columna 'total_web' ya existe en 'cierres_caja'. Ningún cambio necesario.")
            return

        # Añadir la columna con valor por defecto 0.0
        cur.execute("ALTER TABLE cierres_caja ADD COLUMN total_web REAL DEFAULT 0.0")
        conn.commit()
        print("Migración 'total_web' aplicada correctamente (idempotente).")
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        print("Error aplicando migración 'total_web':", e)
    finally:
        try:
            cur.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass


if __name__ == '__main__':
    main()
