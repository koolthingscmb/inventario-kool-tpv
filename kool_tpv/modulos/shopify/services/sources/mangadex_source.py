import logging
import requests
from typing import List, Dict, Any, Optional, Tuple
from .base_source import BaseSource
from .manga_data import MangaData

logger = logging.getLogger(__name__)

class MangaDexSource(BaseSource):
    """Implementación de MangaDex como fuente de datos para Mangas."""

    API_BASE_URL = "https://api.mangadex.org"
    CDN_URL = "https://uploads.mangadex.org"

    @property
    def id(self) -> str:
        return "source_mangadex"

    @property
    def name(self) -> str:
        return "MangaDex"

    @property
    def description(self) -> str:
        return "Base de datos abierta con soporte multilingüe (incluye español)."

    def test_connection(self) -> Tuple[bool, str]:
        """Prueba de conexión básica."""
        try:
            url = f"{self.API_BASE_URL}/manga"
            params = {"title": "One Piece", "limit": 1}
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                return True, "Conexión exitosa con MangaDex"
            else:
                return False, f"Error HTTP {response.status_code}"
                
        except Exception as e:
            return False, f"Error inesperado: {str(e)}"

    def search(self, query_str: str) -> List[Dict[str, Any]]:
        """Busca mangas en MangaDex."""
        url = f"{self.API_BASE_URL}/manga"
        # Incluimos cover_art en los detalles para tener la imagen
        params = {
            "title": query_str, 
            "limit": 5,
            "includes[]": ["cover_art", "author"]
        }
        
        try:
            response = requests.get(url, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json().get("data", [])
                results = []
                for item in data:
                    attrs = item.get("attributes", {})
                    
                    # Extraer imagen de portada
                    cover_filename = ""
                    for rel in item.get("relationships", []):
                        if rel.get("type") == "cover_art":
                            cover_filename = rel.get("attributes", {}).get("fileName", "")
                            break
                    
                    image_url = ""
                    if cover_filename:
                        image_url = f"{self.CDN_URL}/covers/{item['id']}/{cover_filename}"

                    # Extraer autor
                    author = ""
                    for rel in item.get("relationships", []):
                        if rel.get("type") == "author":
                            author = rel.get("attributes", {}).get("name", "")
                            break

                    normalized = {
                        "id": item.get("id"),
                        "title": {
                            "romaji": attrs.get("title", {}).get("en") or attrs.get("title", {}).get("ja-ro"),
                            "english": attrs.get("title", {}).get("en"),
                            "native": attrs.get("title", {}).get("ja")
                        },
                        "subtitle": f"Autor: {author}" if author else "Manga",
                        "description": attrs.get("description", {}).get("es") or attrs.get("description", {}).get("en"),
                        "image_url": image_url
                    }
                    results.append(normalized)
                return results
        except Exception:
            logger.exception("Error en búsqueda MangaDex")
            
        return []

    def get_details(self, media_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene detalles completos de un manga en MangaDex."""
        url = f"{self.API_BASE_URL}/manga/{media_id}"
        params = {"includes[]": ["author", "artist", "cover_art"]}
        
        try:
            response = requests.get(url, params=params, timeout=15)
            if response.status_code == 200:
                item = response.json().get("data", {})
                attrs = item.get("attributes", {})
                
                # Extraer autor y artista
                authors = []
                artists = []
                cover_filename = ""
                
                for rel in item.get("relationships", []):
                    rtype = rel.get("type")
                    if rtype == "author":
                        authors.append(rel.get("attributes", {}).get("name"))
                    elif rtype == "artist":
                        artists.append(rel.get("attributes", {}).get("name"))
                    elif rtype == "cover_art":
                        cover_filename = rel.get("attributes", {}).get("fileName")

                image_url = ""
                if cover_filename:
                    image_url = f"{self.CDN_URL}/covers/{item['id']}/{cover_filename}"

                return {
                    "id": item.get("id"),
                    "title": attrs.get("title"),
                    "altTitles": attrs.get("altTitles"),
                    "description": attrs.get("description", {}).get("es") or attrs.get("description", {}).get("en"),
                    "status": attrs.get("status"),
                    "year": attrs.get("year"),
                    "contentRating": attrs.get("contentRating"),
                    "tags": [t.get("attributes", {}).get("name", {}).get("en") for t in attrs.get("tags", [])],
                    "authors": authors,
                    "artists": artists,
                    "image_url": image_url,
                    "source": "MangaDex"
                }
        except Exception:
            logger.exception(f"Error detalle MangaDex ID {media_id}")
            
        return None

    def normalize(self, raw: Dict[str, Any]) -> MangaData:
        md = MangaData()
        if not raw:
            return md
        title = raw.get('title') or {}
        # altTitles es una lista de dicts {codigo_idioma: titulo}
        alt = {}
        for entry in raw.get('altTitles') or []:
            for lang, value in entry.items():
                alt.setdefault(lang, value)
        md.titulo_romaji = alt.get('ja-ro') or title.get('ja-ro') or title.get('en') or ''
        md.titulo_nativo = alt.get('ja') or title.get('ja') or ''
        authors = raw.get('authors') or []
        md.autor = authors[0] if authors else ''
        if raw.get('year'):
            md.anio = str(raw['year'])
        md.generos = list(raw.get('tags') or [])
        md.sinopsis = raw.get('description') or ''
        md.estado = raw.get('status') or ''
        return md
