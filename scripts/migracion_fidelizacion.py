"""Script idempotente para añadir esquema de fidelización.

Este script crea/asegura:
- tabla `configuracion` (clave/valor)
- columna `fide_porcentaje` en `categorias` (crea tabla si no existe)
- columna `fide_puntos_fijos` en `productos`
- tabla `fide_promociones` para promo temporales

Usa `database.connect()` del proyecto.
"""
from typing import Dict
import sqlite3
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import database


def ensure_config_table(conn: sqlite3.Connection):
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS configuracion (
            clave TEXT PRIMARY KEY,
            valor TEXT
        )
    ''')

    defaults: Dict[str, str] = {
        'fide_activa': '1',
        'fide_porcentaje_general': '5',
        'fide_puntos_valor_euro': '1',
    }

    for k, v in defaults.items():
        try:
            cur.execute('INSERT OR IGNORE INTO configuracion (clave, valor) VALUES (?, ?)', (k, v))
        except Exception:
            pass


def ensure_categorias_table_and_column(conn: sqlite3.Connection):
    cur = conn.cursor()
    # If table doesn't exist, create it with a fide_porcentaje column
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='categorias'")
    exists = cur.fetchone()
    if not exists:
        try:
            cur.execute('''
                CREATE TABLE categorias (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT UNIQUE,
                    fide_porcentaje REAL
                )
            ''')
            return
        except Exception:
            pass

    # If it exists, ensure column fide_porcentaje
    try:
        cur.execute('PRAGMA table_info(categorias)')
        cols = [r[1] for r in cur.fetchall()]
    except Exception:
        cols = []

    if 'fide_porcentaje' not in cols:
        try:
            cur.execute('ALTER TABLE categorias ADD COLUMN fide_porcentaje REAL')
        except Exception:
            pass


def ensure_tipos_table_and_column(conn: sqlite3.Connection):
    cur = conn.cursor()
    # If table doesn't exist, create it with a fide_porcentaje column
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tipos'")
    exists = cur.fetchone()
    if not exists:
        try:
            cur.execute('''
                CREATE TABLE tipos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT UNIQUE,
                    fide_porcentaje REAL
                )
            ''')
            return
        except Exception:
            pass

    # If it exists, ensure column fide_porcentaje
    try:
        cur.execute('PRAGMA table_info(tipos)')
        cols = [r[1] for r in cur.fetchall()]
    except Exception:
        cols = []

    if 'fide_porcentaje' not in cols:
        try:
            cur.execute('ALTER TABLE tipos ADD COLUMN fide_porcentaje REAL')
        except Exception:
            pass


def ensure_product_column(conn: sqlite3.Connection):
    cur = conn.cursor()
    try:
        cur.execute('PRAGMA table_info(productos)')
        cols = [r[1] for r in cur.fetchall()]
    except Exception:
        cols = []

    if 'fide_puntos_fijos' not in cols:
        try:
            cur.execute('ALTER TABLE productos ADD COLUMN fide_puntos_fijos REAL')
        except Exception:
            pass


def ensure_promotions_table(conn: sqlite3.Connection):
    cur = conn.cursor()
    try:
        cur.execute('''
            CREATE TABLE IF NOT EXISTS fide_promociones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT,
                fecha_inicio TEXT,
                fecha_fin TEXT,
                multiplicador REAL DEFAULT 1.0,
                activa INTEGER DEFAULT 1
            )
        ''')
    except Exception:
        pass


def run_migration(db_path: str = None):
    conn = None
    try:
        conn = database.connect(db_path) if db_path else database.connect()
        cur = conn.cursor()

        ensure_config_table(conn)
        ensure_categorias_table_and_column(conn)
        ensure_tipos_table_and_column(conn)
        ensure_product_column(conn)
        ensure_promotions_table(conn)

        try:
            conn.commit()
        except Exception:
            pass

        print('Migración de fidelización aplicada (idempotente).')
    except Exception as e:
        print('Error durante migración de fidelización:', e)
    finally:
        try:
            if conn:
                conn.close()
        except Exception:
            pass


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Migración de esquema para fidelización (idempotente)')
    parser.add_argument('--db', help='Ruta a la base de datos SQLite (opcional)')
    args = parser.parse_args()
    run_migration(args.db)
