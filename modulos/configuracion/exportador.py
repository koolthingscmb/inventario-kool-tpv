import sqlite3
import csv
import time
import subprocess
from pathlib import Path
from database import connect, DB_PATH

def exportar_articulos_csv(dest_path=None, categorias=None, search=None, dry_run=True):
    """Exporta artículos a CSV.
    - categorias: list de nombres de categoría para filtrar (None = todas)
    - search: texto para buscar en nombre o sku
    - dry_run: si True, no escribe archivo, devuelve filas encontradas
    """
    conn = connect()
    cur = conn.cursor()

    q = '''
    SELECT p.id, p.nombre, p.sku, p.categoria, p.proveedor, p.stock_actual, pr.pvp, pr.coste
    FROM productos p
    LEFT JOIN precios pr ON p.id = pr.producto_id AND pr.activo = 1
    WHERE 1=1
    '''
    params = []
    if categorias:
        placeholders = ','.join('?' for _ in categorias)
        q += f" AND p.categoria IN ({placeholders})"
        params.extend(categorias)
    if search:
        q += " AND (p.nombre LIKE ? OR p.sku LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])

    q += " ORDER BY p.nombre LIMIT 10000"

    cur.execute(q, params)
    rows = cur.fetchall()
    conn.close()

    if dry_run:
        return rows

    if not dest_path:
        dest_path = f"/tmp/tpv_export_articulos_{int(time.time())}.csv"

    p = Path(dest_path)
    with p.open('w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['id', 'nombre', 'sku', 'categoria', 'proveedor', 'stock_actual', 'pvp', 'coste'])
        for r in rows:
            writer.writerow(r)

    # Open the file on macOS
    try:
        subprocess.run(["open", str(p)])
    except Exception:
        pass

    return str(p)

def listar_categorias():
    try:
        conn = connect()
        cur = conn.cursor()
        cur.execute('SELECT nombre FROM categorias ORDER BY nombre')
        cats = [r[0] for r in cur.fetchall()]
        conn.close()
        return cats
    except Exception:
        return []
