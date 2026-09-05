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
        query = """
        INSERT INTO shopify_product_mapping (producto_id, shopify_product_id, handle, status, last_synced_at)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(producto_id) DO UPDATE SET
            shopify_product_id = excluded.shopify_product_id,
            handle = excluded.handle,
            status = excluded.status,
            last_synced_at = CURRENT_TIMESTAMP
        """
        # Nota: ON CONFLICT requiere que producto_id sea UNIQUE en la tabla. 
        # Nuestra migración 040 no lo definió como UNIQUE explícitamente, pero debería serlo.
        # Por ahora usaremos REPLACE OR INSERT si no hay constraint, o lo manejamos manualmente.
        
        # Primero intentamos ver si existe
        existing = self.get_mapping_by_product_id(producto_id)
        if existing:
            self.db.execute_query(
                "UPDATE shopify_product_mapping SET shopify_product_id = ?, handle = ?, status = ?, last_synced_at = CURRENT_TIMESTAMP WHERE producto_id = ?",
                (shopify_product_id, handle, status, producto_id)
            )
        else:
            self.db.execute_query(
                "INSERT INTO shopify_product_mapping (producto_id, shopify_product_id, handle, status) VALUES (?, ?, ?, ?)",
                (producto_id, shopify_product_id, handle, status)
            )

    def delete_mapping(self, producto_id: int) -> None:
        """Elimina el mapeo de un producto."""
        self.db.execute_query(
            "DELETE FROM shopify_product_mapping WHERE producto_id = ?",
            (producto_id,)
        )

    # --- Logs Métodos ---

    def add_sync_log(self, producto_id: Optional[int], accion: str, resultado: str, mensaje: str = None) -> None:
        """Registra un evento de sincronización en el log."""
        self.db.execute_query(
            "INSERT INTO shopify_sync_log (producto_id, accion, resultado, mensaje) VALUES (?, ?, ?, ?)",
            (producto_id, accion, resultado, mensaje)
        )

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
