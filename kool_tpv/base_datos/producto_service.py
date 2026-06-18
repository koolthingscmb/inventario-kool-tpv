from .db_wrapper import Database
import logging
import sqlite3
from kool_tpv.base_datos.money_adapter import read_from_db
from decimal import Decimal
from typing import List


    
def _safe_decimal_from_db(v):
    try:
        if v is None:
            return Decimal('0.00')
        return read_from_db(int(v))
    except Exception:
        try:
            return Decimal(str(v))
        except Exception:
            return Decimal('0.00')

from kool_tpv.modulos.almacen.producto_repository import ProductoRepository


class ProductoService:
    def __init__(self, db):
        self.db = db
        # Repository de solo lectura para productos (sin normalización)
        try:
            self.repo = ProductoRepository(db)
        except Exception:
            # Dejar repo como None si no se pudo instanciar (mantener compatibilidad)
            self.repo = None
    def _get_productos_by_query(self, query: str, params: tuple, row_mapper):
        """Helper privado: ejecutar query y mapear filas con `row_mapper`.

        Lanza excepciones hacia el caller si hay errores de DB.
        """
        try:
            rows = self.db.fetch_all(query, params)
            items = []
            for r in rows or []:
                items.append(row_mapper(r))
            return items
        except Exception:
            logging.exception('Error en _get_productos_by_query')
            raise
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
            return self._get_productos_by_query(query, (categoria_nombre,), lambda r: {
                'id': r[0],
                'nombre': r[1] or r[2] or '',
                'pvp': _safe_decimal_from_db(r[3]),
                'tipo_iva': int(r[4] or 21)
            })
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
            return self._get_productos_by_query(query, (tipo_nombre,), lambda r: {
                'id': r[0],
                'nombre': r[1] or r[2] or '',
                'pvp': _safe_decimal_from_db(r[3]),
                'tipo_iva': int(r[4] or 21)
            })
        except Exception as e:
            logging.error(f"Error obteniendo productos por tipo: {e}")
            return []

    def listar_productos(self, termino=''):
        """Listar productos con resumen financiero."""
        try:
            raw_list = self.repo.listar_con_resumen(termino or '')
            for item in raw_list:
                item['pvp'] = _safe_decimal_from_db(item.get('pvp', 0))
            return raw_list
        except Exception:
            logging.exception('Error listando productos')
            return []

    def buscar_productos_paginados(self, termino_busqueda: str = '', categoria_id=None, tipo_id=None, estados=None, limit: int = 50, offset: int = 0):
        """Búsqueda paginada de productos (scroll infinito)."""
        try:
            raw_list = self.repo.buscar(
                termino=termino_busqueda or '',
                categoria_id=categoria_id,
                tipo_id=tipo_id,
                estados=estados,
                limit=limit,
                offset=offset
            )
            for item in raw_list:
                item['pvp'] = _safe_decimal_from_db(item.get('pvp', 0))
            return raw_list
        except sqlite3.DatabaseError:
            logging.exception('DB error en buscar_productos_paginados')
            return []
        except Exception:
            logging.exception('Error inesperado en buscar_productos_paginados')
            raise

    def obtener_ventas_producto(self, producto_id, limite=20):
        """Obtener historial de ventas de un producto."""
        try:
            return self.repo.get_ventas_por_producto_id(producto_id, limite)
        except Exception:
            logging.exception('Error obteniendo ventas de producto %s', producto_id)
            return []

    def get_ventas_por_producto(self, ticket_ids: List[int], limit: int = 100):
        """Obtiene ventas agrupadas por producto para un rango de tickets.

        Args:
            ticket_ids: Lista de IDs de tickets
            limit: Máximo de productos a retornar (default: 100)

        Returns:
            List[(nombre_producto, tickets_count, unidades_sum, total_euros)]
        """
        try:
            if getattr(self, 'repo', None) is None:
                return []
            return self.repo.get_ventas_por_producto(ticket_ids, limit=limit)
        except Exception:
            logging.exception('Error obteniendo ventas por producto')
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

            # Preferir obtener el registro RAW a través del repository
            if getattr(self, 'repo', None) is not None:
                raw = self.repo.get_completo(producto_id)
            else:
                raw_row = self.db.fetch_one(query, (producto_id,))
                raw = dict(raw_row) if raw_row is not None else None

            if not raw:
                return None

            # Construir la misma estructura de salida basada en claves del dict RAW
            return {
                'id': raw.get('id'),
                'nombre': raw.get('nombre'),
                'nombre_boton': raw.get('nombre_boton'),
                'sku': raw.get('sku'),
                'categoria_id': raw.get('categoria'),
                'tipo_id': raw.get('tipo'),
                'proveedor_id': raw.get('proveedor_id'),
                'tipo_iva': int(raw.get('tipo_iva') or 21),
                'stock_actual': int(raw.get('stock_actual') or 0),
                'stock_minimo': int(raw.get('stock_minimo') or 0),
                'ventas_totales': int(raw.get('ventas_totales') or 0),
                'pvp_variable': int(raw.get('pvp_variable') or 0),
                'descripcion_shopify': raw.get('descripcion_shopify'),
                'notas_internas': raw.get('notas_internas'),
                'titulo': raw.get('titulo'),
                'activo': int(raw.get('activo') or 1),
                'created_at': raw.get('created_at'),
                'updated_at': raw.get('updated_at'),
                'pending_sync': int(raw.get('pending_sync') or 0),
                'seo_title': raw.get('seo_title'),
                'seo_description': raw.get('seo_description'),
                'tipo_shop': raw.get('tipo_shop'),
                'etiquetas': raw.get('etiquetas'),
                'shop_link': raw.get('shop_link'),
                'shopify_taxonomy': raw.get('shopify_taxonomy'),
                'categoria_nombre': raw.get('categoria_nombre'),
                'tipo_nombre': raw.get('tipo_nombre'),
                'proveedor_nombre': raw.get('proveedor_nombre'),
                'pvp': _safe_decimal_from_db(raw.get('pvp')),
                'coste': _safe_decimal_from_db(raw.get('coste')),
                'ventas_tickets': int(raw.get('ventas_tickets') or 0),
                'ean': raw.get('ean') or ''
            }

        except sqlite3.DatabaseError as e:
            logging.exception('DB error obteniendo producto completo %s: %s', producto_id, e)
            return None
        except Exception:
            logging.exception('Error inesperado en get_producto_completo %s', producto_id)
            raise

    def get_producto_para_carrito(self, producto_input, cantidad: int = 1, line_tipo: str = 'venta'):
        """Normalizar y devolver un dict completo listo para `CarritoService.add_item`.

        `producto_input` puede ser un `id` o un dict parcial/complete.
        Garantiza las claves: id, sku, nombre, pvp (Decimal), tipo_iva (int), cantidad (int), line_tipo, total_linea (Decimal).
        """
        try:
            # Resolver producto base
            prod = None
            if isinstance(producto_input, dict):
                if producto_input.get('id') is not None:
                    # prefer complete info from DB when possible
                    prod = producto_input
                    # if minimal, try to enrich
                    if not prod.get('pvp') or not prod.get('sku'):
                        completo = self.get_producto_completo(prod.get('id'))
                        if completo:
                            # merge completo into prod without losing provided overrides
                            merged = {**completo, **prod}
                            prod = merged
                else:
                    # dict without id, return normalized minimal
                    prod = producto_input
            else:
                # treat as id
                prod = self.get_producto_completo(producto_input)

            if not prod:
                # fallback to minimal structure
                prod = {}

            # Normalizaciones
            pid = prod.get('id')
            sku = prod.get('sku') or ''
            nombre = prod.get('nombre') or prod.get('nombre_boton') or ''
            # pvp may already be Decimal or a money_adapter value; normalize using helper
            pvp_raw = prod.get('pvp', 0)
            if isinstance(pvp_raw, Decimal):
                pvp = pvp_raw
            else:
                pvp = _safe_decimal_from_db(pvp_raw)

            try:
                tipo_iva = int(prod.get('tipo_iva', 21))
            except Exception:
                tipo_iva = 21

            try:
                cantidad_i = int(cantidad or 1)
            except Exception:
                cantidad_i = 1

            total_linea = (pvp * Decimal(cantidad_i)).quantize(Decimal('0.01'))

            return {
                'id': pid,
                'sku': sku,
                'nombre': nombre,
                'pvp': pvp,
                'tipo_iva': tipo_iva,
                'cantidad': cantidad_i,
                'total_linea': total_linea,
                'line_tipo': line_tipo,
            }
        except Exception:
            logging.exception('Error construyendo producto_para_carrito')
            return {
                'id': producto_input if not isinstance(producto_input, dict) else producto_input.get('id'),
                'sku': '',
                'nombre': '' if isinstance(producto_input, dict) else str(producto_input),
                'pvp': Decimal('0.00'),
                'tipo_iva': 21,
                'cantidad': int(cantidad or 1),
                'total_linea': Decimal('0.00'),
                'line_tipo': line_tipo,
            }

    def buscar_por_ean(self, ean: str):
        """Buscar producto por código EAN/barcode y devolver datos listos para el carrito.

        Returns:
            dict con {id, sku, nombre, pvp, tipo_iva, cantidad, total_linea, line_tipo}
            o None si no existe
        """
        try:
            # Limpiar espacios y caracteres de control que el escáner pueda enviar
            ean_limpio = ean.strip() if ean else ''
            if not ean_limpio:
                return None
            query = """
            SELECT p.id
            FROM productos p
            INNER JOIN codigos_barras cb ON cb.producto_id = p.id
            WHERE cb.ean LIKE ?
            LIMIT 1
            """
            row = self.db.fetch_one(query, (ean_limpio,))
            if not row:
                return None
            producto_id = row[0]
            return self.get_producto_para_carrito(producto_id)
        except Exception:
            logging.exception('Error buscando producto por EAN: %s', ean)
            return None
