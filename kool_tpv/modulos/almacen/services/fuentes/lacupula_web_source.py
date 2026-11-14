"""Fuente La Cúpula: web pública lacupula.com (WooCommerce, sin login).

Su buscador no indexa el ISBN (que guarda en el SKU CON guiones,
`978-84-10264-14-4`), así que `buscar()` recibe el NOMBRE del producto y lo
empareja con los slugs del sitemap de productos (`product-sitemap.xml`).
Cada candidata se pide a la API pública de WooCommerce (título, SKU,
sinopsis, imágenes, categorías y etiquetas) y su página HTML aporta el
autor (enlace `/autores/` del summary) y el enlace "Previsualizar" de
calameo, que se devuelve como link de avance.

El servicio verifica la ficha comparando su EAN (SKU sin guiones) con el
EAN escaneado. Solo lectura.
"""
import html as _html
import json
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

_MAX_CANDIDATAS = 6
_CACHE_SEGUNDOS = 3600
_cache_slugs: Dict[str, tuple] = {}   # url_base -> (momento, [slugs])


def _norm(texto: str) -> str:
    """Minúsculas sin acentos ni signos ni ceros a la izquierda del número
    de tomo: para comparar nombres y slugs."""
    t = unicodedata.normalize("NFKD", texto or "")
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"[^a-z0-9]+", "", t.lower())
    return re.sub(r"(?<!\d)0+(?=\d)", "", t)


def _texto(html: str) -> str:
    return re.sub(r"\s+", " ", _html.unescape(
        re.sub(r"<[^>]+>", " ", html or ""))).strip()


class LacupulaWebSource(BaseFuente):
    """Web pública de La Cúpula. `buscar` recibe el NOMBRE, no el EAN."""

    # Marca para el servicio: busca por nombre y verifica por ISBN
    busca_por_nombre = True

    def __init__(self, url: str, timeout: int = 20):
        self.url_base = (url or "").rstrip("/")
        self.timeout = timeout

    @property
    def id(self) -> str:
        return "lacupula_web"

    # ---------- sitemap ----------

    def _slugs(self) -> List[str]:
        """Slugs de todos los productos (product-sitemap.xml, en caché 1 h)."""
        hecho = _cache_slugs.get(self.url_base)
        if hecho and time.time() - hecho[0] < _CACHE_SEGUNDOS:
            return hecho[1]
        try:
            r = requests.get(f"{self.url_base}/product-sitemap.xml",
                             headers=_UA, timeout=self.timeout)
            slugs = re.findall(
                r"<loc>[^<]*/catalogo/([^/<]+)/?</loc>", r.text)
        except Exception:
            logger.exception("No se pudo leer el sitemap de %s", self.url_base)
            return []
        if slugs:
            _cache_slugs[self.url_base] = (time.time(), slugs)
        return slugs

    # ---------- búsqueda y ficha ----------

    def buscar(self, consulta: str) -> List[Dict[str, Any]]:
        """Fichas candidatas cuyo slug casa con el nombre (sin verificar EAN)."""
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
        """API de WooCommerce (datos) + página HTML (autor y avance)."""
        try:
            r = requests.get(f"{self.url_base}/wp-json/wc/store/v1/products",
                             params={"slug": slug}, headers=_UA,
                             timeout=self.timeout)
            datos = r.json() if r.status_code == 200 else []
        except Exception:
            logger.exception("No se pudo abrir la ficha %s", slug)
            return None
        if not datos:
            return None
        ficha = self._normalizar(datos[0])
        self._completar_desde_html(ficha)
        return ficha

    # ---------- página HTML: autor y avance ----------

    def _completar_desde_html(self, ficha: Dict[str, Any]) -> None:
        """Autor = primer enlace /autores/ tras product_title; avance =
        primer enlace calameo del summary (los siguientes son relacionados)."""
        try:
            r = requests.get(ficha["url_ficha"], headers=_UA,
                             timeout=self.timeout)
            if r.status_code != 200:
                return
            seg = r.text[r.text.find("product_title"):]
        except Exception:
            logger.exception("No se pudo leer la página de %s",
                             ficha["url_ficha"])
            return
        m = re.search(r'/autores/[^/"]+/"[^>]*>.*?<span>([^<]+)</span>',
                      seg, flags=re.S)
        if m:
            ficha["autor"] = _html.unescape(m.group(1)).strip()
        m = re.search(r'href="(https?://[^"]*calameo[^"]*)"', seg)
        if m:
            ficha["links"] = [
                {"url": ficha["url_ficha"], "etiqueta": "Ficha"},
                {"url": _html.unescape(m.group(1)), "etiqueta": "Avance"},
            ]

    # ---------- parseo ----------

    def _normalizar(self, p: Dict[str, Any]) -> Dict[str, Any]:
        sku = (p.get("sku") or "").strip()
        categorias = [_html.unescape(c.get("name", ""))
                      for c in p.get("categories") or []]
        tags = [_html.unescape(t.get("name", ""))
                for t in p.get("tags") or []]
        imagenes: List[str] = []
        for im in p.get("images") or []:
            if im.get("src") and im["src"] not in imagenes:
                imagenes.append(im["src"])
        return {
            "titulo": _html.unescape(p.get("name") or ""),
            "titulo_original": "",
            "autor": "",
            "editorial": "",
            "isbn": sku,
            "ean": re.sub(r"[^0-9]", "", sku),
            "coleccion": "",
            "generos": [],
            "candidatos_meta": categorias + tags,
            "sinopsis": _texto(p.get("description")),
            "imagen_url": imagenes[0] if imagenes else "",
            "imagenes": imagenes,
            "links": [],
            "url_ficha": p.get("permalink") or "",
        }

    # ---------- prueba ----------

    def probar(self) -> tuple:
        """La web es pública: basta comprobar que la API responde."""
        try:
            r = requests.get(f"{self.url_base}/wp-json/wc/store/v1/products",
                             params={"per_page": 1}, headers=_UA,
                             timeout=self.timeout)
            if r.status_code == 200:
                return (True, "Acceso correcto a lacupula.com")
            return (False, f"lacupula.com respondió {r.status_code}")
        except Exception as e:
            return (False, f"No se pudo conectar con lacupula.com: {e}")
