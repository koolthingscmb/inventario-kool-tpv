import logging
from typing import Optional, Dict, Any, List
from kool_tpv.base_datos.db_wrapper import Database

logger = logging.getLogger(__name__)

class ShopifyRepository:
    """Repository para gestionar el mapeo y logs de sincronización con Shopify."""

    def __init__(self, db: Database):
        self.db = db

    # --- Mapping Métodos ---

    def get_mapping_by_product_id(self, producto_id: int) -> Optional[Dict[str, Any]]:
        """Obtiene el mapeo de Shopify para un producto local."""
        row = self.db.fetch_one(
            "SELECT * FROM shopify_product_mapping WHERE producto_id = ?",
            (producto_id,)
        )
        return dict(row) if row else None

    def get_mapping_by_shopify_id(self, shopify_product_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene el mapeo local a partir del ID de Shopify."""
        row = self.db.fetch_one(
            "SELECT * FROM shopify_product_mapping WHERE shopify_product_id = ?",
            (shopify_product_id,)
        )
        return dict(row) if row else None

    def upsert_mapping(self, producto_id: int, shopify_product_id: str, handle: str = None, status: str = None) -> None:
        """Crea o actualiza el mapeo entre producto local y Shopify."""
        # Primero intentamos ver si existe
        existing = self.get_mapping_by_product_id(producto_id)
        if existing:
            self.db.execute_query(
                "UPDATE shopify_product_mapping SET shopify_product_id = ?, handle = ?, status = ?, last_synced_at = datetime('now', 'localtime') WHERE producto_id = ?",
                (shopify_product_id, handle, status, producto_id)
            )
        else:
            self.db.execute_query(
                "INSERT INTO shopify_product_mapping (producto_id, shopify_product_id, handle, status, last_synced_at) VALUES (?, ?, ?, ?, datetime('now', 'localtime'))",
                (producto_id, shopify_product_id, handle, status)
            )

    def delete_mapping(self, producto_id: int) -> None:
        """Elimina el mapeo de un producto."""
        self.db.execute_query(
            "DELETE FROM shopify_product_mapping WHERE producto_id = ?",
            (producto_id,)
        )

    # --- Logs Métodos ---

    def add_sync_log(self, producto_id: Optional[int], accion: str, resultado: str,
                     mensaje: str = None, sku: str = None, cantidad: Optional[int] = None,
                     cur=None) -> None:
        """Registra un evento de sincronización en el log."""
        query = """
            INSERT INTO shopify_sync_log (producto_id, accion, resultado, mensaje, sku, cantidad, created_at)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now', 'localtime'))
        """
        params = (producto_id, accion, resultado, mensaje, sku, cantidad)
        if cur:
            cur.execute(query, params)
        else:
            self.db.execute_query(query, params)

    def get_sync_logs(self, producto_id: Optional[int] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Obtiene los últimos logs de sincronización."""
        if producto_id:
            query = "SELECT * FROM shopify_sync_log WHERE producto_id = ? ORDER BY created_at DESC LIMIT ?"
            params = (producto_id, limit)
        else:
            query = "SELECT * FROM shopify_sync_log ORDER BY created_at DESC LIMIT ?"
            params = (limit,)
            
        rows = self.db.fetch_all(query, params)
        return [dict(row) for row in (rows or [])]

    # --- Cola de sincronización de stock (sobre el propio log) ---

    def encolar_sync_stock(self, sku: str, cantidad: int, motivo: str = None, cur=None) -> None:
        """Deja un encargo de sincronización pendiente en el log.

        Pensado para llamarse dentro de la transacción del llamador: si ésta
        se deshace, el encargo desaparece con ella.
        """
        self.add_sync_log(
            None, "SYNC_STOCK_PREFIX", "pendiente",
            mensaje=motivo, sku=sku, cantidad=cantidad, cur=cur
        )

    def get_pendientes(self) -> List[Dict[str, Any]]:
        """Encargos de sincronización pendientes, del más antiguo al más nuevo."""
        rows = self.db.fetch_all(
            "SELECT * FROM shopify_sync_log WHERE resultado = 'pendiente' AND sku IS NOT NULL ORDER BY id"
        )
        return [dict(row) for row in (rows or [])]

    def get_errores_reintentables(self, max_intentos: int = 3) -> List[Dict[str, Any]]:
        """Errores de sincronización que aún pueden reintentarse."""
        rows = self.db.fetch_all(
            """SELECT * FROM shopify_sync_log
               WHERE resultado = 'error' AND sku IS NOT NULL
                 AND COALESCE(reintentos, 0) < ?
               ORDER BY id""",
            (max_intentos,)
        )
        return [dict(row) for row in (rows or [])]

    def marcar_resultado(self, log_id: int, resultado: str, mensaje: str = None) -> None:
        """Marca un encargo como resuelto (success/error) y guarda el motivo real."""
        if mensaje is not None:
            self.db.execute_query(
                "UPDATE shopify_sync_log SET resultado = ?, mensaje = ? WHERE id = ?",
                (resultado, mensaje, log_id)
            )
        else:
            self.db.execute_query(
                "UPDATE shopify_sync_log SET resultado = ? WHERE id = ?",
                (resultado, log_id)
            )

    def incrementar_reintentos(self, log_id: int) -> None:
        """Suma un intento a un encargo/error de sincronización."""
        self.db.execute_query(
            "UPDATE shopify_sync_log SET reintentos = COALESCE(reintentos, 0) + 1 WHERE id = ?",
            (log_id,)
        )

    def marcar_pendiente(self, log_id: int) -> None:
        """Devuelve un encargo/error a 'pendiente' para que el trabajador lo reintente."""
        self.db.execute_query(
            "UPDATE shopify_sync_log SET resultado = 'pendiente', reintentos = COALESCE(reintentos, 0) + 1 WHERE id = ?",
            (log_id,)
        )

    def get_cola_sync(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Encargos de sync que necesitan atención: pendientes, errores y SKUs sin web."""
        rows = self.db.fetch_all(
            """SELECT * FROM shopify_sync_log
               WHERE accion IN ('SYNC_STOCK_PREFIX', 'SYNC_PRODUCTO') AND sku IS NOT NULL
                 AND resultado IN ('pendiente', 'error', 'sin_variantes')
               ORDER BY id DESC LIMIT ?""",
            (limit,)
        )
        return [dict(row) for row in (rows or [])]

    # --- Mapeo Diseño -> Producto Shopify (SUBIDA) ---

    def upsert_diseno_mapping(self, diseno_codigo: str, genero: str, shopify_product_id: str, handle: str = None) -> None:
        """Crea o actualiza el vínculo diseño+género -> producto web."""
        self.db.execute_query(
            """
            INSERT INTO shopify_diseno_mapping (diseno_codigo, genero, shopify_product_id, handle, last_synced_at)
            VALUES (?, ?, ?, ?, datetime('now', 'localtime'))
            ON CONFLICT(diseno_codigo, genero) DO UPDATE SET
                shopify_product_id = excluded.shopify_product_id,
                handle = excluded.handle,
                last_synced_at = datetime('now', 'localtime')
            """,
            (diseno_codigo, genero, shopify_product_id, handle)
        )

    def get_diseno_mapping(self, diseno_codigo: str, genero: Optional[str] = None) -> List[Dict[str, Any]]:
        """Devuelve los productos web vinculados a un diseño (uno por género)."""
        if genero:
            rows = self.db.fetch_all(
                "SELECT * FROM shopify_diseno_mapping WHERE diseno_codigo = ? AND genero = ?",
                (diseno_codigo, genero)
            )
        else:
            rows = self.db.fetch_all(
                "SELECT * FROM shopify_diseno_mapping WHERE diseno_codigo = ?",
                (diseno_codigo,)
            )
        return [dict(row) for row in (rows or [])]

    def get_diseno_mapping_by_shopify_id(self, shopify_product_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene el mapeo de diseño a partir del ID de Shopify."""
        row = self.db.fetch_one(
            "SELECT * FROM shopify_diseno_mapping WHERE shopify_product_id = ?",
            (shopify_product_id,)
        )
        return dict(row) if row else None
