import logging
from typing import List, Dict, Any
from duckduckgo_search import DDGS

logger = logging.getLogger(__name__)

class WebSearchService:
    """Servicio para realizar búsquedas reales en el vasto Internet (vía DuckDuckGo)."""

    def search_manga_facts(self, query: str) -> str:
        """Busca información técnica y real de un manga en la web."""
        # Buscamos específicamente en Whakoom o sitios de editoriales para asegurar veracidad
        search_query = f"{query} manga oficial español whakoom autor"
        
        try:
            logger.info(f"Buscando en Internet datos de: {query}")
            with DDGS() as ddgs:
                # Usamos el generador de DuckDuckGo para obtener fragmentos de webs
                results = list(ddgs.text(search_query, max_results=5))
                
                if not results:
                    logger.warning(f"No se encontraron resultados en Internet para: {query}")
                    return ""
                
                context_parts = []
                for r in results:
                    title = r.get('title', '')
                    snippet = r.get('body', '')
                    context_parts.append(f"WEB_RESULT: {title}\nINFO: {snippet}")
                
                full_context = "\n\n---\n\n".join(context_parts)
                
                # MOSTRAR EN TERMINAL PARA EL USUARIO (DEBUG)
                print("\n" + "="*50)
                print(f"DATOS ENCONTRADOS EN INTERNET PARA: {query}")
                print("-"*50)
                print(full_context[:1000] + "...") # Primeros 1000 chars
                print("="*50 + "\n")
                
                return full_context
                
        except Exception as e:
            logger.error(f"Fallo en la búsqueda de Internet: {str(e)}")
            return ""
