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

from kool_tpv.base_datos.money_adapter import prepare_for_db, read_from_db
from kool_tpv.base_datos.audit_service import AuditService

logger = logging.getLogger(__name__)

from kool_tpv.base_datos.db_wrapper import Database


class ProductoRepository:
    """Repository mínimo para consultas relacionadas con `productos`.

    Constructor exige una instancia de `Database` ya conectada.
    """

    def __init__(self, db: Database):
        self.db = db
        self.audit = AuditService(db)
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
        p.fabricado_por_nosotros,
        p.es_menu,
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

    def sku_existe(self, sku: str) -> bool:
        """Verifica si un SKU ya existe en la base de datos."""
        row = self.db.fetch_one("SELECT 1 FROM productos WHERE sku = ?", (sku,))
        return row is not None

    def get_pvps_by_ids(self, producto_ids: List[int]) -> Dict[int, float]:
        """Obtener PVP activo para una lista de producto_ids en una sola query.

        Returns:
            Dict {producto_id: pvp_euros}
        """
        if not producto_ids:
            return {}
        placeholders = ','.join(['?'] * len(producto_ids))
        query = f"""
        SELECT producto_id, COALESCE(pvp, 0.0) AS pvp
        FROM precios
        WHERE producto_id IN ({placeholders}) AND activo = 1
        """
        rows = self.db.fetch_all(query, tuple(producto_ids))
        return {int(row[0]): float(read_from_db(int(row[1]))) for row in (rows or [])}

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

    def get_ventas_por_producto(self, ticket_ids: List[int], limit: int = 100, line_tipo: str = None):
        """Obtiene ventas agrupadas por producto para un rango de tickets.

        Args:
            ticket_ids: Lista de IDs de tickets
            limit: Máximo de productos a retornar
            line_tipo: Opcional, filtrar por tipo de línea ('venta', 'devolucion')

        Returns:
            List[(nombre_producto, tickets_count, unidades_sum, total_euros)]
        """
        if not ticket_ids:
            return []

        try:
            placeholders = ','.join(['?'] * len(ticket_ids))
            sql = f"""
            SELECT p.nombre, 
                   COUNT(DISTINCT tl.ticket_id) AS tickets_cnt, 
                   COALESCE(SUM(tl.cantidad), 0) AS uds,
                   COALESCE(SUM(tl.cantidad * tl.precio), 0) AS total_cents
            FROM ticket_lines tl
            JOIN productos p ON tl.producto_id = p.id
            WHERE tl.ticket_id IN ({placeholders})
            """
            params = list(ticket_ids)
            if line_tipo:
                sql += " AND tl.line_tipo = ?"
                params.append(line_tipo)

            sql += " GROUP BY p.id, p.nombre ORDER BY total_cents DESC LIMIT ?"
            params.append(limit)

            rows = self.db.fetch_all(sql, tuple(params))

            # Convertir céntimos a euros
            from kool_tpv.base_datos.money_adapter import read_from_db
            result = []
            for row in (rows or []):
                nombre = row[0]
                tickets_cnt = int(row[1] or 0)
                uds = int(row[2] or 0)
                total_cents = int(row[3] or 0)
                total_euros = read_from_db(total_cents)
                result.append((nombre, tickets_cnt, uds, float(total_euros)))

            return result

        except Exception as e:
            logging.exception(f"Error obteniendo ventas por producto: {e}")
            return []

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
            COALESCE(p.ventas_totales, 0) AS ventas,
            COALESCE(pr.pvp, 0) AS pvp,
            COALESCE(p.tipo_iva, 21) AS tipo_iva
        FROM productos p
        LEFT JOIN categorias c ON p.categoria = c.id
        LEFT JOIN tipos t ON p.tipo = t.id
        LEFT JOIN precios pr ON pr.producto_id = p.id AND pr.activo = 1
        WHERE p.nombre LIKE ? COLLATE NOCASE OR p.sku LIKE ? COLLATE NOCASE OR EXISTS (SELECT 1 FROM codigos_barras cb WHERE cb.producto_id = p.id AND cb.ean LIKE ? COLLATE NOCASE)
        ORDER BY p.id
        """
        termino_like = f'%{termino}%'
        rows = self.db.fetch_all(query, (termino_like, termino_like, termino_like))
        if not rows:
            return []
        return [dict(row) for row in rows]

    def buscar(self, termino: str = '', categoria_id=None, tipo_id=None, estados=None, limit: int = 50, offset: int = 0):
        """Query dinámica para scroll infinito en busqueda_ui.

        Devuelve list[dict] con: id, sku, nombre, categoria, tipo, ean,
        pvp (raw sin normalizar), stock_actual, ventas, estado, tipo_id, proveedor_id.
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
       END AS estado,
       p.tipo AS tipo_id,
       p.proveedor_id,
       COALESCE(prov.nombre, 'Sin proveedor') AS proveedor_nombre
FROM productos p
LEFT JOIN categorias c ON p.categoria = c.id
LEFT JOIN tipos t ON p.tipo = t.id
LEFT JOIN proveedores prov ON p.proveedor_id = prov.id
LEFT JOIN precios pr ON pr.producto_id = p.id AND pr.activo = 1
WHERE 1=1
        """
        params = []

        if termino:
            termino_like = f'%{termino}%'
            query += (
                " AND (p.nombre LIKE ? COLLATE NOCASE OR p.sku LIKE ? COLLATE NOCASE OR EXISTS ("
                "SELECT 1 FROM codigos_barras cb "
                "WHERE cb.producto_id = p.id AND cb.ean LIKE ? COLLATE NOCASE))"
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
        pvp_variable: int = 0,
        fabricado_por_nosotros: int = 0,
        codigos_barras: Optional[List[str]] = None,
        producto_id: Optional[int] = None,
        force_insert: bool = False,
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
                    if force_insert:
                        raise ValueError(
                            f'SKU duplicado al crear producto nuevo: "{sku}" '
                            f'ya existe con id={r[0]}. Use force_insert=False para actualizar.'
                        )
                    producto_id = int(r[0])

            # 2. INSERT o UPDATE producto
            if not producto_id:
                cur.execute(
                    '''INSERT INTO productos (nombre, nombre_boton, sku, categoria, tipo,
                        proveedor_id, shopify_taxonomy, tipo_iva, stock_actual, stock_minimo,
                        activo, pvp_variable, fabricado_por_nosotros, descripcion_shopify, titulo, seo_title,
                        seo_description, tipo_shop, etiquetas, shop_link, pending_sync)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (nombre, nombre_boton, sku, categoria_id, tipo_id, proveedor_id,
                     shopify_taxonomy, iva, stock_actual, stock_min, activo, pvp_variable, fabricado_por_nosotros,
                     descripcion_shopify, titulo, seo_title, seo_description, tipo_shop,
                     etiquetas, shop_link, 0),
                )
                producto_id = cur.lastrowid
            else:
                cur.execute(
                    '''UPDATE productos SET nombre=?, nombre_boton=?, sku=?, categoria=?, tipo=?,
                        proveedor_id=?, shopify_taxonomy=?, tipo_iva=?,
                        stock_minimo=?, activo=?, pvp_variable=?, fabricado_por_nosotros=?, descripcion_shopify=?, titulo=?,
                        seo_title=?, seo_description=?, tipo_shop=?, etiquetas=?,
                        shop_link=?, pending_sync=1 WHERE id=?''',
                    (nombre, nombre_boton, sku, categoria_id, tipo_id, proveedor_id,
                     shopify_taxonomy, iva, stock_min, activo, pvp_variable, fabricado_por_nosotros,
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

    def ajustar_stock_manual(self, producto_id: int, cantidad_ajuste: int, motivo: str, usuario_id: int) -> bool:
        """Realiza un ajuste manual de stock y lo registra en stock_movements y audit_logs."""
        try:
            with self.db.transaction() as cur:
                # 0. Obtener stock actual para auditoría
                cur.execute("SELECT stock_actual, nombre FROM productos WHERE id = ?", (producto_id,))
                row = cur.fetchone()
                stock_previo = row[0] if row else 0
                nombre_prod = row[1] if row else "Desconocido"

                # 1. Actualizar stock en productos
                cur.execute(
                    "UPDATE productos SET stock_actual = stock_actual + ? WHERE id = ?",
                    (cantidad_ajuste, producto_id)
                )
                # 2. Registrar movimiento técnico con usuario_id
                cur.execute(
                    "INSERT INTO stock_movements (producto_id, cantidad, motivo, usuario_id) VALUES (?, ?, ?, ?)",
                    (producto_id, cantidad_ajuste, motivo, usuario_id)
                )
                
                # 3. Auditoría de gestión
                self.audit.registrar(
                    entidad='productos',
                    entidad_id=producto_id,
                    accion='AJUSTE_STOCK_MANUAL',
                    usuario_id=usuario_id,
                    datos_previos=f"Stock previo: {stock_previo}",
                    datos_nuevos=f"Ajuste: {cantidad_ajuste} ({motivo}). Nuevo stock: {stock_previo + cantidad_ajuste}",
                    cur=cur
                )
            return True
        except Exception:
            logging.exception("Error en ajuste manual de stock para producto_id=%s", producto_id)
            raise
