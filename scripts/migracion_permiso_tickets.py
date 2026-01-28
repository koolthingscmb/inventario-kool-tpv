"""Migración idempotente para añadir la columna `permiso_tickets` a la tabla `usuarios`.

Añade la columna INTEGER DEFAULT 0 si no existe ya.
Usa `database.connect()` del proyecto.
"""
import sqlite3
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import database


def run_migration(db_path: str = None):
    conn = None
    try:
        conn = database.connect(db_path) if db_path else database.connect()
        cur = conn.cursor()

        # Ensure usuarios table exists (if not, other migrations should create it)
        try:
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='usuarios'")
            if not cur.fetchone():
                # table missing — create with the new column included
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS usuarios (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nombre TEXT UNIQUE,
                        password TEXT,
                        rol TEXT,
                        permiso_cierre INTEGER DEFAULT 0,
                        permiso_descuento INTEGER DEFAULT 0,
                        permiso_devolucion INTEGER DEFAULT 0,
                        permiso_configuracion INTEGER DEFAULT 0,
                        permiso_tickets INTEGER DEFAULT 0
                    )
                ''')
        except Exception:
            pass

        # Check if column permiso_tickets exists
        try:
            cur.execute("PRAGMA table_info(usuarios)")
            cols = [r[1] for r in cur.fetchall()]
        except Exception:
            cols = []

        if 'permiso_tickets' not in cols:
            try:
                cur.execute('ALTER TABLE usuarios ADD COLUMN permiso_tickets INTEGER DEFAULT 0')
            except Exception:
                pass

        # Ensure admins get default 1 (for existing admins, set permiso_tickets=1 if rol='admin' and permiso_tickets IS NULL OR 0)
        try:
            cur.execute("UPDATE usuarios SET permiso_tickets=1 WHERE rol='admin' AND (permiso_tickets IS NULL OR permiso_tickets=0)")
        except Exception:
            pass

        try:
            conn.commit()
        except Exception:
            pass

        print('Migración permiso_tickets aplicada (idempotente).')
    except Exception as e:
        print('Error durante migración permiso_tickets:', e)
    finally:
        try:
            if conn:
                conn.close()
        except Exception:
            pass


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Añadir columna permiso_tickets a usuarios (idempotente)')
    parser.add_argument('--db', help='Ruta a la base de datos SQLite (opcional)')
    args = parser.parse_args()
    run_migration(args.db)
