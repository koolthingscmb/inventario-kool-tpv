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
        "source_anilist": "shopify_source_anilist",
        "source_bgg": "shopify_source_bgg",
        "source_google_books": "shopify_source_google_books"
    }

    def __init__(self, db: Database):
        self.db = db

    def get_config(self) -> Dict[str, Any]:
        """Carga toda la configuración de Shopify desde la BD."""
        config = {}
        try:
            # Podríamos hacer un fetch_all pero por simplicidad y robustez lo hacemos por clave
            for local_key, db_key in self.KEYS.items():
                row = self.db.fetch_one("SELECT valor FROM configuracion WHERE clave = ?", (db_key,))
                config[local_key] = row[0] if row else ""
            
            # Conversión de tipos para booleanos/números si es necesario
            config["sync_active"] = config.get("sync_active") == "1"
            config["source_anilist"] = config.get("source_anilist") == "1"
            config["source_bgg"] = config.get("source_bgg") == "1"
            config["source_google_books"] = config.get("source_google_books") == "1"
            
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
