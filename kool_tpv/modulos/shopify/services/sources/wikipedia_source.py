import logging
import re
import requests
from typing import List, Dict, Any, Optional, Tuple
from .base_source import BaseSource
from .manga_data import MangaData

logger = logging.getLogger(__name__)

class WikipediaSource(BaseSource):
    """Wikipedia como fuente para el título original (romaji/kanji) y demografía.

    Soporta varios idiomas vía `lang` ('es', 'en'). No se registra en
    SourceManager: se usa solo en el flujo OBTENER y como gap-fill,
    para no contaminar el diálogo general de BUSCAR DATA.
    """

    HEADERS = {"User-Agent": "KoolTPV/1.0 (TPV de tienda; consulta de titulos originales)"}

    def __init__(self, lang: str = 'es'):
        self.lang = lang
        self.api_url = f"https://{lang}.wikipedia.org/w/api.php"

    @property
    def id(self) -> str:
        return f"source_wikipedia_{self.lang}"

    @property
    def name(self) -> str:
        return f"Wikipedia ({self.lang.upper()})"

    @property
    def description(self) -> str:
        return "Artículos de Wikipedia; extrae título original japonés y demografía del infobox."

    def test_connection(self) -> Tuple[bool, str]:
        try:
            response = requests.get(self.api_url, params={
                'action': 'opensearch', 'search': 'Naruto',
                'limit': 1, 'namespace': 0, 'format': 'json'
            }, headers=self.HEADERS, timeout=10)
            if response.status_code == 200:
                return True, f"Conexión exitosa con Wikipedia ({self.lang})"
            return False, f"Error HTTP {response.status_code}"
        except Exception as e:
            return False, f"Error inesperado: {str(e)}"

    def search(self, query_str: str, **kwargs) -> List[Dict[str, Any]]:
        """Busca páginas con la API opensearch."""
        params = {
            'action': 'opensearch',
            'search': query_str,
            'limit': 5,
            'namespace': 0,
            'format': 'json'
        }
        try:
            response = requests.get(self.api_url, params=params, headers=self.HEADERS, timeout=15)
            if response.status_code == 200:
                data = response.json()
                titles, descs = data[1], data[2]
                results = []
                for i, t in enumerate(titles):
                    results.append({
                        'id': t,  # el identificador es el propio título de la página
                        'title': {'romaji': t, 'english': '', 'native': ''},
                        'subtitle': descs[i] if i < len(descs) else '',
                        'description': '',
                        'image_url': ''
                    })
                return results
            logger.error(f"Error Wikipedia Search (Status {response.status_code})")
        except Exception:
            logger.exception("Error en búsqueda Wikipedia")
        return []

    def get_details(self, page_title: str) -> Optional[Dict[str, Any]]:
        """Descarga el wikitexto y extrae nihongo (romaji/kanji) + demografía."""
        params = {
            'action': 'parse',
            'page': page_title,
            'prop': 'wikitext',
            'format': 'json',
            'redirects': 1
        }
        try:
            response = requests.get(self.api_url, params=params, headers=self.HEADERS, timeout=15)
            if response.status_code == 200:
                wikitext = (response.json().get('parse', {})
                            .get('wikitext', {}).get('*', ''))
                romaji, nativo = self._extract_nihongo(wikitext)
                demographic = self._extract_demographic(wikitext)
                return {
                    'id': page_title,
                    'title': page_title,
                    'romaji': romaji,
                    'native': nativo,
                    'demographic': demographic,
                    'source': self.name
                }
            logger.error(f"Error Wikipedia Details (Status {response.status_code})")
        except Exception:
            logger.exception(f"Error detalle Wikipedia '{page_title}'")
        return None

    def _extract_nihongo(self, wikitext: str) -> Tuple[str, str]:
        """Extrae (romaji, kanji) de la plantilla nihongo según el idioma.

        es.wiki: {{nihongo|romaji|kanji|...}}
        en.wiki: {{nihongo|lead|kanji|romaji|...}}  (romaji opcional si coincide con el lead)
        """
        match = re.search(r'\{\{\s*[Nn]ihongo\s*\|([^\n}]*)\}\}', wikitext or '')
        if not match:
            return '', ''
        params = match.group(1).split('|')
        if self.lang == 'en':
            kanji = self._clean_wiki(params[1]) if len(params) > 1 else ''
            romaji = self._clean_wiki(params[2]) if len(params) > 2 else self._clean_wiki(params[0])
        else:
            romaji = self._clean_wiki(params[0]) if params else ''
            kanji = self._clean_wiki(params[1]) if len(params) > 1 else ''
        return romaji, kanji

    def _extract_demographic(self, wikitext: str) -> str:
        """Extrae la demografía del infobox (|demographic= / |demografía=)."""
        match = re.search(r'\|\s*(?:demographic|demograf[íi]a)\s*=\s*([^\n]+)',
                          wikitext or '', re.IGNORECASE)
        if not match:
            return ''
        return self._clean_wiki(match.group(1))

    def _clean_wiki(self, text: str) -> str:
        """Limpia marcado wiki básico: cursivas, enlaces, refs."""
        text = re.sub(r"''+", '', text)
        text = re.sub(r'\[\[(?:[^]|]*\|)?([^]]*)\]\]', r'\1', text)
        text = re.sub(r'<[^>]+>', '', text)
        return text.strip()

    def normalize(self, raw: Dict[str, Any]) -> MangaData:
        md = MangaData()
        if not raw:
            return md
        md.titulo_romaji = raw.get('romaji') or ''
        md.titulo_nativo = raw.get('native') or ''
        md.demografia = raw.get('demographic') or ''
        return md
