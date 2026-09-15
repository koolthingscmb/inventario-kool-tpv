import logging
from typing import Dict, Any, Optional
from kool_tpv.base_datos.db_wrapper import Database

logger = logging.getLogger(__name__)

class ShopifyConfigService:
    """Servicio para gestionar la persistencia de la configuración de Shopify en la base de datos."""

    # Claves utilizadas en la tabla configuracion
    KEYS = {
        "shop_url": "shopify_shop_url",
        "access_token": "shopify_access_token",
        "location_id": "shopify_location_id",
        "sync_active": "shopify_sync_active",
        "ia_model": "shopify_ia_model",
        "ia_api_key": "shopify_ia_api_key",
        "google_api_key": "shopify_google_api_key",
        "ia_seo_prompt": "shopify_ia_seo_prompt",
        "source_anilist": "shopify_source_anilist",
        "source_mangadex": "shopify_source_mangadex",
        "source_bgg": "shopify_source_bgg",
        "source_google_books": "shopify_source_google_books",
        "source_wikipedia_es": "shopify_source_wikipedia_es",
        "source_wikipedia_en": "shopify_source_wikipedia_en"
    }

    def __init__(self, db: Database):
        self.db = db

    def get_config(self) -> Dict[str, Any]:
        """Carga toda la configuración de Shopify desde la BD en una única consulta eficiente."""
        config = {local_key: "" for local_key in self.KEYS}
        try:
            # Una sola query para todas las claves de Shopify
            rows = self.db.fetch_all("SELECT clave, valor FROM configuracion WHERE clave LIKE 'shopify_%'")
            
            # Mapeo inverso: de db_key a local_key
            reverse_keys = {v: k for k, v in self.KEYS.items()}
            
            if rows:
                for clave_db, valor in rows:
                    if clave_db in reverse_keys:
                        config[reverse_keys[clave_db]] = valor
            
            # Conversión de tipos para booleanos
            bool_keys = ["sync_active", "source_anilist", "source_mangadex", "source_bgg", "source_google_books", "source_wikipedia_es", "source_wikipedia_en"]
            for bk in bool_keys:
                if bk in config:
                    config[bk] = config[bk] == "1"
            
        except Exception:
            logger.exception("Error cargando configuración de Shopify")
        
        return config

    def save_config(self, config: Dict[str, Any]) -> bool:
        """Guarda la configuración de Shopify en la BD."""
        try:
            with self.db.transaction() as cur:
                for local_key, db_key in self.KEYS.items():
                    if local_key in config:
                        val = config[local_key]
                        # Convertir booleanos a 1/0 para SQLite
                        if isinstance(val, bool):
                            val = "1" if val else "0"
                        
                        cur.execute(
                            "INSERT OR REPLACE INTO configuracion (clave, valor) VALUES (?, ?)",
                            (db_key, str(val))
                        )
            return True
        except Exception:
            logger.exception("Error guardando configuración de Shopify")
            return False

    def add_log(self, accion: str, resultado: str, mensaje: str, producto_id: Optional[int] = None) -> bool:
        """Añade una entrada a la tabla shopify_sync_log."""
        try:
            query = """
            INSERT INTO shopify_sync_log (producto_id, accion, resultado, mensaje)
            VALUES (?, ?, ?, ?)
            """
            self.db.execute_query(query, (producto_id, accion, resultado, mensaje))
            return True
        except Exception:
            logger.exception("Error añadiendo log de Shopify")
            return False

    def get_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Obtiene los últimos logs de sincronización."""
        try:
            query = """
            SELECT id, producto_id, accion, resultado, mensaje, created_at 
            FROM shopify_sync_log 
            ORDER BY created_at DESC 
            LIMIT ?
            """
            rows = self.db.fetch_all(query, (limit,))
            logs = []
            for r in rows:
                logs.append({
                    "id": r[0],
                    "producto_id": r[1],
                    "accion": r[2],
                    "resultado": r[3],
                    "mensaje": r[4],
                    "fecha": r[5]
                })
            return logs
        except Exception:
            logger.exception("Error obteniendo logs de Shopify")
            return []

    def clear_logs(self) -> bool:
        """Limpia todo el historial de logs."""
        try:
            self.db.execute_query("DELETE FROM shopify_sync_log")
            return True
        except Exception:
            logger.exception("Error limpiando logs de Shopify")
            return False

    # --- Mapeo de Fuentes y Tipos ---

    def get_source_type_mappings(self, source_id: str) -> List[int]:
        """Obtiene los IDs de tipos asociados a una fuente."""
        try:
            query = "SELECT tipo_id FROM shopify_source_type_mapping WHERE source_id = ?"
            rows = self.db.fetch_all(query, (source_id,))
            return [r[0] for r in (rows or [])]
        except Exception:
            logger.exception(f"Error obteniendo mapeos para fuente {source_id}")
            return []

    def update_source_type_mappings(self, source_id: str, tipo_ids: List[int]) -> bool:
        """Actualiza los tipos asociados a una fuente (borra y reinserta)."""
        try:
            with self.db.transaction() as cur:
                cur.execute("DELETE FROM shopify_source_type_mapping WHERE source_id = ?", (source_id,))
                for t_id in tipo_ids:
                    cur.execute(
                        "INSERT INTO shopify_source_type_mapping (source_id, tipo_id) VALUES (?, ?)",
                        (source_id, t_id)
                    )
            return True
        except Exception:
            logger.exception(f"Error actualizando mapeos para fuente {source_id}")
            return False
