from .db_wrapper import Database
import logging


class ProductoService:
    def __init__(self, db):
        self.db = db
    
    def get_productos_by_categoria(self, categoria_nombre):
        """Obtener productos por nombre de categoría"""
        try:
            # Prefer selecting product data plus active price from `precios` table
            query = """
            SELECT p.id, p.nombre, p.nombre_boton, COALESCE(pr.pvp, 0.0) as pvp, COALESCE(p.tipo_iva, 21) as tipo_iva
            FROM productos p
            LEFT JOIN precios pr ON pr.producto_id = p.id AND pr.activo = 1
            INNER JOIN categorias c ON c.id = p.categoria
            WHERE c.nombre = ?
            """
            rows = self.db.fetch_all(query, (categoria_nombre,))
            items = []
            for r in rows or []:
                # r: (id, nombre, nombre_boton, pvp, tipo_iva)
                pid = r[0]
                nombre = r[1] or r[2] or ''
                # Return pvp as string to preserve exact DB value for Decimal parsing
                pvp_raw = r[3]
                pvp = str(pvp_raw) if pvp_raw is not None else '0.00'
                tipo_iva = int(r[4] or 21)
                items.append({'id': pid, 'nombre': nombre, 'pvp': pvp, 'tipo_iva': tipo_iva})
            return items
        except Exception as e:
            logging.error(f"Error obteniendo productos por categoría: {e}")
            return []
    
    def get_productos_by_tipo(self, tipo_nombre):
        """Obtener productos por nombre de tipo"""
        try:
            query = """
            SELECT p.id, p.nombre, p.nombre_boton, COALESCE(pr.pvp, 0.0) as pvp, COALESCE(p.tipo_iva, 21) as tipo_iva
            FROM productos p
            LEFT JOIN precios pr ON pr.producto_id = p.id AND pr.activo = 1
            INNER JOIN tipos t ON t.id = p.tipo
            WHERE t.nombre = ?
            """
            rows = self.db.fetch_all(query, (tipo_nombre,))
            items = []
            for r in rows or []:
                pid = r[0]
                nombre = r[1] or r[2] or ''
                pvp_raw = r[3]
                pvp = str(pvp_raw) if pvp_raw is not None else '0.00'
                tipo_iva = int(r[4] or 21)
                items.append({'id': pid, 'nombre': nombre, 'pvp': pvp, 'tipo_iva': tipo_iva})
            return items
        except Exception as e:
            logging.error(f"Error obteniendo productos por tipo: {e}")
            return []

    def listar_productos(self, termino=''):
        """Listar productos con JOIN a categorías y tipos.

        Args:
            termino: Filtro por nombre (búsqueda parcial)

        Returns:
            Lista de dicts con {id, nombre, stock_actual, categoria_nombre, tipo_nombre, pvp, tipo_iva}
        """
        try:
            query = """
            SELECT 
                p.id,
                p.nombre,
                p.stock_actual,
                c.nombre AS categoria_nombre,
                t.nombre AS tipo_nombre,
                COALESCE(pr.pvp, 0.0) AS pvp,
                COALESCE(p.tipo_iva, 21) AS tipo_iva
            FROM productos p
            LEFT JOIN categorias c ON p.categoria = c.id
            LEFT JOIN tipos t ON p.tipo = t.id
            LEFT JOIN precios pr ON pr.producto_id = p.id AND pr.activo = 1
            WHERE p.nombre LIKE ?
            ORDER BY p.id
            """

            termino_like = f'%{termino}%'
            rows = self.db.fetch_all(query, (termino_like,))

            productos = []
            for r in rows or []:
                productos.append({
                    'id': r[0],
                    'nombre': r[1] or '',
                    'stock_actual': r[2] or 0,
                    'categoria': r[3] or 'Sin categoría',
                    'tipo': r[4] or 'Sin tipo',
                    'pvp': str(r[5]) if r[5] is not None else '0.00',
                    'tipo_iva': int(r[6] or 21)
                })

            return productos

        except Exception:
            logging.exception('Error listando productos con JOIN')
            return []

    def buscar_productos_paginados(self, termino_busqueda: str = '', categoria_id=None, tipo_id=None, estados=None, limit: int = 50, offset: int = 0):
        """Busca productos con paginación, filtros y JOINs.

        Args:
            termino_busqueda: Filtro por nombre, sku o ean
            categoria_id: ID de categoría (None = todas)
            tipo_id: ID de tipo (None = todos)
            estados: Lista de estados a incluir: ['activo', 'sin_stock', 'archivado']
            limit: Registros por página
            offset: Offset de paginación

        Returns:
            Lista de dicts con datos de productos
        """
        try:
            # Base query (include computed estado)
            query = """
SELECT DISTINCT p.id,
       p.sku,
       p.nombre,
       COALESCE(c.nombre, 'Sin categoría') AS categoria_nombre,
       COALESCE(t.nombre, 'Sin tipo') AS tipo_nombre,
       (SELECT GROUP_CONCAT(cb2.ean, ', ') FROM codigos_barras cb2 WHERE cb2.producto_id = p.id) AS ean,
       COALESCE(pr.pvp, 0.0) AS pvp,
       COALESCE(p.stock_actual, 0) AS stock_actual,
       COALESCE((SELECT SUM(tl.cantidad) FROM ticket_lines tl WHERE tl.sku = p.sku), 0) AS ventas,
       p.activo,
       CASE
           WHEN p.activo = 0 THEN 'Archivado'
           WHEN p.activo = 1 AND p.stock_actual <= 0 THEN 'Sin Stock'
           ELSE 'Activo'
       END AS estado
FROM productos p
LEFT JOIN categorias c ON p.categoria = c.id
LEFT JOIN tipos t ON p.tipo = t.id
LEFT JOIN precios pr ON pr.producto_id = p.id AND pr.activo = 1
LEFT JOIN codigos_barras cb ON cb.producto_id = p.id
WHERE 1=1
            """

            params = []

            # Filtro búsqueda
            if termino_busqueda:
                termino_like = f'%{termino_busqueda}%'
                query += " AND (p.nombre LIKE ? OR p.sku LIKE ? OR cb.ean LIKE ?)"
                params.extend([termino_like, termino_like, termino_like])

            # Filtro categoría
            if categoria_id is not None:
                query += " AND p.categoria = ?"
                params.append(categoria_id)

            # Filtro tipo
            if tipo_id is not None:
                query += " AND p.tipo = ?"
                params.append(tipo_id)

            # Filtro estados
            if estados:
                condiciones_estados = []
                if 'activo' in estados:
                    condiciones_estados.append("(p.activo = 1 AND p.stock_actual > 0)")
                if 'sin_stock' in estados:
                    condiciones_estados.append("(p.activo = 1 AND p.stock_actual <= 0)")
                if 'archivado' in estados:
                    condiciones_estados.append("(p.activo = 0)")

                if condiciones_estados:
                    query += " AND (" + " OR ".join(condiciones_estados) + ")"

            query += " ORDER BY p.nombre ASC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            rows = self.db.fetch_all(query, tuple(params))
            results = []
            for r in rows or []:
                results.append({
                    'id': r[0],
                    'sku': r[1] or '',
                    'nombre': r[2] or '',
                    'categoria': r[3] or 'Sin categoría',
                    'tipo': r[4] or 'Sin tipo',
                    'ean': r[5] or '',
                    'pvp': str(r[6]) if r[6] is not None else '0.00',
                    'stock_actual': int(r[7] or 0),
                    'ventas': int(r[8] or 0),
                    'estado': r[10] or 'Activo'
                })
            return results
        except Exception:
            logging.exception('Error en buscar_productos_paginados')
            return []

    def listar_categorias(self):
        """Obtener lista de todas las categorías.

        Returns:
            Lista de dicts con {id, nombre}
        """
        try:
            query = "SELECT id, nombre FROM categorias ORDER BY nombre ASC"
            rows = self.db.fetch_all(query)
            return [{'id': r[0], 'nombre': r[1]} for r in (rows or [])]
        except Exception:
            logging.exception('Error listando categorías')
            return []

    def listar_tipos(self):
        """Obtener lista de todos los tipos.

        Returns:
            Lista de dicts con {id, nombre}
        """
        try:
            query = "SELECT id, nombre FROM tipos ORDER BY nombre ASC"
            rows = self.db.fetch_all(query)
            return [{'id': r[0], 'nombre': r[1]} for r in (rows or [])]
        except Exception:
            logging.exception('Error listando tipos')
            return []

    def obtener_ventas_producto(self, producto_id, limite=20):
        """Obtener historial de ventas de un producto (últimos clientes).

        Args:
            producto_id: ID del producto
            limite: Número máximo de registros (default 20)

        Returns:
            Lista de dicts con {ticket_id, fecha, cantidad, cliente_nombre}
        """
        try:
            query = """
            SELECT
                t.id AS ticket_id,
                t.created_at AS fecha,
                tl.cantidad,
                COALESCE(c.nombre, 'Sin cliente') AS cliente_nombre
            FROM ticket_lines tl
            JOIN tickets t ON tl.ticket_id = t.id
            JOIN productos p ON tl.sku = p.sku
            LEFT JOIN clientes c ON t.cliente_id = c.id
            WHERE p.id = ?
            ORDER BY t.created_at DESC
            LIMIT ?
            """

            rows = self.db.fetch_all(query, (producto_id, limite))

            ventas = []
            for r in rows or []:
                ventas.append({
                    'ticket_id': r[0],
                    'fecha': r[1],
                    'cantidad': r[2] or 0,
                    'cliente_nombre': r[3]
                })

            return ventas

        except Exception:
            logging.exception(f'Error obteniendo ventas de producto {producto_id}')
            return []

    def get_producto_completo(self, producto_id):
        """Obtener producto completo con todos sus datos para edición.

        Args:
            producto_id: ID del producto

        Returns:
            dict con TODOS los campos de productos + precios + nombres de relaciones
            o None si no existe
        """
        try:
            query = """
            SELECT
            p.id,
            p.nombre,
            p.nombre_boton,
            p.sku,
            p.categoria,
            p.tipo,
            p.proveedor_id,
            p.tipo_iva,
            p.stock_actual,
            p.stock_minimo,
            p.ventas_totales,
            p.pvp_variable,
            p.descripcion_shopify,
            p.notas_internas,
            p.titulo,
            p.activo,
            p.created_at,
            p.updated_at,
            p.pending_sync,
            p.seo_title,
            p.seo_description,
            p.tipo_shop,
            p.etiquetas,
            p.shop_link,
            p.shopify_taxonomy,
            COALESCE(c.nombre, 'Sin categoría') AS categoria_nombre,
            COALESCE(t.nombre, 'Sin tipo') AS tipo_nombre,
            COALESCE(prov.nombre, 'Sin proveedor') AS proveedor_nombre,
            COALESCE(pr.pvp, 0.0) AS pvp,
            COALESCE(pr.coste, 0.0) AS coste,
            COALESCE((SELECT SUM(tl.cantidad) FROM ticket_lines tl WHERE tl.sku = p.sku), 0) AS ventas_tickets,
            (SELECT GROUP_CONCAT(cb.ean, ', ') FROM codigos_barras cb WHERE cb.producto_id = p.id) AS ean
            FROM productos p
            LEFT JOIN categorias c ON p.categoria = c.id
            LEFT JOIN tipos t ON p.tipo = t.id
            LEFT JOIN proveedores prov ON p.proveedor_id = prov.id
            LEFT JOIN precios pr ON pr.producto_id = p.id AND pr.activo = 1
            WHERE p.id = ?
            """

            row = self.db.fetch_one(query, (producto_id,))

            if not row:
                return None

            return {
                'id': row[0],
                'nombre': row[1],
                'nombre_boton': row[2],
                'sku': row[3],
                'categoria_id': row[4],
                'tipo_id': row[5],
                'proveedor_id': row[6],
                'tipo_iva': int(row[7] or 21),
                'stock_actual': int(row[8] or 0),
                'stock_minimo': int(row[9] or 0),
                'ventas_totales': int(row[10] or 0),
                'pvp_variable': int(row[11] or 0),
                'descripcion_shopify': row[12],
                'notas_internas': row[13],
                'titulo': row[14],
                'activo': int(row[15] or 1),
                'created_at': row[16],
                'updated_at': row[17],
                'pending_sync': int(row[18] or 0),
                'seo_title': row[19],
                'seo_description': row[20],
                'tipo_shop': row[21],
                'etiquetas': row[22],
                'shop_link': row[23],
                'shopify_taxonomy': row[24],
                'categoria_nombre': row[25],
                'tipo_nombre': row[26],
                'proveedor_nombre': row[27],
                'pvp': float(row[28] or 0.0),
                'coste': float(row[29] or 0.0),
                'ventas_tickets': int(row[30] or 0),
                'ean': row[31] or ''
            }

        except Exception:
            logging.exception('Error obteniendo producto completo')
            return None
