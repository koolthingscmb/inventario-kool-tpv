import sqlite3
from typing import List, Dict, Optional
from database import connect


def get_products_page(db_path: str,
                      page: int = 1,
                      page_size: int = 100,
                      search: str = '',
                      proveedor: str = '',
                      categoria: str = '',
                      tipo: str = '',
                      sort_by: Optional[str] = None,
                      sort_desc: bool = False) -> List[Dict]:
    """Return a paginated list of products as dictionaries.

    This function mirrors the previous SQL logic used inside
    TodosArticulos.load_items. It keeps the DB access isolated here so
    the UI can call it via a simple API.
    """
    conn = connect(db_path)
    cur = conn.cursor()

    # get product columns to detect available fields
    try:
        cur.execute("PRAGMA table_info(productos)")
        rows = cur.fetchall()
        prod_cols = [r[1] for r in rows]
    except Exception:
        prod_cols = []

    name_col = 'nombre' if 'nombre' in prod_cols else ('name' if 'name' in prod_cols else None)
    sku_col = None
    for sc in ['sku', 'codigo', 'codigo_barra', 'codigo_barras']:
        if sc in prod_cols:
            sku_col = sc
            break

    select_parts = ['p.id']
    if name_col:
        select_parts.append(f'p.{name_col} as nombre')
    else:
        select_parts.append("'' as nombre")
    if sku_col:
        select_parts.append(f'p.{sku_col} as sku')
    else:
        select_parts.append("'' as sku")

    select_parts.extend([
        'p.categoria as categoria_raw',
        'COALESCE(cat.nombre, p.categoria, "") as categoria_nombre',
        'p.proveedor as proveedor_raw',
        'COALESCE(prov.nombre, p.proveedor, "") as proveedor_nombre',
        'pr.pvp as pvp',
        'pr.coste as coste'
    ])

    tipo_col = None
    for tc in ['tipo', 'tipo_id', 'id_tipo', 'tipo_shop']:
        if tc in prod_cols:
            tipo_col = tc
            break
    if tipo_col:
        select_parts.insert(-2, f'p.{tipo_col} as tipo_raw')
        select_parts.insert(-2, f'COALESCE(t.nombre, p.{tipo_col}, "") as tipo_nombre')

    sql = 'SELECT ' + ', '.join(select_parts) + ' FROM productos p '
    sql += 'LEFT JOIN precios pr ON p.id = pr.producto_id AND pr.activo = 1 '
    sql += 'LEFT JOIN categorias cat ON (p.categoria = cat.nombre OR p.categoria = cat.id) '
    sql += 'LEFT JOIN proveedores prov ON (p.proveedor = prov.nombre OR p.proveedor = prov.id) '
    if tipo_col:
        sql += f'LEFT JOIN tipos t ON (p.{tipo_col} = t.nombre OR p.{tipo_col} = t.id) '

    params = []
    if search:
        qlike = f"%{search}%"
        where_clauses = []
        if name_col:
            where_clauses.append(f'p.{name_col} LIKE ?')
        if sku_col:
            where_clauses.append(f'p.{sku_col} LIKE ?')
        if where_clauses:
            sql += ' WHERE (' + ' OR '.join(where_clauses) + ') '
            for _ in where_clauses:
                params.append(qlike)

    def _apply_filter(column_expr, value):
        nonlocal sql, params
        if not value:
            return
        v = value
        if 'WHERE' in sql:
            sql += ' AND '
        else:
            sql += ' WHERE '
        sql += column_expr
        params.extend([v, v])

    _apply_filter('(LOWER(p.proveedor) = LOWER(?) OR LOWER(prov.nombre) = LOWER(?)) ', proveedor)
    _apply_filter('(LOWER(p.categoria) = LOWER(?) OR LOWER(cat.nombre) = LOWER(?)) ', categoria)
    if tipo_col:
        _apply_filter(f'(LOWER(p.{tipo_col}) = LOWER(?) OR LOWER(t.nombre) = LOWER(?)) ', tipo)

    if sort_by:
        sort_map = {
            'nombre': 'nombre',
            'categoria': 'categoria_nombre',
            'proveedor': 'proveedor_nombre',
            'tipo': 'tipo_nombre'
        }
        sort_col = sort_map.get(sort_by, 'nombre')
        sql += f" ORDER BY {sort_col} {'DESC' if sort_desc else 'ASC'}"

    if page_size:
        offset = (max(1, page) - 1) * page_size
        sql += f" LIMIT {page_size} OFFSET {offset}"

    try:
        cur.execute(sql, params)
        rows = cur.fetchall()
    except Exception:
        try:
            conn.close()
        except Exception:
            pass
        return []

    items = []
    for r in rows:
        _id = r[0]
        nombre = r[1] if len(r) > 1 else ''
        sku = r[2] if len(r) > 2 else ''
        categoria_nombre = r[4] if len(r) > 4 else ''
        proveedor_nombre = r[6] if len(r) > 6 else ''
        tipo_nombre = r[8] if len(r) > 8 else ''
        items.append({
            'id': _id,
            'nombre': nombre or '',
            'sku': sku or '',
            'categoria': categoria_nombre or '',
            'proveedor': proveedor_nombre or '',
            'tipo': tipo_nombre or ''
        })

    try:
        conn.close()
    except Exception:
        pass
    return items
