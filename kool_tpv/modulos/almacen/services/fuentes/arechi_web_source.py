"""Fuente Arechi Manga: web pública arechimanga.com (WooCommerce, sin login).

Su API pública guarda el ISBN en el SKU CON guiones (`979-13-87822-41-5`),
que no se pueden deducir del EAN, y su buscador falla con los apóstrofos
(`Cat´s`). Por eso `buscar()` recibe el NOMBRE del producto y lo empareja con
los slugs del sitemap de productos (público, en `sitemap_index.xml`), sin
signos ni espacios. Cada candidata se pide a la API por slug y el servicio la
verifica comparando su ISBN con el EAN escaneado (sin guiones).

La ficha aporta: título, autor (`Guion y dibujo:`, `Guion:`/`Dibujo:` o las
etiquetas de autor), sinopsis (`description`), demografía (categoría) e
imágenes a tamaño original. No hay año de publicación. No se importan precios
ni géneros.

Solo lectura.
"""
import html as _html
import logging
import re
import time
import unicodedata
from typing import Any, Dict, List, Optional

import requests

from .base_fuente import BaseFuente

logger = logging.getLogger(__name__)

_UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 Chrome/120.0 Safari/537.36"}

# categorías de la web que son demografía (el resto son géneros, serie o estado)
_DEMOGRAFIAS = {"shonen", "seinen", "shojo", "josei", "kodomo", "yaoi",
                "yuri", "bl"}

_MAX_CANDIDATAS = 6
_CACHE_SEGUNDOS = 3600
_cache_slugs: Dict[str, tuple] = {}   # url_base -> (momento, [slugs])


def _norm(texto: str) -> str:
    """Minúsculas sin acentos ni signos ni ceros a la izquierda del número
    de tomo ('Smiley 06' == 'smiley-6'): para comparar nombres y slugs."""
    t = unicodedata.normalize("NFKD", texto or "")
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"[^a-z0-9]+", "", t.lower())
    return re.sub(r"(?<!\d)0+(?=\d)", "", t)


def _texto(html: str) -> str:
    return re.sub(r"\s+", " ", _html.unescape(
        re.sub(r"<[^>]+>", " ", html or ""))).strip()


class ArechiWebSource(BaseFuente):
    """Web pública de Arechi Manga. `buscar` recibe el NOMBRE, no el EAN."""

    # Marca para el servicio: busca por nombre y verifica por ISBN
    busca_por_nombre = True

    def __init__(self, url: str, timeout: int = 20):
        self.url_base = (url or "").rstrip("/")
        self.timeout = timeout

    @property
    def id(self) -> str:
        return "arechi_web"

    # ---------- sitemap ----------

    def _slugs(self) -> List[str]:
        """Slugs de todos los productos (sitemap de productos, en caché 1 h)."""
        hecho = _cache_slugs.get(self.url_base)
        if hecho and time.time() - hecho[0] < _CACHE_SEGUNDOS:
            return hecho[1]
        slugs: List[str] = []
        try:
            r = requests.get(f"{self.url_base}/sitemap_index.xml",
                             headers=_UA, timeout=self.timeout)
            for loc in re.findall(r"<loc>([^<]+)</loc>", r.text):
                if "product" not in loc or "_cat" in loc or "_tag" in loc:
                    continue
                s = requests.get(loc, headers=_UA, timeout=self.timeout)
                slugs += re.findall(r"<loc>[^<]*/producto/([^/<]+)/?</loc>",
                                    s.text)
        except Exception:
            logger.exception("No se pudo leer el sitemap de %s", self.url_base)
            return []
        if slugs:
            _cache_slugs[self.url_base] = (time.time(), slugs)
        return slugs

    # ---------- búsqueda y ficha ----------

    def buscar(self, consulta: str) -> List[Dict[str, Any]]:
        """Fichas candidatas cuyo slug casa con el nombre (sin verificar ISBN)."""
        nombre = re.sub(
            r"\b(?:n[ºo°]\.?|núm\.?|vol(?:umen)?\.?|tomo)\s*(?=\d)", "",
            consulta or "", flags=re.I)
        buscado = _norm(nombre)
        if len(buscado) < 3:
            return []
        slugs = self._slugs()
        exactos = [s for s in slugs if _norm(s) == buscado]
        parecidos = [s for s in slugs if s not in exactos and len(_norm(s)) >= 4
                     and (buscado in _norm(s) or _norm(s) in buscado)]
        salida = []
        for slug in (exactos + parecidos)[:_MAX_CANDIDATAS]:
            ficha = self._pedir_ficha(slug)
            if ficha:
                ficha["_ficha"] = True  # detalle() la devuelve tal cual
                salida.append(ficha)
        return salida

    def detalle(self, identificador: Any) -> Optional[Dict[str, Any]]:
        """La ficha ya llega completa desde `buscar()`."""
        if isinstance(identificador, dict) and identificador.get("_ficha"):
            return identificador
        return None

    def _pedir_ficha(self, slug: str) -> Optional[Dict[str, Any]]:
        try:
            r = requests.get(f"{self.url_base}/wp-json/wc/store/v1/products",
                             params={"slug": slug}, headers=_UA,
                             timeout=self.timeout)
            datos = r.json() if r.status_code == 200 else []
        except Exception:
            logger.exception("No se pudo abrir la ficha %s", slug)
            return None
        return self._normalizar(datos[0]) if datos else None

    # ---------- parseo ----------

    def _normalizar(self, p: Dict[str, Any]) -> Dict[str, Any]:
        sku = (p.get("sku") or "").strip()
        corta = _texto(p.get("short_description"))
        categorias = [_html.unescape(c.get("name", ""))
                      for c in p.get("categories") or []]
        imagenes: List[str] = []
        for im in p.get("images") or []:
            if im.get("src") and im["src"] not in imagenes:
                imagenes.append(im["src"])
        return {
            "titulo": _html.unescape(p.get("name") or ""),
            "titulo_original": "",
            "autor": self._autor(corta, p.get("tags") or []),
            "editorial": "",
            "isbn": sku,
            "ean": re.sub(r"[^0-9]", "", sku),
            "coleccion": "",
            "demografia": next((c.upper() for c in categorias
                                if c.lower() in _DEMOGRAFIAS), ""),
            "generos": [],
            "sinopsis": _texto(p.get("description")),
            "imagen_url": imagenes[0] if imagenes else "",
            "imagenes": imagenes,
            "url_ficha": p.get("permalink") or "",
        }

    @staticmethod
    def _autor(descripcion: str, tags: List[Dict[str, Any]]) -> str:
        """'Guion y dibujo: X', 'Guion: A Dibujo: B' o 'Autor: X' (antes de
        'Contiene'); si no, las etiquetas de la ficha."""
        m = re.search(r"Guion y dibujo:\s*(.+?)\s+Contiene\b", descripcion, re.I)
        if m:
            return m.group(1).strip()
        m = re.search(r"Guion:\s*(.+?)\s+Dibujo:\s*(.+?)\s+Contiene\b",
                      descripcion, re.I)
        if m:
            return f"{m.group(1).strip()} / {m.group(2).strip()}"
        m = re.search(r"Autor(?:es|a)?:\s*(.+?)\s+Contiene\b", descripcion, re.I)
        if m:
            return m.group(1).strip()
        return " / ".join(_html.unescape(t.get("name", "")).strip()
                          for t in tags if t.get("name"))

    # ---------- prueba ----------

    def probar(self) -> tuple:
        """La web es pública: basta comprobar que la API responde."""
        try:
            r = requests.get(f"{self.url_base}/wp-json/wc/store/v1/products",
                             params={"per_page": 1}, headers=_UA,
                             timeout=self.timeout)
            if r.status_code == 200:
                return (True, "Acceso correcto a arechimanga.com")
            return (False, f"arechimanga.com respondió {r.status_code}")
        except Exception as e:
            return (False, f"No se pudo conectar con arechimanga.com: {e}")
