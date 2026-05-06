#!/usr/bin/env python3
"""Normalize ticket_lines.precio values that were accidentally scaled.

This script:
- Backs up the DB file to kool_bd.db.bak.TIMESTAMP
- Scans `ticket_lines` for rows where `precio` looks incorrectly scaled
  (heuristic: integer >= 10000 and divisible by 100)
- Updates those rows dividing `precio` by 100 (integer division)

Run in staging first. This change is irreversible unless you restore the
backup created by the script.
"""
from pathlib import Path
import sqlite3
import time
import shutil

ROOT = Path.cwd()
DB = ROOT / 'kool_tpv' / 'base_datos' / 'kool_bd.db'
if not DB.exists():
    print('Database not found at', DB)
    raise SystemExit(1)

bak = DB.with_name(DB.name + f'.bak.{int(time.time())}')
print('Backing up', DB, '->', bak)
shutil.copy2(DB, bak)

conn = sqlite3.connect(str(DB))
cur = conn.cursor()

# Heuristic: precio is integer >= 10000 and divisible by 100 -> divide by 100
cur.execute('SELECT id, precio FROM ticket_lines WHERE precio IS NOT NULL')
rows = cur.fetchall()
to_fix = []
for r in rows:
    tid, precio = r
    try:
        p = int(precio)
    except Exception:
        continue
    if p >= 10000 and p % 100 == 0:
        to_fix.append((tid, p))

print(f'Found {len(to_fix)} rows to normalize')
if not to_fix:
    conn.close()
    raise SystemExit(0)

# Show sample
for sample in to_fix[:10]:
    print('sample', sample)

ok = input('Proceed to update these rows? (yes/NO): ')
if ok.strip().lower() != 'yes':
    print('Aborting')
    conn.close()
    raise SystemExit(1)

try:
    cur.execute('BEGIN')
    for tid, p in to_fix:
        newp = p // 100
        cur.execute('UPDATE ticket_lines SET precio = ? WHERE id = ?', (newp, tid))
    conn.commit()
    print('Updated', len(to_fix), 'rows')
except Exception as e:
    conn.rollback()
    print('Error:', e)
finally:
    conn.close()

print('Done. If anything goes wrong restore from', bak)
