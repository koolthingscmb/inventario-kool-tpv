from typing import Optional, List, Dict, Any
import logging
import sqlite3
import database

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
                    SELECT p.id, p.nombre, pr.pvp AS precio, p.sku, COALESCE(p.pvp_variable,0) as pvp_variable
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
