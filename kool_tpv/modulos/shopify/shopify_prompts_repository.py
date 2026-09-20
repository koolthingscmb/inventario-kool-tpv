import logging
from typing import Optional, Dict, Any, List
from kool_tpv.base_datos.db_wrapper import Database

logger = logging.getLogger(__name__)

class ShopifyPromptsRepository:
    """Repository para gestionar los prompts de IA de Shopify (tabla shopify_prompts)."""

    def __init__(self, db: Database):
        self.db = db

    def get_prompt(self, clave: str, tipo_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Obtiene un prompt por clave. Si tipo_id es None -> genérico (tipo IS NULL)."""
        if tipo_id is None:
            row = self.db.fetch_one(
                "SELECT * FROM shopify_prompts WHERE clave = ? AND tipo IS NULL",
                (clave,)
            )
        else:
            row = self.db.fetch_one(
                "SELECT * FROM shopify_prompts WHERE clave = ? AND tipo = ?",
                (clave, str(tipo_id))
            )
        return dict(row) if row else None

    def get_texto(self, clave: str, tipo_id: Optional[int] = None) -> str:
        """Devuelve el texto de un prompt, buscando primero el específico de tipo y cayendo al genérico."""
        try:
            if tipo_id is not None:
                row = self.db.fetch_one(
                    "SELECT texto FROM shopify_prompts WHERE clave = ? AND tipo = ?",
                    (clave, str(tipo_id))
                )
                if row and row[0]:
                    return row[0]
            row = self.db.fetch_one(
                "SELECT texto FROM shopify_prompts WHERE clave = ? AND tipo IS NULL",
                (clave,)
            )
            return row[0] if row and row[0] else ""
        except Exception:
            logger.exception(f"Error leyendo texto del prompt {clave}")
            return ""

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

    def save_texto(self, clave: str, texto: str, tipo_id: Optional[int] = None) -> bool:
        """Guarda el texto de un prompt. tipo_id=None guarda el genérico; tipo_id=ID guarda la excepción de ese tipo."""
        try:
            if tipo_id is None:
                self.db.execute_query(
                    "UPDATE shopify_prompts SET texto = ?, updated_at = CURRENT_TIMESTAMP WHERE clave = ? AND tipo IS NULL",
                    (texto, clave)
                )
                return True

            # Obtener los metadatos del prompt genérico para no perder nombre/texto_default
            base = self.db.fetch_one(
                "SELECT nombre, texto_default FROM shopify_prompts WHERE clave = ? AND tipo IS NULL",
                (clave,)
            )
            nombre = base[0] if base else clave
            texto_default = base[1] if base else ""

            self.db.execute_query(
                """INSERT INTO shopify_prompts (clave, nombre, tipo, texto, texto_default)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(clave, tipo) DO UPDATE SET
                       texto = excluded.texto,
                       updated_at = CURRENT_TIMESTAMP""",
                (clave, nombre, str(tipo_id), texto, texto_default)
            )
            return True
        except Exception:
            logger.exception(f"Error guardando prompt {clave}")
            return False

    def reset_to_default(self, clave: str, tipo_id: Optional[int] = None) -> Optional[str]:
        """Restaura el texto al original del script. Devuelve el texto restaurado."""
        try:
            if tipo_id is None:
                row = self.db.fetch_one(
                    "SELECT texto_default FROM shopify_prompts WHERE clave = ? AND tipo IS NULL",
                    (clave,)
                )
                if not row:
                    return None
                default = dict(row)["texto_default"]
                self.db.execute_query(
                    "UPDATE shopify_prompts SET texto = ?, updated_at = CURRENT_TIMESTAMP WHERE clave = ? AND tipo IS NULL",
                    (default, clave)
                )
                return default

            # Para un tipo específico: borrar la excepción y devolver el texto genérico
            self.db.execute_query(
                "DELETE FROM shopify_prompts WHERE clave = ? AND tipo = ?",
                (clave, str(tipo_id))
            )
            return self.get_texto(clave, None)
        except Exception:
            logger.exception(f"Error restaurando prompt {clave}")
            return None
