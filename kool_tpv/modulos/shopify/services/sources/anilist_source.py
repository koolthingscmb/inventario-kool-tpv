import logging
import requests
from typing import List, Dict, Any, Optional
from .base_source import BaseSource

logger = logging.getLogger(__name__)

class AniListSource(BaseSource):
    """Implementación de AniList como fuente de datos enchufable."""

    API_URL = "https://graphql.anilist.co"

    @property
    def id(self) -> str:
        return "source_anilist"

    @property
    def name(self) -> str:
        return "AniList (Manga / Anime)"

    @property
    def description(self) -> str:
        return "Búsqueda de títulos, autores y sinopsis para mangas."

    def test_connection(self) -> bool:
        """Prueba buscando 'Dragon Ball'."""
        try:
            results = self.search("Dragon Ball")
            return len(results) > 0
        except Exception:
            return False

    def search(self, query_str: str) -> List[Dict[str, Any]]:
        query = """
        query ($search: String) {
          Page (page: 1, perPage: 5) {
            media (search: $search, type: MANGA, format: MANGA) {
              id
              title { romaji english native }
              description
              coverImage { large extraLarge }
            }
          }
        }
        """
        try:
            response = requests.post(self.API_URL, json={'query': query, 'variables': {'search': query_str}}, timeout=10)
            if response.status_code == 200:
                return response.json().get("data", {}).get("Page", {}).get("media", [])
        except Exception:
            logger.exception("Error en búsqueda AniList")
        return []

    def get_details(self, media_id: int) -> Optional[Dict[str, Any]]:
        query = """
        query ($id: Int) {
          Media (id: $id, type: MANGA) {
            id
            title { romaji english native }
            description
            coverImage { extraLarge }
            genres
            status
          }
        }
        """
        try:
            response = requests.post(self.API_URL, json={'query': query, 'variables': {'id': media_id}}, timeout=10)
            if response.status_code == 200:
                return response.json().get("data", {}).get("Media")
        except Exception:
            logger.exception(f"Error detalle AniList {media_id}")
        return None
