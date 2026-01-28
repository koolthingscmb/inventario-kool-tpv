from typing import Optional, List, Dict, Any
import logging
import sqlite3
import database
from datetime import datetime

logger = logging.getLogger(__name__)


class ProductoService:
    """Service for product lookups used by the UI/services.

    Methods return plain dicts or lists of dicts. Errors are logged and
    the methods return None/empty lists on failure.
    """

    def __init__(self):
        pass

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        if row is None:
            return None
        return {k: row[k] for k in row.keys()}

    def buscar_por_codigo(self, codigo: str) -> Optional[Dict[str, Any]]:
        """Search product by exact SKU or EAN. Returns a dict or None."""
        try:
            with database.connect() as conn:
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                cur.execute('''
                    SELECT p.nombre, pr.pvp AS precio, p.sku, p.tipo_iva, p.id, COALESCE(p.pvp_variable,0) as pvp_variable
                    FROM productos p
                    JOIN precios pr ON p.id = pr.producto_id
                    LEFT JOIN codigos_barras cb ON p.id = cb.producto_id
                    WHERE (p.sku = ? OR cb.ean = ?) AND pr.activo = 1
                    LIMIT 1
                ''', (codigo, codigo))
                row = cur.fetchone()
                return self._row_to_dict(row)
        except Exception:
            logger.exception('Error buscando producto por código: %s', codigo)
            return None

    def buscar_por_nombre(self, texto: str, limit: int = 30) -> List[Dict[str, Any]]:
        """Search products by name or sku using LIKE. Returns list of dicts."""
        try:
            like = f"%{texto}%"
            with database.connect() as conn:
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                cur.execute('''
                    SELECT p.nombre, pr.pvp AS precio, p.sku, p.tipo_iva, p.id, COALESCE(p.pvp_variable,0) as pvp_variable
                    FROM productos p
                    JOIN precios pr ON p.id = pr.producto_id
                    WHERE (p.nombre LIKE ? OR p.sku LIKE ?) AND pr.activo = 1
                    ORDER BY p.nombre COLLATE NOCASE
                    LIMIT ?
                ''', (like, like, limit))
                rows = cur.fetchall()
                return [self._row_to_dict(r) for r in rows]
        except Exception:
            logger.exception('Error buscando productos por nombre: %s', texto)
            return []

    def obtener_por_id(self, producto_id: int) -> Optional[Dict[str, Any]]:
        """Return product record (joined with active price) by id."""
        try:
            with database.connect() as conn:
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                cur.execute('''
                    SELECT p.nombre, pr.pvp AS precio, p.sku, p.tipo_iva, p.id, COALESCE(p.pvp_variable,0) as pvp_variable
                    FROM productos p
                    JOIN precios pr ON p.id = pr.producto_id
                    WHERE p.id = ? AND pr.activo = 1
                    LIMIT 1
                ''', (producto_id,))
                row = cur.fetchone()
                return self._row_to_dict(row)
        except Exception:
            logger.exception('Error obteniendo producto id=%s', producto_id)
            return None

    def guardar_producto(self, datos_producto: Dict[str, Any], lista_eans: List[str], lista_imagenes: List[str]) -> Optional[int]:
        """Guarda o actualiza un producto de forma transaccional.

        Usa un único contexto `with database.connect() as conn:` para asegurar
        rollback automático en caso de error.

        Retorna el id del producto o None si falla.
        """
        try:
            now = datetime.now().isoformat(sep=' ', timespec='seconds')
            # extraer campos con valores por defecto si faltan
            prod_id = datos_producto.get('id') or datos_producto.get('producto_id')
            nombre = datos_producto.get('nombre', '')
            nombre_boton = datos_producto.get('nombre_boton', '')
            sku = datos_producto.get('sku', '')
            categoria = datos_producto.get('categoria', '')
            proveedor = datos_producto.get('proveedor', '')
            tipo_iva = int(datos_producto.get('tipo_iva', 0) or 0)
            stock_actual = int(datos_producto.get('stock_actual', 0) or 0)
            pvp_variable = 1 if datos_producto.get('pvp_variable') else 0
            titulo = datos_producto.get('titulo', '')
            stock_minimo = int(datos_producto.get('stock_minimo', 0) or 0)
            activo = 1 if datos_producto.get('activo', 1) else 0
            descripcion_shopify = datos_producto.get('descripcion_shopify', '')
            pending_sync = 1 if datos_producto.get('pending_sync') else 0
            # precios
            pvp = float(datos_producto.get('pvp', 0.0) or 0.0)
            coste = float(datos_producto.get('coste', 0.0) or 0.0)
            usuario = datos_producto.get('usuario', 'system')
            cambios_txt = datos_producto.get('cambios', f'Guardado por servicio a {now}')

            with database.connect() as conn:
                cur = conn.cursor()
                # inspeccionar columnas existentes para operaciones condicionales
                try:
                    cur.execute('PRAGMA table_info(productos)')
                    cols = [c[1] for c in cur.fetchall()]
                except Exception:
                    cols = []

                # Inserción/actualización base (sin campos opcionales que pueden no existir)
                if not prod_id:
                    cur.execute('''
                        INSERT INTO productos (nombre, nombre_boton, sku, categoria, proveedor, tipo_iva, stock_actual, pvp_variable, titulo, stock_minimo, activo, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (nombre, nombre_boton, sku, categoria, proveedor, tipo_iva, stock_actual, pvp_variable, titulo, stock_minimo, activo, now, now))
                    prod_id = cur.lastrowid
                else:
                    # asegurar que el id sea int
                    try:
                        pid = int(prod_id)
                    except Exception:
                        pid = prod_id
                    cur.execute('''
                        UPDATE productos SET nombre=?, nombre_boton=?, sku=?, categoria=?, proveedor=?, tipo_iva=?, stock_actual=?, pvp_variable=?, titulo=?, stock_minimo=?, activo=?, updated_at=?
                        WHERE id=?
                    ''', (nombre, nombre_boton, sku, categoria, proveedor, tipo_iva, stock_actual, pvp_variable, titulo, stock_minimo, activo, now, pid))
                    prod_id = pid

                # Guardar campos opcionales solo si existen en la tabla
                optional_updates = []
                if 'descripcion_shopify' in cols:
                    optional_updates.append(('descripcion_shopify', descripcion_shopify))
                if 'link' in cols and datos_producto.get('link') is not None:
                    optional_updates.append(('link', datos_producto.get('link')))
                if 'shopify_taxonomy' in cols and datos_producto.get('shopify_taxonomy') is not None:
                    optional_updates.append(('shopify_taxonomy', datos_producto.get('shopify_taxonomy')))
                if 'pending_sync' in cols:
                    optional_updates.append(('pending_sync', pending_sync))

                if optional_updates:
                    # construir query dinámicamente
                    set_clause = ', '.join([f"{k}=?" for k, _ in optional_updates]) + ', updated_at=?'
                    params = [v for _, v in optional_updates]
                    params.append(now)
                    params.append(prod_id)
                    try:
                        cur.execute(f'UPDATE productos SET {set_clause} WHERE id=?', tuple(params))
                    except Exception:
                        logger.debug('No se pudo actualizar campos opcionales para producto id=%s', prod_id)

                # Lógica dinámica para campo 'tipo' (buscar column candidates y actualizar)
                tipo_val = datos_producto.get('tipo') or datos_producto.get('tipo_sel') or datos_producto.get('tipo_id')
                if tipo_val is not None:
                    tipo_candidates = ['tipo', 'tipo_id', 'id_tipo', 'tipo_shop']
                    for tc in tipo_candidates:
                        if tc in cols:
                            try:
                                cur.execute(f'UPDATE productos SET {tc}=? WHERE id=?', (tipo_val, prod_id))
                            except Exception:
                                logger.debug('No se pudo actualizar columna tipo %s para producto %s', tc, prod_id)
                            break

                # Precios: desactivar antiguos e insertar nuevo registro
                try:
                    cur.execute('UPDATE precios SET activo=0 WHERE producto_id=?', (prod_id,))
                except Exception:
                    # si la tabla no existe o la columna difiere, dejamos pasar y continuamos
                    logger.debug('No se pudo desactivar precios antiguos para producto id=%s', prod_id)
                cur.execute('INSERT INTO precios (producto_id, pvp, coste, fecha_registro, activo) VALUES (?, ?, ?, ?, 1)', (prod_id, pvp, coste, now))

                # EANs
                cur.execute('DELETE FROM codigos_barras WHERE producto_id=?', (prod_id,))
                for ean in lista_eans or []:
                    try:
                        cur.execute('INSERT INTO codigos_barras (producto_id, ean) VALUES (?, ?)', (prod_id, ean))
                    except Exception:
                        logger.debug('Falló insertar EAN %s para producto %s', ean, prod_id)

                # Imágenes
                try:
                    cur.execute('DELETE FROM product_images WHERE producto_id=?', (prod_id,))
                    for pth in lista_imagenes or []:
                        try:
                            cur.execute('INSERT INTO product_images (producto_id, path) VALUES (?, ?)', (prod_id, pth))
                        except Exception:
                            logger.debug('Falló insertar imagen %s para producto %s', pth, prod_id)
                except Exception:
                    logger.debug('Tabla product_images no disponible o error eliminando imágenes para id=%s', prod_id)

                # Historial
                try:
                    cur.execute('INSERT INTO product_history (producto_id, usuario, fecha, cambios) VALUES (?, ?, ?, ?)', (prod_id, usuario, now, cambios_txt))
                except Exception:
                    logger.debug('No se pudo insertar historial para producto id=%s', prod_id)
                # Commit explícito antes de salir del with
                try:
                    conn.commit()
                except Exception:
                    logger.debug('No se pudo hacer commit explicito para producto id=%s', prod_id)
            return int(prod_id)
        except Exception:
            logger.exception('Error guardando producto: %s', datos_producto.get('sku') if isinstance(datos_producto, dict) else datos_producto)
            return None

    def obtener_producto_completo(self, producto_id: int) -> Optional[Dict[str, Any]]:
        """Devuelve un dict con datos básicos, precio activo, eans, imágenes e historial."""
        try:
            with database.connect() as conn:
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                # producto básico (incluye posibles columnas opcionales)
                cur.execute('SELECT * FROM productos WHERE id=? LIMIT 1', (producto_id,))
                prod_row = cur.fetchone()
                producto = dict(prod_row) if prod_row else {}

                # inspeccionar columnas
                try:
                    cur.execute('PRAGMA table_info(productos)')
                    cols = [c[1] for c in cur.fetchall()]
                except Exception:
                    cols = []

                # precio activo
                precio = None
                try:
                    cur.execute('SELECT pvp, coste FROM precios WHERE producto_id=? AND activo=1 LIMIT 1', (producto_id,))
                    pr = cur.fetchone()
                    if pr:
                        precio = {'pvp': pr['pvp'] if 'pvp' in pr.keys() else pr[0], 'coste': pr['coste'] if 'coste' in pr.keys() else pr[1]}
                except Exception:
                    precio = None

                # eans
                eans = []
                try:
                    cur.execute('SELECT ean FROM codigos_barras WHERE producto_id=?', (producto_id,))
                    eans = [r['ean'] if isinstance(r, sqlite3.Row) else r[0] for r in cur.fetchall()]
                except Exception:
                    eans = []

                # imágenes
                imagenes = []
                try:
                    cur.execute('SELECT path FROM product_images WHERE producto_id=?', (producto_id,))
                    imagenes = [r['path'] if isinstance(r, sqlite3.Row) else r[0] for r in cur.fetchall()]
                except Exception:
                    imagenes = []

                # historial
                historial = []
                try:
                    cur.execute('SELECT usuario, fecha, cambios FROM product_history WHERE producto_id=? ORDER BY fecha DESC LIMIT 5', (producto_id,))
                    for r in cur.fetchall():
                        if isinstance(r, sqlite3.Row):
                            historial.append({'usuario': r['usuario'], 'fecha': r['fecha'], 'cambios': r['cambios']})
                        else:
                            historial.append({'usuario': r[0], 'fecha': r[1], 'cambios': r[2]})
                except Exception:
                    historial = []

                # valor del campo tipo si existe
                tipo_val = None
                try:
                    tipo_candidates = ['tipo', 'tipo_id', 'id_tipo', 'tipo_shop']
                    for tc in tipo_candidates:
                        if tc in cols:
                            try:
                                cur.execute(f'SELECT {tc} FROM productos WHERE id=? LIMIT 1', (producto_id,))
                                tr = cur.fetchone()
                                if tr:
                                    tipo_val = tr[0] if not isinstance(tr, sqlite3.Row) else tr[tc]
                            except Exception:
                                tipo_val = None
                            break
                except Exception:
                    tipo_val = None

                return {
                    'producto': producto,
                    'precio': precio,
                    'eans': eans,
                    'imagenes': imagenes,
                    'historial': historial,
                    'tipo': tipo_val,
                }
        except Exception:
            logger.exception('Error obteniendo producto completo id=%s', producto_id)
            return None

    def obtener_datos_maestros(self) -> Dict[str, Any]:
        """Devuelve listas para poblar combos: proveedores, categorias y tipos."""
        try:
            with database.connect() as conn:
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                proveedores = []
                try:
                    cur.execute('SELECT id, nombre FROM proveedores ORDER BY nombre')
                    for r in cur.fetchall():
                        proveedores.append({'id': r['id'] if 'id' in r.keys() else r[0], 'nombre': r['nombre'] if 'nombre' in r.keys() else r[1]})
                except Exception:
                    proveedores = []

                categorias = []
                cat_map = {}
                try:
                    cur.execute("SELECT nombre, shopify_taxonomy FROM categorias ORDER BY nombre")
                    rows = cur.fetchall()
                    if rows:
                        for r in rows:
                            name = r['nombre'] if 'nombre' in r.keys() else r[0]
                            tax = r['shopify_taxonomy'] if 'shopify_taxonomy' in r.keys() else (r[1] if len(r) > 1 else '')
                            categorias.append({'nombre': name, 'shopify_taxonomy': tax or ''})
                    else:
                        raise Exception('sin filas')
                except Exception:
                    try:
                        cur.execute("SELECT DISTINCT categoria FROM productos WHERE categoria IS NOT NULL AND categoria != '' ORDER BY categoria")
                        categorias = [{'nombre': r[0], 'shopify_taxonomy': ''} for r in cur.fetchall() if r[0]]
                    except Exception:
                        categorias = []

                tipos = []
                try:
                    cur.execute('SELECT nombre FROM tipos ORDER BY nombre')
                    tipos = [r['nombre'] if 'nombre' in r.keys() else r[0] for r in cur.fetchall() if (r[0] if not isinstance(r, sqlite3.Row) else r['nombre'])]
                except Exception:
                    tipos = []

                return {'proveedores': proveedores, 'categorias': categorias, 'tipos': tipos}
        except Exception:
            logger.exception('Error obteniendo datos maestros')
            return {'proveedores': [], 'categorias': [], 'tipos': []}

    def obtener_columnas_productos(self) -> List[str]:
        """Obtiene todos los nombres de columna de la tabla `productos`.

        Retorna una lista de strings con los nombres de columna en el orden
        reportado por PRAGMA table_info(productos).
        """
        try:
            with database.connect() as conn:
                cur = conn.cursor()
                try:
                    cur.execute('PRAGMA table_info(productos)')
                    rows = cur.fetchall()
                    cols = [r[1] for r in rows]
                    # Si existe una tabla de códigos de barras, exponer una columna virtual
                    # `codigo_barras` que agrupa los EANs asociados (soportado por
                    # `obtener_productos_por_ids_columnas` mediante LEFT JOIN + GROUP_CONCAT)
                    try:
                        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='codigos_barras'")
                        if cur.fetchone():
                            # evitar duplicados si ya existiera una columna con ese nombre
                            if 'codigo_barras' not in cols:
                                cols.append('codigo_barras')
                    except Exception:
                        # no hacer nada si falla la verificación
                        pass
                    return cols
                except Exception:
                    logger.exception('No se pudieron obtener columnas de productos via PRAGMA')
                    return []
        except Exception:
            logger.exception('Error conectando a DB para obtener columnas de productos')
            return []

    def obtener_productos_por_ids_columnas(self, ids: List[int], columnas: List[str]) -> List[List[Any]]:
        """Devuelve filas de `productos` para los ids y columnas solicitadas.

        Soporta una columna especial `codigo_barras` que agrupa los EANs
        asociados con `GROUP_CONCAT`. Retorna una lista de filas (listas)
        en el mismo orden que `columnas`.
        """
        if not ids or not columnas:
            return []
        try:
            with database.connect() as conn:
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()

                # detectar columnas reales de la tabla productos
                try:
                    cur.execute('PRAGMA table_info(productos)')
                    prod_cols = [r[1] for r in cur.fetchall()]
                except Exception:
                    prod_cols = []

                select_parts = []
                join_cb = False
                for col in columnas:
                    if col == 'codigo_barras':
                        join_cb = True
                        select_parts.append('GROUP_CONCAT(cb.ean, ",") AS codigo_barras')
                    elif col in prod_cols:
                        select_parts.append(f'p.{col} AS {col}')
                    else:
                        # intentar seleccionar columna desde productos si no existe en prod_cols
                        select_parts.append(f'p.{col} AS {col}')

                placeholders = ','.join(['?'] * len(ids))
                sql = 'SELECT ' + ', '.join(select_parts) + ' FROM productos p '
                if join_cb:
                    sql += 'LEFT JOIN codigos_barras cb ON p.id = cb.producto_id '
                sql += f'WHERE p.id IN ({placeholders}) '
                if join_cb:
                    sql += 'GROUP BY p.id'

                cur.execute(sql, tuple(ids))
                rows = cur.fetchall()

                result = []
                for r in rows:
                    if isinstance(r, sqlite3.Row):
                        result.append([r[col] if col in r.keys() else r[col] for col in columnas])
                    else:
                        result.append(list(r))
                return result
        except Exception:
            logger.exception('Error obteniendo productos por ids y columnas ids=%s cols=%s', ids, columnas)
            return []

    def eliminar_producto(self, producto_id: int) -> bool:
        """Borra producto y filas relacionadas de forma transaccional."""
        try:
            with database.connect() as conn:
                cur = conn.cursor()
                try:
                    cur.execute('DELETE FROM precios WHERE producto_id=?', (producto_id,))
                except Exception:
                    pass
                try:
                    cur.execute('DELETE FROM codigos_barras WHERE producto_id=?', (producto_id,))
                except Exception:
                    pass
                try:
                    cur.execute('DELETE FROM product_images WHERE producto_id=?', (producto_id,))
                except Exception:
                    pass
                try:
                    cur.execute('DELETE FROM product_history WHERE producto_id=?', (producto_id,))
                except Exception:
                    pass
                try:
                    cur.execute('DELETE FROM productos WHERE id=?', (producto_id,))
                except Exception:
                    pass
                try:
                    conn.commit()
                except Exception:
                    logger.debug('No se pudo hacer commit explicito al eliminar producto id=%s', producto_id)
            return True
        except Exception:
            logger.exception('Error eliminando producto id=%s', producto_id)
            return False

    def obtener_productos_paginados(self, filtros: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Devuelve una lista de productos paginada según los filtros.

        `filtros` puede contener: 'search'|'nombre' (texto), 'proveedor', 'categoria',
        'tipo', 'pagina' (int), 'tamaño_pagina'|'page_size' (int), 'orden'|'sort_by', 'orden_desc'|'sort_desc' (bool).
        """
        try:
            page = int(filtros.get('pagina') or filtros.get('page') or 1)
            page_size = int(filtros.get('tamaño_pagina') or filtros.get('page_size') or filtros.get('pageSize') or 100)
            search = filtros.get('search') or filtros.get('nombre') or ''
            proveedor = filtros.get('proveedor') or ''
            categoria = filtros.get('categoria') or ''
            tipo = filtros.get('tipo') or ''
            sort_by = filtros.get('orden') or filtros.get('sort_by')
            sort_desc = bool(filtros.get('orden_desc') or filtros.get('sort_desc') or False)

            with database.connect() as conn:
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()

                # detectar columnas disponibles
                try:
                    cur.execute("PRAGMA table_info(productos)")
                    prod_cols = [r[1] for r in cur.fetchall()]
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
                    # insertar antes de pvp/coste
                    select_parts.insert(-2, f'p.{tipo_col} as tipo_raw')
                    select_parts.insert(-2, f'COALESCE(t.nombre, p.{tipo_col}, "") as tipo_nombre')

                sql = 'SELECT ' + ', '.join(select_parts) + ' FROM productos p '
                sql += 'LEFT JOIN precios pr ON p.id = pr.producto_id AND pr.activo = 1 '
                sql += 'LEFT JOIN categorias cat ON (p.categoria = cat.nombre OR p.categoria = cat.id) '
                sql += 'LEFT JOIN proveedores prov ON (p.proveedor = prov.nombre OR p.proveedor = prov.id) '
                if tipo_col:
                    sql += f'LEFT JOIN tipos t ON (p.{tipo_col} = t.nombre OR p.{tipo_col} = t.id) '

                params = []
                where_clauses = []
                if search:
                    qlike = f"%{search}%"
                    sub = []
                    if name_col:
                        sub.append(f'p.{name_col} LIKE ?')
                    if sku_col:
                        sub.append(f'p.{sku_col} LIKE ?')
                    if sub:
                        where_clauses.append('(' + ' OR '.join(sub) + ')')
                        for _ in sub:
                            params.append(qlike)

                def _apply_filter_expr(expr, value):
                    if not value:
                        return
                    where_clauses.append(expr)
                    params.extend([value, value])

                _apply_filter_expr('(LOWER(p.proveedor) = LOWER(?) OR LOWER(prov.nombre) = LOWER(?))', proveedor)
                _apply_filter_expr('(LOWER(p.categoria) = LOWER(?) OR LOWER(cat.nombre) = LOWER(?))', categoria)
                if tipo_col:
                    _apply_filter_expr(f'(LOWER(p.{tipo_col}) = LOWER(?) OR LOWER(t.nombre) = LOWER(?))', tipo)

                if where_clauses:
                    sql += ' WHERE ' + ' AND '.join(where_clauses)

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
                    logger.exception('Error ejecutando consulta paginada de productos')
                    return []

                items = []
                for r in rows:
                    try:
                        _id = r['id'] if 'id' in r.keys() else r[0]
                        nombre = r['nombre'] if 'nombre' in r.keys() else (r[1] if len(r) > 1 else '')
                        sku = r['sku'] if 'sku' in r.keys() else (r[2] if len(r) > 2 else '')
                        categoria_nombre = r['categoria_nombre'] if 'categoria_nombre' in r.keys() else ''
                        proveedor_nombre = r['proveedor_nombre'] if 'proveedor_nombre' in r.keys() else ''
                        tipo_nombre = r['tipo_nombre'] if 'tipo_nombre' in r.keys() else ''
                    except Exception:
                        # fallback por índice si no es Row
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

                return items
        except Exception:
            logger.exception('Error preparando filtros para obtener productos paginados')
            return []

    def obtener_valores_unicos(self, columna: str) -> List[str]:
        """Devuelve valores distintos para la columna indicada (para usar en filtros).

        Para 'categoria', 'proveedor' y 'tipo' intenta primero las tablas maestras
        ('categorias','proveedores','tipos') y si no existen, hace DISTINCT desde productos.
        """
        try:
            with database.connect() as conn:
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()

                col = columna.lower()
                # proveedores
                if col in ('proveedor', 'proveedores'):
                    try:
                        cur.execute('SELECT nombre FROM proveedores ORDER BY nombre')
                        return [r['nombre'] if 'nombre' in r.keys() else r[0] for r in cur.fetchall()]
                    except Exception:
                        pass
                    try:
                        cur.execute("SELECT DISTINCT proveedor FROM productos WHERE proveedor IS NOT NULL AND proveedor != '' ORDER BY proveedor")
                        return [r[0] for r in cur.fetchall()]
                    except Exception:
                        return []

                # categorias
                if col in ('categoria', 'categorias'):
                    try:
                        cur.execute('SELECT nombre, shopify_taxonomy FROM categorias ORDER BY nombre')
                        rows = cur.fetchall()
                        if rows:
                            return [ (r['nombre'] if 'nombre' in r.keys() else r[0]) for r in rows ]
                    except Exception:
                        pass
                    try:
                        cur.execute("SELECT DISTINCT categoria FROM productos WHERE categoria IS NOT NULL AND categoria != '' ORDER BY categoria")
                        return [r[0] for r in cur.fetchall()]
                    except Exception:
                        return []

                # tipos
                if col in ('tipo', 'tipos'):
                    try:
                        cur.execute('SELECT nombre FROM tipos ORDER BY nombre')
                        rows = cur.fetchall()
                        if rows:
                            return [r['nombre'] if 'nombre' in r.keys() else r[0] for r in rows]
                    except Exception:
                        pass
                    # fallback: detectar columna tipo en productos
                    try:
                        cur.execute('PRAGMA table_info(productos)')
                        prod_cols = [r[1] for r in cur.fetchall()]
                        tipo_col = None
                        for tc in ['tipo', 'tipo_id', 'id_tipo', 'tipo_shop']:
                            if tc in prod_cols:
                                tipo_col = tc
                                break
                        if tipo_col:
                            cur.execute(f"SELECT DISTINCT {tipo_col} FROM productos WHERE {tipo_col} IS NOT NULL AND {tipo_col} != '' ORDER BY {tipo_col}")
                            return [r[0] for r in cur.fetchall()]
                    except Exception:
                        return []

                # genérico
                try:
                    # evitar inyección moderada: sólo permitir nombres alfanum y _
                    if not columna.replace('_', '').isalnum():
                        return []
                    cur.execute(f"SELECT DISTINCT {columna} FROM productos WHERE {columna} IS NOT NULL AND {columna} != '' ORDER BY {columna}")
                    return [r[0] for r in cur.fetchall()]
                except Exception:
                    return []
        except Exception:
            logger.exception('Error obteniendo valores únicos para columna=%s', columna)
            return []

    def borrar_productos_masivo(self, ids: List[int]) -> bool:
        """(DEPRECATED) Mantiene compatibilidad: llama a eliminar_productos_por_id o vaciar_inventario_completo.

        Recomendado: usar `eliminar_productos_por_id` o `vaciar_inventario_completo` según el caso.
        """
        try:
            if ids:
                return self.eliminar_productos_por_id(ids)
            else:
                return self.vaciar_inventario_completo()
        except Exception:
            logger.exception('Error borrando productos masivo ids=%s', ids)
            return False

    def eliminar_productos_por_id(self, ids: List[int]) -> bool:
        """Elimina productos por lista de IDs.

        Si `ids` está vacía no hace nada y retorna False.
        """
        try:
            if not ids:
                return False
            with database.connect() as conn:
                cur = conn.cursor()

                def has_table(tbl: str) -> bool:
                    try:
                        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (tbl,))
                        return cur.fetchone() is not None
                    except Exception:
                        return False

                placeholders = ','.join(['?'] * len(ids))
                params = tuple(ids)
                if has_table('precios'):
                    cur.execute(f'DELETE FROM precios WHERE producto_id IN ({placeholders})', params)
                if has_table('codigos_barras'):
                    cur.execute(f'DELETE FROM codigos_barras WHERE producto_id IN ({placeholders})', params)
                if has_table('product_images'):
                    cur.execute(f'DELETE FROM product_images WHERE producto_id IN ({placeholders})', params)
                if has_table('product_history'):
                    cur.execute(f'DELETE FROM product_history WHERE producto_id IN ({placeholders})', params)
                if has_table('productos'):
                    cur.execute(f'DELETE FROM productos WHERE id IN ({placeholders})', params)

                try:
                    conn.commit()
                except Exception:
                    logger.debug('No se pudo hacer commit explicito en eliminar_productos_por_id ids=%s', ids)
            return True
        except Exception:
            logger.exception('Error eliminando productos por id ids=%s', ids)
            return False

    def vaciar_inventario_completo(self) -> bool:
        """Borra por completo todo el inventario y tablas relacionadas.

        # Función sensible llamada desde Configuración
        """
        try:
            with database.connect() as conn:
                cur = conn.cursor()

                # Borrar tablas relacionadas sin comprobación redundante
                for table in ['precios', 'codigos_barras', 'product_images', 'product_history', 'productos']:
                    try:
                        cur.execute(f'DELETE FROM {table}')
                    except Exception:
                        logger.warning('La tabla %s no existe o ocurrió un error al intentar borrarla.', table)

                # Realizar el commit al final; si falla queremos que la excepción se propague
                conn.commit()
                return True
        except Exception:
            logger.exception('Error vaciando inventario completo')
            raise
