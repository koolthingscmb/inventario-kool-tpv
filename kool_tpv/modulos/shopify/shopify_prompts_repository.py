import logging
from typing import Optional, Dict, Any, List
from kool_tpv.base_datos.db_wrapper import Database

logger = logging.getLogger(__name__)

class ShopifyPromptsRepository:
    """Repository para gestionar los prompts de IA de Shopify (tabla shopify_prompts)."""

    def __init__(self, db: Database):
        self.db = db

    def get_prompt(self, clave: str) -> Optional[Dict[str, Any]]:
        """Obtiene un prompt por su clave ('camiseta_seo', 'camiseta_body'...)."""
        row = self.db.fetch_one(
            "SELECT * FROM shopify_prompts WHERE clave = ?",
            (clave,)
        )
        return dict(row) if row else None

    def get_all(self, tipo: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lista todos los prompts, opcionalmente filtrados por tipo."""
        if tipo:
            rows = self.db.fetch_all(
                "SELECT * FROM shopify_prompts WHERE tipo = ? ORDER BY clave",
                (tipo,)
            )
        else:
            rows = self.db.fetch_all("SELECT * FROM shopify_prompts ORDER BY tipo, clave")
        return [dict(row) for row in (rows or [])]

    def save_texto(self, clave: str, texto: str) -> bool:
        """Actualiza el texto editable de un prompt (sin tocar texto_default)."""
        try:
            self.db.execute_query(
                "UPDATE shopify_prompts SET texto = ?, updated_at = CURRENT_TIMESTAMP WHERE clave = ?",
                (texto, clave)
            )
            return True
        except Exception:
            logger.exception(f"Error guardando prompt {clave}")
            return False

    def reset_to_default(self, clave: str) -> Optional[str]:
        """Restaura el texto al original del script. Devuelve el texto restaurado."""
        try:
            row = self.db.fetch_one(
                "SELECT texto_default FROM shopify_prompts WHERE clave = ?",
                (clave,)
            )
            if not row:
                return None
            default = dict(row)["texto_default"]
            self.db.execute_query(
                "UPDATE shopify_prompts SET texto = ?, updated_at = CURRENT_TIMESTAMP WHERE clave = ?",
                (default, clave)
            )
            return default
        except Exception:
            logger.exception(f"Error restaurando prompt {clave}")
            return None
