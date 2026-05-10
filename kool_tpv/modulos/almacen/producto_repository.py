"""ProductoRepository: capa mínima de acceso a BD para productos.

Provee métodos de solo lectura que devuelven los valores tal como
los entrega la base de datos (sin normalización ni transformaciones).
Reglas implementadas:
 - No se realizan try/except (los errores deben escalar)
 - No se ejecutan queries adicionales
 - No se transforman ni normalizan tipos
 - Se usan `self.db.fetch_one` / `self.db.fetch_all` según corresponda
"""
from typing import Optional, Dict, Any

from kool_tpv.base_datos.db_wrapper import Database


class ProductoRepository:
    """Repository mínimo para consultas relacionadas con `productos`.

    Constructor exige una instancia de `Database` ya conectada.
    """

    def __init__(self, db: Database):
        self.db = db

    def get_by_id(self, producto_id: int) -> Optional[Dict[str, Any]]:
        """SELECT * FROM productos WHERE id = ?

        Devuelve un `dict` con las columnas tal como vienen de la BD
        (sin normalización). Si no existe, devuelve `None`.
        """
        row = self.db.fetch_one("SELECT * FROM productos WHERE id = ?", (producto_id,))
        if row is None:
            return None
        return dict(row)

    def get_completo(self, producto_id: int) -> Optional[Dict[str, Any]]:
        """Consulta completa (misma SELECT que ProductoService.get_producto_completo).

        Devuelve un `dict` con las columnas resultantes del SELECT tal cual
        devuelve la BD (sin normalizar tipos). Si no existe, devuelve `None`.
        """
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
        if row is None:
            return None
        return dict(row)

    def get_by_sku(self, sku: str) -> Optional[Dict[str, Any]]:
        """SELECT * FROM productos WHERE sku = ?

        Devuelve un `dict` con las columnas tal como vienen de la BD
        (sin normalización). Si no existe, devuelve `None`.
        """
        row = self.db.fetch_one("SELECT * FROM productos WHERE sku = ?", (sku,))
        if row is None:
            return None
        return dict(row)
