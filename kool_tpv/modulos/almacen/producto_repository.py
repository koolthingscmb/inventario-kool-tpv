"""ProductoRepository: capa mínima de acceso a BD para productos.

Provee métodos de solo lectura que devuelven los valores tal como
los entrega la base de datos (sin normalización ni transformaciones).
Reglas implementadas:
 - No se realizan try/except (los errores deben escalar)
 - No se ejecutan queries adicionales
 - No se transforman ni normalizan tipos
 - Se usan `self.db.fetch_one` / `self.db.fetch_all` según corresponda
"""
import logging
from typing import Optional, Dict, Any, List

from kool_tpv.base_datos.money_adapter import prepare_for_db

from kool_tpv.base_datos.db_wrapper import Database


class ProductoRepository:
    """Repository mínimo para consultas relacionadas con `productos`.

    Constructor exige una instancia de `Database` ya conectada.
    """

    def __init__(self, db: Database):
        self.db = db
        self._create_indexes()

    def _create_indexes(self) -> None:
        """Crear índices de rendimiento (CREATE INDEX IF NOT EXISTS — no-op si ya existen)."""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_productos_sku ON productos(sku)",
            "CREATE INDEX IF NOT EXISTS idx_tl_sku ON ticket_lines(sku)",
            "CREATE INDEX IF NOT EXISTS idx_codigos_barras_ean ON codigos_barras(ean)",
            "CREATE INDEX IF NOT EXISTS idx_codigos_barras_pid ON codigos_barras(producto_id)",
        ]
        try:
            for idx_sql in indexes:
                self.db.execute_query(idx_sql)
        except Exception:
            logging.debug('Error creando índices en ProductoRepository')

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

    def get_ventas_por_producto_id(self, producto_id: int, limite: int = 20):
        """Historial de ventas de un producto (joins con tickets y clientes).

        Devuelve lista de dicts tal como los entrega la BD:
        {ticket_id, fecha, cantidad, cliente_nombre}
        """
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
        if not rows:
            return []
        return [dict(row) for row in rows]

    def listar_con_resumen(self, termino: str = ''):
        """Productos con resumen para listados (JOIN con categorias, tipos y precios).

        Devuelve lista de dicts con las columnas tal como las entrega la BD:
        {id, nombre, stock_actual, categoria, tipo, ventas, pvp, tipo_iva}
        """
        query = """
        SELECT
            p.id,
            p.nombre,
            p.stock_actual,
            COALESCE(c.nombre, 'Sin categoría') AS categoria,
            COALESCE(t.nombre, 'Sin tipo') AS tipo,
            COALESCE((SELECT SUM(tl.cantidad) FROM ticket_lines tl WHERE tl.sku = p.sku), 0) AS ventas,
            COALESCE(pr.pvp, 0) AS pvp,
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
        if not rows:
            return []
        return [dict(row) for row in rows]

    def buscar(self, termino: str = '', categoria_id=None, tipo_id=None, estados=None, limit: int = 50, offset: int = 0):
        """Query dinámica para scroll infinito en busqueda_ui.

        Devuelve list[dict] con: id, sku, nombre, categoria, tipo, ean,
        pvp (raw sin normalizar), stock_actual, ventas, estado.
        """
        query = """
SELECT p.id,
       p.sku,
       p.nombre,
       COALESCE(c.nombre, 'Sin categoría') AS categoria,
       COALESCE(t.nombre, 'Sin tipo') AS tipo,
       (SELECT GROUP_CONCAT(cb2.ean, ', ') FROM codigos_barras cb2 WHERE cb2.producto_id = p.id) AS ean,
       COALESCE(pr.pvp, 0.0) AS pvp,
       COALESCE(p.stock_actual, 0) AS stock_actual,
       COALESCE((SELECT SUM(tl.cantidad) FROM ticket_lines tl WHERE tl.sku = p.sku), 0) AS ventas,
       CASE
           WHEN p.activo = 0 THEN 'Archivado'
           WHEN p.activo = 1 AND p.stock_actual <= 0 THEN 'Sin Stock'
           ELSE 'Activo'
       END AS estado
FROM productos p
LEFT JOIN categorias c ON p.categoria = c.id
LEFT JOIN tipos t ON p.tipo = t.id
LEFT JOIN precios pr ON pr.producto_id = p.id AND pr.activo = 1
WHERE 1=1
        """
        params = []

        if termino:
            termino_like = f'%{termino}%'
            query += (
                " AND (p.nombre LIKE ? OR p.sku LIKE ? OR EXISTS ("
                "SELECT 1 FROM codigos_barras cb "
                "WHERE cb.producto_id = p.id AND cb.ean LIKE ?))"
            )
            params.extend([termino_like, termino_like, termino_like])

        if categoria_id is not None:
            query += " AND p.categoria = ?"
            params.append(categoria_id)

        if tipo_id is not None:
            query += " AND p.tipo = ?"
            params.append(tipo_id)

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
        if not rows:
            return []
        return [dict(row) for row in rows]

    def guardar_producto_completo(
        self,
        nombre: str,
        nombre_boton: str,
        sku: str,
        categoria_id,
        tipo_id,
        proveedor_id,
        iva,
        stock_actual: int,
        stock_min: int,
        activo: int,
        pvp,
        coste,
        codigos_barras: Optional[List[str]] = None,
        producto_id: Optional[int] = None,
        shopify_taxonomy: str = '',
        descripcion_shopify: str = '',
        titulo: str = '',
        seo_title: str = '',
        seo_description: str = '',
        tipo_shop: str = '',
        etiquetas: str = '',
        shop_link: str = '',
    ) -> int:
        """Guarda producto COMPLETO (producto + precio + códigos) en UNA transacción atómica.

        Si producto_id es None y SKU existe en BD → usa ese id como UPDATE.
        Si producto_id es None y SKU no existe → INSERT nuevo.
        Si producto_id está informado → UPDATE directo.

        Todo o nada: si falla cualquier operación → rollback total.
        Devuelve el id del producto guardado.
        """
        try:
            cur = self.db.connection.cursor()
            cur.execute('BEGIN')

            # 1. Si no hay producto_id, buscar por SKU
            if not producto_id and sku:
                cur.execute('SELECT id FROM productos WHERE sku = ?', (sku,))
                r = cur.fetchone()
                if r and r[0]:
                    producto_id = int(r[0])

            # 2. INSERT o UPDATE producto
            if not producto_id:
                cur.execute(
                    '''INSERT INTO productos (nombre, nombre_boton, sku, categoria, tipo,
                        proveedor_id, shopify_taxonomy, tipo_iva, stock_actual, stock_minimo,
                        activo, pvp_variable, descripcion_shopify, titulo, seo_title,
                        seo_description, tipo_shop, etiquetas, shop_link, pending_sync)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (nombre, nombre_boton, sku, categoria_id, tipo_id, proveedor_id,
                     shopify_taxonomy, iva, stock_actual, stock_min, activo, 0,
                     descripcion_shopify, titulo, seo_title, seo_description, tipo_shop,
                     etiquetas, shop_link, 0),
                )
                producto_id = cur.lastrowid
            else:
                cur.execute(
                    '''UPDATE productos SET nombre=?, nombre_boton=?, categoria=?, tipo=?,
                        proveedor_id=?, shopify_taxonomy=?, tipo_iva=?, stock_actual=?,
                        stock_minimo=?, activo=?, descripcion_shopify=?, titulo=?,
                        seo_title=?, seo_description=?, tipo_shop=?, etiquetas=?,
                        shop_link=? WHERE id=?''',
                    (nombre, nombre_boton, categoria_id, tipo_id, proveedor_id,
                     shopify_taxonomy, iva, stock_actual, stock_min, activo,
                     descripcion_shopify, titulo, seo_title, seo_description, tipo_shop,
                     etiquetas, shop_link, producto_id),
                )

            # 3. Desactivar precios anteriores
            cur.execute('UPDATE precios SET activo = 0 WHERE producto_id = ?', (producto_id,))

            # 4. Insertar nuevo precio (pvp/coste convertidos a céntimos)
            pvp_db = int(prepare_for_db(pvp))
            coste_db = int(prepare_for_db(coste))
            cur.execute(
                'INSERT INTO precios (producto_id, pvp, coste, activo) VALUES (?, ?, ?, 1)',
                (producto_id, pvp_db, coste_db),
            )

            # 5. DELETE códigos antiguos e INSERT nuevos
            cur.execute('DELETE FROM codigos_barras WHERE producto_id = ?', (producto_id,))
            if codigos_barras:
                cur.executemany(
                    'INSERT INTO codigos_barras (producto_id, ean) VALUES (?, ?)',
                    [(producto_id, c) for c in codigos_barras],
                )

            self.db.connection.commit()
            return producto_id

        except Exception:
            self.db.connection.rollback()
            logging.exception('Error guardando producto completo id=%s', producto_id)
            raise
