#!/usr/bin/env python3
"""Script de migración para crear la tabla `clientes` y añadir `puntos_activados`.

Uso:
  python3 scripts/migracion_clientes.py [<db_path>]

Si se pasa <db_path> la migración se ejecuta contra ese fichero (útil para staging/backups).
El script es idempotente: comprueba existencia de tabla y columna antes de alterar.
"""
import os
import sys
from datetime import datetime

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from database import connect


def _ensure_column_puntos_activados(conn):
    cur = conn.cursor()
    try:
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='clientes'")
        if not cur.fetchone():
            return False, 'table_missing'

        cur.execute("PRAGMA table_info(clientes)")
        cols = [r[1] for r in cur.fetchall()]
        if 'puntos_activados' in cols:
            return True, 'already'

        # Add column (integer). Using ALTER TABLE ADD COLUMN
        cur.execute('ALTER TABLE clientes ADD COLUMN puntos_activados INTEGER')
        # Ensure existing rows have value 1
        try:
            cur.execute('UPDATE clientes SET puntos_activados=1 WHERE puntos_activados IS NULL')
        except Exception:
            pass
        conn.commit()
        return True, 'added'
    finally:
        try:
            cur.close()
        except Exception:
            pass


def migrar(db_path: str = None):
    """Run migration. If db_path provided, connect to that DB file (staging).

    Returns a tuple (ok:bool, message:str).
    """
    conn = None
    try:
        if db_path:
            conn = connect(db_path)
        else:
            conn = connect()

        cur = conn.cursor()
        # Ensure table exists (original behavior)
        cur.execute('''
            CREATE TABLE IF NOT EXISTS clientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                telefono TEXT,
                email TEXT,
                dni TEXT,
                direccion TEXT,
                ciudad TEXT,
                cp TEXT,
                tags TEXT,
                puntos_fidelidad INTEGER DEFAULT 0,
                total_gastado REAL DEFAULT 0.0,
                notas_internas TEXT,
                fecha_alta TEXT
            )
        ''')
        conn.commit()

        ok, msg = _ensure_column_puntos_activados(conn)
        if msg == 'table_missing':
            return False, 'clientes table missing after create step'
        if msg == 'already':
            return True, 'puntos_activados already present'
        if msg == 'added':
            return True, 'puntos_activados added and populated'
        return True, 'unknown'
    except Exception as e:
        return False, f'error: {e}'
    finally:
        try:
            if conn:
                conn.close()
        except Exception:
            pass


if __name__ == '__main__':
    # accept optional db path as first arg
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    ok, msg = migrar(arg)
    if ok:
        print('Migración OK:', msg)
        sys.exit(0)
    else:
        print('Migración FALLÓ:', msg)
        sys.exit(2)
#!/usr/bin/env python3
"""Script de migración para crear la tabla `clientes` en la BD."""
import os
import sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from database import connect

def migrar():
    conn = connect()
    cur = conn.cursor()
    try:
        cur.execute('''
            CREATE TABLE IF NOT EXISTS clientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                telefono TEXT,
                email TEXT,
                dni TEXT,
                direccion TEXT,
                ciudad TEXT,
                cp TEXT,
                tags TEXT,
                puntos_fidelidad INTEGER DEFAULT 0,
                total_gastado REAL DEFAULT 0.0,
                notas_internas TEXT,
                fecha_alta TEXT
            )
        ''')
        conn.commit()
        print('Migración completada: tabla `clientes` creada/asegurada.')
    except Exception as e:
        print('Error creando tabla clientes:', e)
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
    migrar()
