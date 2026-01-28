"""Migración idempotente para añadir clave de contraseña global de configuración.

Inserta la entrada 'config_pass_global' con valor '1234' en la tabla `configuracion`.
Usa `INSERT OR IGNORE` para no sobrescribir si ya existe.
"""
import sqlite3
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import database


def ensure_config_key(conn: sqlite3.Connection, key: str, value: str):
    cur = conn.cursor()
    try:
        cur.execute('''
            CREATE TABLE IF NOT EXISTS configuracion (
                clave TEXT PRIMARY KEY,
                valor TEXT
            )
        ''')
    except Exception:
        pass

    try:
        cur.execute('INSERT OR IGNORE INTO configuracion (clave, valor) VALUES (?, ?)', (key, value))
    except Exception:
        pass


def run_migration(db_path: str = None):
    conn = None
    try:
        conn = database.connect(db_path) if db_path else database.connect()
        ensure_config_key(conn, 'config_pass_global', '1234')
        try:
            conn.commit()
        except Exception:
            pass

        print('Infraestructura para clave maestra de configuración lista.')
    except Exception as e:
        print('Error durante migración de clave de configuración:', e)
    finally:
        try:
            if conn:
                conn.close()
        except Exception:
            pass


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Migración: añadir clave config_pass_global (idempotente)')
    parser.add_argument('--db', help='Ruta a la base de datos SQLite (opcional)')
    args = parser.parse_args()
    run_migration(args.db)
