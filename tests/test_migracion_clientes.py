#!/usr/bin/env python3
"""Basic test runner for clientes migration (non-pytest)."""
import os
import shutil
import tempfile
import subprocess
import sys
from database import DB_PATH, connect
# import scripts.migracion_clientes as mig


def run():
    # create staging copy
    tmp_dir = tempfile.gettempdir()
    ts = 'staging_test'
    dst = os.path.join(tmp_dir, f'inventario.db.{ts}.sqlite')
    shutil.copy(DB_PATH, dst)
    print('Staging DB at', dst)

    # call migration script as subprocess to avoid import/caching issues
    env = os.environ.copy()
    env['PYTHONPATH'] = os.getcwd()
    p1 = subprocess.run([sys.executable, 'scripts/migracion_clientes.py', dst], env=env, capture_output=True, text=True)
    print('First run stdout:', p1.stdout.strip())
    print('First run stderr:', p1.stderr.strip())
    p2 = subprocess.run([sys.executable, 'scripts/migracion_clientes.py', dst], env=env, capture_output=True, text=True)
    print('Second run stdout:', p2.stdout.strip())
    print('Second run stderr:', p2.stderr.strip())
    assert p1.returncode == 0
    assert p2.returncode == 0

    conn = connect(dst)
    cur = conn.cursor()
    try:
        cur.execute("PRAGMA table_info(clientes)")
        cols = [r[1] for r in cur.fetchall()]
        print('Columns:', cols)
        # New schema uses `fidelidad_activa` instead of `puntos_activados`
        assert 'fidelidad_activa' in cols or 'puntos_activados' in cols, 'fidelidad_activa missing'

        # insert a client with fidelidad_activa = 0 (or puntos_activados for legacy DBs)
        if 'fidelidad_activa' in cols:
            cur.execute("INSERT INTO clientes (nombre, fidelidad_activa) VALUES (?, ?)", ('TC Test', 0))
        else:
            cur.execute("INSERT INTO clientes (nombre, puntos_activados) VALUES (?, ?)", ('TC Test', 0))
        conn.commit()
        cid = cur.lastrowid
        if 'fidelidad_activa' in cols:
            cur.execute('SELECT fidelidad_activa FROM clientes WHERE id=?', (cid,))
            v = cur.fetchone()[0]
            print('Inserted fidelidad_activa value:', v)
            assert int(v) == 0

            # update to 1
            cur.execute('UPDATE clientes SET fidelidad_activa=? WHERE id=?', (1, cid))
            conn.commit()
            cur.execute('SELECT fidelidad_activa FROM clientes WHERE id=?', (cid,))
            v2 = cur.fetchone()[0]
            print('Updated fidelidad_activa value:', v2)
            assert int(v2) == 1
        else:
            cur.execute('SELECT puntos_activados FROM clientes WHERE id=?', (cid,))
            v = cur.fetchone()[0]
            print('Inserted puntos_activados value:', v)
            assert int(v) == 0

            cur.execute('UPDATE clientes SET puntos_activados=? WHERE id=?', (1, cid))
            conn.commit()
            cur.execute('SELECT puntos_activados FROM clientes WHERE id=?', (cid,))
            v2 = cur.fetchone()[0]
            print('Updated puntos_activados value:', v2)
            assert int(v2) == 1
        print('TESTS OK')
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
    run()
