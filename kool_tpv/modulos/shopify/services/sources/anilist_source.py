import logging
import requests
from typing import List, Dict, Any, Optional, Tuple
from .base_source import BaseSource
from .manga_data import MangaData

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

    def test_connection(self) -> Tuple[bool, str]:
        """Prueba buscando 'Dragon Ball'."""
        try:
            query = """
            query ($search: String) {
              Page (page: 1, perPage: 1) {
                media (search: $search, type: MANGA) {
                  id
                }
              }
            }
            """
            response = requests.post(self.API_URL, json={'query': query, 'variables': {'search': 'Dragon Ball'}}, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if "errors" in data:
                    err_msg = data["errors"][0].get("message", "Error desconocido en AniList")
                    return False, f"Error API: {err_msg}"
                return True, "Conexión exitosa"
            
            elif response.status_code == 403:
                try:
                    err_data = response.json()
                    msg = err_data.get("errors", [{}])[0].get("message", "Acceso prohibido (403)")
                    return False, f"AniList Desactivado: {msg}"
                except:
                    return False, "Error 403: Acceso prohibido por AniList"
            
            return False, f"Error HTTP {response.status_code}"
            
        except requests.exceptions.Timeout:
            return False, "Tiempo de espera agotado (Timeout)"
        except Exception as e:
            return False, f"Error inesperado: {str(e)}"

    def search(self, query_str: str, **kwargs) -> List[Dict[str, Any]]:
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
            response = requests.post(self.API_URL, json={'query': query, 'variables': {'search': query_str}}, timeout=15)
            if response.status_code == 200:
                return response.json().get("data", {}).get("Page", {}).get("media", [])
            else:
                logger.error(f"Error AniList (Status {response.status_code}): {response.text}")
        except requests.exceptions.Timeout:
            logger.warning("Timeout en búsqueda AniList (sin respuesta en 15s)")
        except Exception as e:
            logger.exception(f"Error inesperado en búsqueda AniList: {str(e)}")
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
            startDate { year }
            staff(page: 1, perPage: 6) { edges { role node { name { full } } } }
          }
        }
        """
        try:
            response = requests.post(self.API_URL, json={'query': query, 'variables': {'id': media_id}}, timeout=15)
            if response.status_code == 200:
                return response.json().get("data", {}).get("Media")
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout en detalle AniList {media_id} (sin respuesta en 15s)")
        except Exception:
            logger.exception(f"Error detalle AniList {media_id}")
        return None

    def normalize(self, raw: Dict[str, Any]) -> MangaData:
        md = MangaData()
        if not raw:
            return md
        title = raw.get('title') or {}
        md.titulo_romaji = title.get('romaji') or ''
        md.titulo_nativo = title.get('native') or ''
        md.generos = list(raw.get('genres') or [])
        md.sinopsis = raw.get('description') or ''
        md.estado = raw.get('status') or ''
        start = raw.get('startDate') or {}
        if start.get('year'):
            md.anio = str(start['year'])
        for edge in (raw.get('staff') or {}).get('edges') or []:
            role = (edge.get('role') or '').lower()
            if 'story' in role or 'art' in role:
                name = ((edge.get('node') or {}).get('name') or {}).get('full')
                if name:
                    md.autor = name
                    break
        return md
