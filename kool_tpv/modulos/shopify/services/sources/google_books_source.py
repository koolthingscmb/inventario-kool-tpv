import logging
import requests
from typing import List, Dict, Any, Optional, Tuple
from .base_source import BaseSource
from ..shopify_config_service import ShopifyConfigService
from kool_tpv.base_datos.db_wrapper import Database

logger = logging.getLogger(__name__)

class GoogleBooksSource(BaseSource):
    """Implementación de Google Books como fuente de datos para Libros y Mangas."""

    API_BASE_URL = "https://www.googleapis.com/books/v1/volumes"

    def __init__(self, db: Optional[Database] = None):
        self.db = db
        # No cacheamos la API Key aquí para que se lea en tiempo real de la DB

    def _get_api_key(self) -> str:
        """Obtiene la API Key actualizada desde la base de datos."""
        if not self.db:
            return ""
        try:
            config = ShopifyConfigService(self.db).get_config()
            return config.get("google_api_key", "")
        except Exception:
            return ""

    @property
    def id(self) -> str:
        return "source_google_books"

    @property
    def name(self) -> str:
        return "Google Books"

    @property
    def description(self) -> str:
        return "Buscador global de libros (ideal para ediciones españolas e ISBN)."

    def _get_params(self, base_params: Dict[str, Any]) -> Dict[str, Any]:
        """Añade la API Key a los parámetros si está disponible."""
        key = self._get_api_key()
        if key:
            base_params["key"] = key
        return base_params

    def test_connection(self) -> Tuple[bool, str]:
        """Prueba de conexión básica."""
        try:
            params = self._get_params({"q": "20th Century Boys", "maxResults": 1})
            response = requests.get(self.API_BASE_URL, params=params, timeout=10)
            
            if response.status_code == 200:
                return True, "Conexión exitosa con Google Books"
            elif response.status_code == 429:
                return False, "Error 429: Límite de cuota excedido"
            else:
                # Intentar extraer el mensaje de error de Google
                try:
                    err_data = response.json()
                    msg = err_data.get("error", {}).get("message", f"Error HTTP {response.status_code}")
                    return False, f"Google API Error: {msg}"
                except:
                    return False, f"Error HTTP {response.status_code}"
                
        except Exception as e:
            return False, f"Error inesperado: {str(e)}"

    def search(self, query_str: str, **kwargs) -> List[Dict[str, Any]]:
        """Busca libros en Google Books usando un filtro de título estricto."""
        search_query = query_str.strip()
        context = kwargs.get('context', '')
        
        # Usamos el contexto dinámico (ej: 'manga') en lugar de dejarlo fijo
        if context:
            refined_query = f'intitle:"{search_query}" +{context}'
        else:
            refined_query = f'intitle:"{search_query}"'
        
        params = self._get_params({
            "q": refined_query,
            "maxResults": 15,
            "langRestrict": "es",
            "orderBy": "relevance",
            "printType": "books"
        })
        
        try:
            logger.info(f"Buscando en Google Books (Query Estricta): {refined_query}")
            response = requests.get(self.API_BASE_URL, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                items = data.get("items", [])
                results = []
                
                for item in items:
                    info = item.get("volumeInfo", {})
                    
                    # Extraer autores
                    authors = info.get("authors", [])
                    author_str = ", ".join(authors) if authors else ""
                    
                    # Imagen
                    image_url = info.get("imageLinks", {}).get("thumbnail", "")
                    if image_url:
                        image_url = image_url.replace("http://", "https://")

                    normalized = {
                        "id": item.get("id"),
                        "title": {
                            "romaji": info.get("title"),
                            "english": info.get("title"),
                            "native": ""
                        },
                        "subtitle": f"Autor: {author_str}" if author_str else "Libro/Manga",
                        "image_url": image_url,
                        "_source_id": self.id,
                        "_source_name": self.name
                    }
                    results.append(normalized)
                return results
        except Exception:
            logger.exception("Error en búsqueda Google Books")
            
        return []

    def get_details(self, media_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene detalles completos de un libro en Google Books."""
        url = f"{self.API_BASE_URL}/{media_id}"
        params = self._get_params({})
        
        try:
            logger.info(f"Solicitando detalles Google Books para ID: {media_id}")
            response = requests.get(url, params=params, timeout=15)
            if response.status_code == 200:
                item = response.json()
                info = item.get("volumeInfo", {})
                logger.info(f"Detalles obtenidos correctamente para: {info.get('title')}")
                
                return {
                    "id": item.get("id"),
                    "title": info.get("title"),
                    "subtitle": info.get("subtitle"),
                    "authors": info.get("authors", []),
                    "publisher": info.get("publisher"),
                    "publishedDate": info.get("publishedDate"),
                    "description": info.get("description", ""),
                    "pageCount": info.get("pageCount"),
                    "categories": info.get("categories", []),
                    "image_url": info.get("imageLinks", {}).get("thumbnail", ""),
                    "language": info.get("language"),
                    "isbn": [i.get("identifier") for i in info.get("industryIdentifiers", [])],
                    "source": "Google Books"
                }
            else:
                logger.error(f"Error Google Books get_details (Status {response.status_code}): {response.text}")
        except Exception:
            logger.exception(f"Error detalle Google Books ID {media_id}")
            
        return None
