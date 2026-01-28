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
        """Normalize DB row into a validated dict (DTO).

        Guarantees the returned dict contains the keys:
        {'id', 'nombre', 'precio', 'sku', 'tipo_iva', 'pvp_variable'}.

        Ensures that numeric fields are not None: `precio` and `pvp_variable`
        will be floats (default 0.0) and `tipo_iva` will be int (default 0).
        If `row` is None returns None.
        """
        if row is None:
            return None

        # Build base mapping from row keys (sqlite3.Row behaves like a mapping)
        data = {k: row[k] for k in row.keys()}

        # Standardize keys and types
        result: Dict[str, Any] = {
            'id': data.get('id'),
            'nombre': data.get('nombre') or '',
            'precio': 0.0,
            'sku': data.get('sku') or '',
            'tipo_iva': 0,
            'pvp_variable': 0.0,
        }

        # precio: accept numeric-like, otherwise coerce to 0.0
        try:
            # prefer explicit key 'precio' (alias for pr.pvp)
            raw_precio = data.get('precio')
            result['precio'] = float(raw_precio) if raw_precio is not None else 0.0
        except Exception:
            result['precio'] = 0.0

        # tipo_iva: ensure int (default 0)
        try:
            raw_iva = data.get('tipo_iva')
            result['tipo_iva'] = int(raw_iva) if raw_iva is not None else 0
        except Exception:
            result['tipo_iva'] = 0

        # pvp_variable: ensure float (default 0.0)
        try:
            raw_pvpv = data.get('pvp_variable')
            result['pvp_variable'] = float(raw_pvpv) if raw_pvpv is not None else 0.0
        except Exception:
            result['pvp_variable'] = 0.0

        return result

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
                    SELECT p.id, p.nombre, pr.pvp AS precio, p.sku, p.tipo_iva, COALESCE(p.pvp_variable,0) as pvp_variable
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
