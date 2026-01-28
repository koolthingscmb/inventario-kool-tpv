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

                # Commit implícito al salir del with
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
            return True
        except Exception:
            logger.exception('Error eliminando producto id=%s', producto_id)
            return False
