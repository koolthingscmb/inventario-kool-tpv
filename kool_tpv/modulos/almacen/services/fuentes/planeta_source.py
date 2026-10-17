"""Fuente Planeta: portal B2B distribucion.planetacomic.com.

Login: GET / (token `_csrf_token`) + POST /login/ con `_username`/`_password`.
Búsqueda: GET /ajax/libros/listado/?category_id=1&filters[text]=<q>&view_type=list
  -> JSON {view: tabla html con título/autor/EAN13/PVP y enlace a la ficha}.
Detalle: /libro/<slug>/<id>/ -> sinopsis en .product-list_summary-content y
  datos técnicos en pares .technical-data_title / .technical-data_value
  (Título original, Colección, ISBN, EAN, Formato, Nº de páginas, Publicación...).

Ojo: mandar filtros extra o `order_by` puede dar 500 en el portal; usar la
petición mínima de abajo. Solo lectura. Credenciales por parámetro.
"""
import html as _html
import logging
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import requests

from .base_fuente import BaseFuente

logger = logging.getLogger(__name__)

_UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}


class PlanetaSource(BaseFuente):
    """Portal de distribución de Planeta: login + búsqueda + ficha."""

    def __init__(self, url: str, credenciales: Dict[str, str], timeout: int = 20):
        self.url_base = url.rstrip("/")
        self.creds = credenciales or {}
        self.timeout = timeout
        self._sesion: Optional[requests.Session] = None

    @property
    def id(self) -> str:
        return "planeta"

    def _entrar(self) -> bool:
        """GET portada (token CSRF) + POST /login/. True si hay sesión."""
        s = requests.Session()
        s.headers.update(_UA)
        try:
            r = s.get(self.url_base + "/", timeout=self.timeout)
            m = re.search(r'name="_csrf_token"\s+value="([^"]+)"', r.text)
            if not m:
                return False
            r = s.post(f"{self.url_base}/login/",
                       data={"_username": self.creds.get("usuario", ""),
                             "_password": self.creds.get("password", ""),
                             "_csrf_token": m.group(1)},
                       timeout=self.timeout)
            if "logout" not in r.text and "logged" not in r.text:
                return False
            self._sesion = s
            return True
        except Exception:
            logger.exception("Error de conexión con %s", self.url_base)
            return False

    # ---------- búsqueda y ficha ----------

    def buscar(self, consulta: str) -> List[Dict[str, Any]]:
        """Búsqueda por EAN/ISBN/título. Devuelve resultados normalizados."""
        consulta = (consulta or "").strip()
        if not consulta:
            return []
        if self._sesion is None and not self._entrar():
            return []
        try:
            # petición mínima: más parámetros pueden hacer fallar el endpoint
            r = self._sesion.get(
                f"{self.url_base}/ajax/libros/listado/",
                params={"category_id": "1", "filters[text]": consulta,
                        "view_type": "list", "limit": 20, "offset": 0, "page": 1},
                timeout=self.timeout)
            if r.status_code != 200:
                return []
            vista = r.json().get("view", "")
            return self._parsear_tabla(vista)
        except Exception:
            logger.exception("Error buscando en Planeta")
            return []

    def _parsear_tabla(self, vista: str) -> List[Dict[str, Any]]:
        """Filas de la tabla: título(enlace a ficha), autor, EAN13, PVP."""
        resultados = []
        for fila in re.findall(r"<tr>(.*?)</tr>", vista, flags=re.S):
            enlace = re.search(
                r'class="title-cell"[^>]*>\s*<a href="([^"]+)">([^<]+)</a>', fila)
            if not enlace:
                continue
            autor = re.search(r'class="author-cell"[^>]*>\s*([^<]+)', fila)
            ean = re.search(r'class="ean-cell"[^>]*>\s*([^<]+)', fila)
            resultados.append({
                "titulo": _html.unescape(enlace.group(2)).strip(),
                "titulo_original": "",
                "autor": _html.unescape(autor.group(1)).strip() if autor else "",
                "anio": "",
                "editorial": "",
                "isbn": "",
                "ean": ean.group(1).strip() if ean else "",
                "coleccion": "",
                "generos": [],
                "sinopsis": "",
                "imagen_url": "",
                "url_ficha": urljoin(self.url_base, enlace.group(1)),
                "_ci": enlace.group(1),
            })
        return resultados

    def detalle(self, identificador: Any) -> Optional[Dict[str, Any]]:
        """Ficha completa. `identificador` es el dict de buscar() o su URL."""
        if self._sesion is None and not self._entrar():
            return None
        url = identificador.get("url_ficha") if isinstance(identificador, dict) \
            else str(identificador)
        if not url:
            return None
        try:
            r = self._sesion.get(url, timeout=self.timeout)
            if r.status_code != 200:
                return None
            return self._parsear_ficha(r.text, url)
        except Exception:
            logger.exception("Error en ficha %s de Planeta", url)
            return None

    def _parsear_ficha(self, html: str, url: str) -> Dict[str, Any]:
        """Sinopsis en product-list_summary-content y pares título/valor
        de la tabla technical-data."""
        sinopsis = ""
        m = re.search(r'class="product-list_summary-content"[^>]*>(.*?)</div>',
                      html, flags=re.S)
        if m:
            sinopsis = _html.unescape(re.sub(r"<[^>]+>", " ", m.group(1))).strip()
            sinopsis = re.sub(r"\s+", " ", sinopsis)

        datos = {}
        for m in re.finditer(
                r'class="technical-data_title[^"]*">(.*?)</(?:div|span|p|td)>'
                r'.*?class="technical-data_value[^"]*">(.*?)</(?:div|span|p|td)>',
                html, flags=re.S):
            k = _html.unescape(re.sub(r"<[^>]+>", " ", m.group(1))).strip()
            v = _html.unescape(re.sub(r"<[^>]+>", " ", m.group(2))).strip()
            datos[re.sub(r"\s+", " ", k)] = re.sub(r"\s+", " ", v)

        titulo = ""
        m = re.search(r"<title>([^<]+)</title>", html)
        if m:
            titulo = m.group(1).split(" - ")[0].strip()

        imagen = ""
        for pat in (r'property="og:image" content="([^"]+)"',
                    r'src="([^"]*thumbnails[^"]*)"'):
            m = re.search(pat, html)
            if m:
                imagen = urljoin(self.url_base, m.group(1))
                break

        anio = ""
        m = re.search(r"(\d{4})", datos.get("Publicación", ""))
        if m:
            anio = m.group(1)

        return {
            "titulo": titulo,
            "titulo_original": datos.get("Título original", ""),
            "autor": "",
            "anio": anio,
            "editorial": datos.get("Editorial", "Planeta Cómic"),
            "isbn": datos.get("ISBN", ""),
            "ean": datos.get("EAN", ""),
            "coleccion": datos.get("Colección", ""),
            "generos": [],
            "sinopsis": sinopsis,
            "imagen_url": imagen,
            "url_ficha": url,
        }

    # ---------- prueba ----------

    def probar(self) -> tuple:
        if self._entrar():
            return (True, "Login correcto en Planeta")
        return (False, f"No se pudo iniciar sesión en {self.url_base}")
