from database import connect
import csv
import os

OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'sample_export.csv'))
con = connect()
cur = con.cursor()

# pick up to 3 product ids
cur.execute('SELECT id FROM productos LIMIT 3')
ids = [r[0] for r in cur.fetchall()]

if not ids:
    print('No products found in DB')
    con.close()
    raise SystemExit(1)

# columns order: id, nombre, sku, categoria, tipo, proveedor, pvp, coste, ventas_totales, stock_actual, descripcion_shopify, notas_internas
cols = ['id','nombre','sku','categoria','tipo','proveedor','pvp','coste','ventas_totales','stock_actual','descripcion_shopify','notas_internas']

with open(OUT, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=cols)
    writer.writeheader()

    for pid in ids:
        row = {c: '' for c in cols}
        try:
            cur.execute('SELECT * FROM productos WHERE id=?', (pid,))
            prod = cur.fetchone()
            pcols = []
            try:
                cur.execute('PRAGMA table_info(productos)')
                pcols = [r[1] for r in cur.fetchall()]
            except Exception:
                pass
            if prod:
                for i, pc in enumerate(pcols):
                    if pc in cols and i < len(prod):
                        row[pc] = prod[i]
        except Exception:
            pass

        # price
        try:
            cur.execute('SELECT pvp, coste FROM precios WHERE producto_id=? AND activo=1 LIMIT 1', (pid,))
            pr = cur.fetchone()
            if pr:
                row['pvp'] = pr[0]
                row['coste'] = pr[1]
        except Exception:
            pass

        # resolve proveedor id -> nombre if numeric
        try:
            prov = row.get('proveedor')
            if prov not in (None, ''):
                try:
                    prov_id = int(prov)
                    cur.execute('SELECT nombre FROM proveedores WHERE id=? LIMIT 1', (prov_id,))
                    r = cur.fetchone()
                    if r and r[0]:
                        row['proveedor'] = r[0]
                except Exception:
                    pass
        except Exception:
            pass

        writer.writerow(row)

try:
    con.close()
except Exception:
    pass

print('Wrote:', OUT)
