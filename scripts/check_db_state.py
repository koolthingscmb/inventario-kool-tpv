import sqlite3
import sys
import os
import time
from database import connect

def inspect_db(path):
    print('DB path:', path)
    try:
        st = os.stat(path)
        print('Size:', st.st_size, 'bytes')
        print('MTime:', time.ctime(st.st_mtime))
    except Exception as e:
        print('Stat error:', e)
        return

    wal = path + '-wal'
    shm = path + '-shm'
    print('WAL exists:', os.path.exists(wal), ' SHM exists:', os.path.exists(shm))

    try:
        conn = connect(path)
        cur = conn.cursor()
        cur.execute("PRAGMA journal_mode;")
        jm = cur.fetchone()
        print('PRAGMA journal_mode ->', jm)
        cur.execute("PRAGMA wal_autocheckpoint;")
        wak = cur.fetchone()
        print('PRAGMA wal_autocheckpoint ->', wak)
    except Exception as e:
        print('PRAGMA error:', e)
    
    # list some products
    try:
        cur.execute('SELECT id, nombre, sku, categoria, proveedor FROM productos ORDER BY id')
        rows = cur.fetchall()
        print('Productos count:', len(rows))
        for r in rows:
            print(r)
    except Exception as e:
        print('Error reading productos table:', e)
    finally:
        try:
            conn.close()
        except Exception:
            pass

if __name__ == '__main__':
    from database import DB_PATH
    if len(sys.argv) > 1:
        p = sys.argv[1]
    else:
        p = DB_PATH
    inspect_db(p)
