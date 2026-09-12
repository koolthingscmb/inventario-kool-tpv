import logging
import requests
import time
from typing import List, Dict, Any, Optional, Tuple
from .base_source import BaseSource

logger = logging.getLogger(__name__)

class JikanSource(BaseSource):
    """Implementación de Jikan (MyAnimeList) como fuente de datos para Mangas."""

    API_BASE_URL = "https://api.jikan.moe/v4"

    @property
    def id(self) -> str:
        return "source_jikan"

    @property
    def name(self) -> str:
        return "Jikan (MyAnimeList)"

    @property
    def description(self) -> str:
        return "Búsqueda en MyAnimeList para Mangas y Novelas Ligeras."

    def test_connection(self) -> Tuple[bool, str]:
        """Prueba buscando 'One Piece'."""
        try:
            url = f"{self.API_BASE_URL}/manga"
            params = {"q": "One Piece", "limit": 1}
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                return True, "Conexión exitosa con MyAnimeList"
            elif response.status_code == 429:
                return False, "Error 429: Demasiadas peticiones (Rate Limit)"
            else:
                return False, f"Error HTTP {response.status_code}"
                
        except requests.exceptions.Timeout:
            return False, "Tiempo de espera agotado (Timeout)"
        except Exception as e:
            return False, f"Error inesperado: {str(e)}"

    def search(self, query_str: str) -> List[Dict[str, Any]]:
        """Busca mangas usando la API de Jikan."""
        url = f"{self.API_BASE_URL}/manga"
        params = {"q": query_str, "limit": 5}
        
        try:
            # Jikan tiene rate limiting estricto, a veces un pequeño sleep ayuda
            response = requests.get(url, params=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json().get("data", [])
                results = []
                for item in data:
                    # Normalizamos para que la UI lo entienda bien
                    normalized = {
                        "id": item.get("mal_id"),
                        "title": {
                            "romaji": item.get("title"),
                            "english": item.get("title_english"),
                            "native": item.get("title_japanese")
                        },
                        "subtitle": f"{item.get('type', 'Manga')} - {item.get('chapters', '?')} caps",
                        "description": item.get("synopsis"),
                        "image_url": item.get("images", {}).get("webp", {}).get("large_image_url")
                    }
                    results.append(normalized)
                return results
            else:
                logger.error(f"Error Jikan Search (Status {response.status_code}): {response.text}")
        except Exception:
            logger.exception("Error en búsqueda Jikan")
            
        return []

    def get_details(self, media_id: int) -> Optional[Dict[str, Any]]:
        """Obtiene detalles completos de un manga."""
        url = f"{self.API_BASE_URL}/manga/{media_id}/full"
        
        try:
            response = requests.get(url, timeout=15)
            if response.status_code == 200:
                item = response.json().get("data", {})
                # Estructura enriquecida para la IA
                return {
                    "id": item.get("mal_id"),
                    "title": {
                        "romaji": item.get("title"),
                        "english": item.get("title_english"),
                        "native": item.get("title_japanese")
                    },
                    "description": item.get("synopsis"),
                    "background": item.get("background"),
                    "type": item.get("type"),
                    "chapters": item.get("chapters"),
                    "volumes": item.get("volumes"),
                    "status": item.get("status"),
                    "genres": [g.get("name") for g in item.get("genres", [])],
                    "authors": [a.get("name") for a in item.get("authors", [])],
                    "url": item.get("url")
                }
            else:
                logger.error(f"Error Jikan Details (Status {response.status_code})")
        except Exception:
            logger.exception(f"Error detalle Jikan ID {media_id}")
            
        return None
