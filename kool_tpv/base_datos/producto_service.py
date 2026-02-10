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
