import logging
from typing import List, Dict, Any, Optional
from kool_tpv.base_datos.db_wrapper import Database
from ..shopify_config_service import ShopifyConfigService
from ..sources.source_manager import SourceManager
from ..openai_service import OpenAIService
from ..web_search_service import WebSearchService
from kool_tpv.paths import PROJECT_ROOT

logger = logging.getLogger(__name__)

class BuscarDataService:
    """Orquestador para buscar información en fuentes externas y generar SEO con IA."""

    def __init__(self, db: Database):
        self.db = db
        self.config_service = ShopifyConfigService(db)
        self.source_manager = SourceManager(db)
        self.web_search = WebSearchService()
        
    def _load_seo_rules(self) -> str:
        """Carga las reglas maestras de SEO desde el archivo Markdown."""
        try:
            rules_path = PROJECT_ROOT / "kool_tpv" / "modulos" / "shopify" / "SEO_RULES.md"
            if rules_path.exists():
                with open(rules_path, "r", encoding="utf-8") as f:
                    return f.read()
        except Exception:
            logger.exception("Error cargando SEO_RULES.md")
        return ""

    def get_active_sources(self, tipo_id: Optional[int] = None) -> List[Any]:
        """
        Devuelve la lista de fuentes externas activas.
        Si se proporciona tipo_id, prioriza o filtra las fuentes vinculadas a ese tipo.
        """
        config = self.config_service.get_config()
        all_sources = self.source_manager.get_all_sources()
        
        # 1. Obtener todas las fuentes activas globalmente
        active_global = [src for src in all_sources if config.get(src.id) is True]
        logger.info(f"Fuentes activas globales en config: {[s.id for s in active_global]}")
        
        if not tipo_id:
            return active_global
            
        # 2. Buscar si hay fuentes vinculadas específicamente a este tipo
        try:
            query = "SELECT source_id FROM shopify_source_type_mapping WHERE tipo_id = ?"
            rows = self.db.fetch_all(query, (tipo_id,))
            mapped_source_ids = [r[0] for r in (rows or [])]
            logger.info(f"Mapeos encontrados en BD para tipo {tipo_id}: {mapped_source_ids}")
            
            if mapped_source_ids:
                # Filtrar: solo las que están mapeadas Y activas
                mapped_active = [src for src in active_global if src.id in mapped_source_ids]
                logger.info(f"Fuentes finales a consultar (mapeadas + activas): {[s.id for s in mapped_active]}")
                if mapped_active:
                    return mapped_active
        except Exception:
            logger.exception(f"Error filtrando fuentes por tipo {tipo_id}")
            
        # 3. Fallback: Si no hay mapeos específicos activos, devolvemos todas las activas
        logger.info(f"Usando fallback: todas las fuentes activas")
        return active_global

    def _clean_query(self, query: str) -> str:
        """Limpia el nombre del producto para mejorar la búsqueda en APIs.
        Ejemplo: 'Atelier Witch 3' -> 'Atelier Witch'
        """
        import re
        # 1. Quitar números sueltos al final (posibles tomos)
        clean = re.sub(r'\s+\d+$', '', query).strip()
        # 2. Quitar palabras como 'Tomo', 'Volumen', 'Vol' al final
        clean = re.sub(r'\s+(tomo|volumen|vol|#)\s*\d*$', '', clean, flags=re.IGNORECASE).strip()
        return clean

    def search_all_active(self, query: str, tipo_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Busca en las fuentes adecuadas según el tipo de producto."""
        active_sources = self.get_active_sources(tipo_id)
        results = []
        
        # Obtener contexto del tipo (ej: 'manga') para fuentes generalistas como Google Books
        context_word = ""
        if tipo_id:
            try:
                row = self.db.fetch_one("SELECT nombre FROM tipos WHERE id = ?", (tipo_id,))
                if row:
                    context_word = row[0].lower()
            except Exception:
                logger.exception(f"Error obteniendo nombre del tipo {tipo_id}")

        # 1. Intento con el nombre original
        for src in active_sources:
            try:
                # Solo pasamos el contexto a Google Books por ahora
                if src.id == "source_google_books":
                    src_results = src.search(query, context=context_word)
                else:
                    src_results = src.search(query)
                
                for r in src_results:
                    r["_source_name"] = src.name
                    r["_source_id"] = src.id
                    results.append(r)
            except Exception:
                logger.exception(f"Error buscando en fuente {src.name}")
        
        # 2. Si no hay resultados, reintentamos con el nombre limpio (sin tomos/números)
        if not results:
            clean_query = self._clean_query(query)
            if clean_query != query:
                logger.info(f"Reintentando búsqueda con nombre limpio: {clean_query}")
                for src in active_sources:
                    try:
                        if src.id == "source_google_books":
                            src_results = src.search(clean_query, context=context_word)
                        else:
                            src_results = src.search(clean_query)
                            
                        for r in src_results:
                            r["_source_name"] = src.name
                            r["_source_id"] = src.id
                            results.append(r)
                    except Exception:
                        logger.exception(f"Error reintentando en fuente {src.name}")

        return results

    def get_full_data_and_seo(self, source_id: str, identifier: Any, product_name: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene el detalle completo de una fuente y genera el contenido SEO con IA.
        
        Args:
            source_id: ID de la fuente elegida (ej: 'source_anilist').
            identifier: ID del ítem en esa fuente (el que devuelve search).
            product_name: Nombre del producto en el TPV.
        """
        # 1. Obtener la fuente y sus detalles
        src = self.source_manager.get_source(source_id)
        if not src:
            logger.error(f"Fuente no encontrada: {source_id}")
            return None
            
        source_details = src.get_details(identifier)
        if not source_details:
            logger.error(f"No se pudieron obtener detalles de la fuente {source_id} para ID {identifier}")
            return None
            
        # 2. Configurar el servicio de IA (por ahora solo OpenAI)
        config = self.config_service.get_config()
        api_key = config.get("ia_api_key")
        model = config.get("ia_model", "gpt-4o-mini")
        prompt_template = config.get("ia_seo_prompt")
        
        if not api_key:
            logger.warning("No hay API Key de OpenAI configurada. Se devolverán solo los datos de la fuente.")
            return {
                "source_data": source_details,
                "seo_data": None
            }
            
        # 3. Generar SEO
        seo_rules = self._load_seo_rules()
        
        # 4. Búsqueda web para veracidad extra (usamos nombre limpio para mejor resultado)
        clean_name = self._clean_query(product_name)
        logger.info(f"Realizando búsqueda web de apoyo para: {clean_name}")
        web_context = self.web_search.search_manga_facts(clean_name)
        
        ai_service = OpenAIService(api_key, model)
        seo_content = ai_service.generate_seo(
            source_data=source_details, 
            product_name=product_name, 
            prompt_template=prompt_template, 
            seo_rules=seo_rules,
            web_data=web_context
        )
        
        return {
            "source_data": source_details,
            "seo_data": seo_content
        }
