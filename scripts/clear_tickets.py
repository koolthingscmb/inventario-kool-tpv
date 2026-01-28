import os
import sys
import sqlite3

# Ensure project root is on sys.path so `database` can be imported when running
# this script from `scripts/` or from the UI.
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from database import DB_PATH

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

print('Counts before:')
for name in ('ticket_lines','tickets','cierres_caja'):
    try:
        cur.execute(f"SELECT COUNT(*) FROM {name}")
        print(name, cur.fetchone()[0])
    except Exception as e:
        print(name, 'ERR', e)

# Delete all test data (tables may not exist in all environments)
for tbl in ('ticket_lines', 'tickets', 'cierres_caja'):
    try:
        cur.execute(f"DELETE FROM {tbl}")
    except Exception:
        pass
conn.commit()

print('\nCounts after delete:')
for name in ('ticket_lines','tickets','cierres_caja'):
    try:
        cur.execute(f"SELECT COUNT(*) FROM {name}")
        print(name, cur.fetchone()[0])
    except Exception as e:
        print(name, 'ERR', e)

# Reset sqlite_sequence for these tables (if present) so AUTOINCREMENT restarts at 1
try:
    cur.execute("DELETE FROM sqlite_sequence WHERE name IN ('ticket_lines','tickets','cierres_caja')")
    conn.commit()
    print('\nReset sqlite_sequence entries (if existed).')
except Exception as e:
    print('\nCould not reset sqlite_sequence:', e)

cur.close()
conn.close()
print('\nDone')
