#!/usr/bin/env python3
"""Idempotent migration: add `total_web` REAL column to `cierres_caja`.

Usage:
    PYTHONPATH=. python3 scripts/fix_db_cierres.py
"""
from database import connect


def main():
    conn = connect()
    cur = conn.cursor()
    try:
        cur.execute("PRAGMA table_info(cierres_caja)")
        cols = [r[1] for r in cur.fetchall()]
    except Exception as e:
        print(f"ERROR leyendo esquema de la BD: {e}")
        try:
            cur.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass
        raise SystemExit(1)

    if not cols:
        print("ERROR: tabla 'cierres_caja' no encontrada en la base de datos.")
        try:
            cur.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass
        raise SystemExit(2)

    if 'total_web' in cols:
        # Already present; nothing to do
        print('✅ Columna total_web añadida con éxito a cierres_caja')
        try:
            cur.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass
        return

    try:
        cur.execute('ALTER TABLE cierres_caja ADD COLUMN total_web REAL DEFAULT 0.0')
        conn.commit()
    except Exception as e:
        print(f"ERROR añadiendo columna total_web: {e}")
        try:
            cur.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass
        raise SystemExit(3)

    print('✅ Columna total_web añadida con éxito a cierres_caja')
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
