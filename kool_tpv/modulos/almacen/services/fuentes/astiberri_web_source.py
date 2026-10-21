"""Fuente Astiberri: web pública astiberri.com (sin login).

El buscador de la web (`/search`) devuelve el catálogo entero y su
robots.txt lo prohíbe a bots, así que NO se usa. En su lugar las fichas
`/products/<slug>` son públicas y publican ISBN y EAN: `buscar()` genera
candidatas de slug a partir del NOMBRE del producto (sin peticiones) y el
servicio verifica cada ficha comparando su EAN con el escaneado — una
candidata equivocada simplemente no coincide y se prueba la siguiente.

La ficha aporta: título (`<h1>`), autor (`h2.product-author` -> enlaces
`/authors/`), propiedades (`ISBN`, `EAN`, `Año de publicación`, `Serie`),
sinopsis oficial (`og:description`, HTML escapado dos veces), las imágenes
del producto (`data-product-summary`) y el enlace 'Descargar avance' (PDF).
No se usan precios ni stock.

Solo lectura.
"""
import html as _html
import json
import logging
import re
import unicodedata
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import requests

from .base_fuente import BaseFuente

logger = logging.getLogger(__name__)

_UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 Chrome/120.0 Safari/537.36"}

_MAX_CANDIDATAS = 8


class AstiberriWebSource(BaseFuente):
    """Web pública de Astiberri. `buscar` recibe el NOMBRE, no el EAN."""

    # Marca para el servicio: busca por nombre y verifica por EAN de la ficha
    busca_por_nombre = True

    def __init__(self, url: str, timeout: int = 20):
        self.url_base = (url or "").rstrip("/")
        self.timeout = timeout

    @property
    def id(self) -> str:
        return "astiberri_web"

    # ---------- búsqueda y ficha ----------

    def buscar(self, consulta: str) -> List[Dict[str, Any]]:
        """Candidatas /products/<slug> generadas del nombre (sin peticiones):
        nombre limpio, sin número de tomo/edición, y quitando palabras del
        final. La ficha buena se reconoce por su EAN en el servicio."""
        return [{"titulo": slug, "url_ficha": f"{self.url_base}/products/{slug}"}
                for slug in self._slugs(consulta)]

    def detalle(self, identificador: Any) -> Optional[Dict[str, Any]]:
        """Descarga y parsea la ficha; None si no es una ficha de producto."""
        url = identificador.get("url_ficha") if isinstance(identificador, dict) \
            else str(identificador or "")
        if not url:
            return None
        try:
            r = requests.get(url, headers=_UA, timeout=self.timeout)
            if r.status_code != 200:
                return None
        except Exception:
            logger.exception("No se pudo abrir la ficha %s", url)
            return None
        # las páginas de "no existe" responden 200 pero sin propiedades
        if 'class="product-property"' not in r.text:
            return None
        return self._parsear_ficha(r.text, url)

    # ---------- candidatas de slug ----------

    @classmethod
    def _slugs(cls, nombre: str) -> List[str]:
        """'RANCIOFACTS 1. EFECTIVIWONDER 6.ª ED.' ->
        ranciofacts-1-efectiviwonder, ranciofacts-efectiviwonder, ranciofacts."""
        base = re.sub(
            r"\s+(?:\d+[.\sªºao]*)?ed(?:ici[oó]n)?\.?\s*$", "",
            nombre or "", flags=re.I).strip()
        slug = cls._slug(base)
        if not slug:
            return []
        candidatas = [slug]
        sin_numeros = "-".join(t for t in slug.split("-") if not t.isdigit())
        if sin_numeros and sin_numeros != slug:
            candidatas.append(sin_numeros)
        partes = (sin_numeros or slug).split("-")
        while len(partes) > 1 and len(candidatas) < _MAX_CANDIDATAS:
            partes = partes[:-1]
            corta = "-".join(partes)
            if corta not in candidatas:
                candidatas.append(corta)
        return candidatas[:_MAX_CANDIDATAS]

    @staticmethod
    def _slug(texto: str) -> str:
        """Minúsculas, sin acentos y con guiones: el formato de sus URLs."""
        t = unicodedata.normalize("NFKD", texto or "")
        t = "".join(c for c in t if not unicodedata.combining(c))
        return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")

    # ---------- parseo ----------

    def _parsear_ficha(self, html: str, url: str) -> Dict[str, Any]:
        ficha: Dict[str, Any] = {"url_ficha": url}

        m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S)
        if m:
            ficha["titulo"] = _html.unescape(
                re.sub(r"<[^>]+>", " ", m.group(1))).strip()

        # h2.product-author: uno o varios enlaces /authors/<slug>
        m = re.search(r'<h2[^>]*class="product-author[^"]*"[^>]*>(.*?)</h2>',
                      html, re.S)
        if m:
            autores = re.findall(r'<a[^>]*href="/authors/[^"]*"[^>]*>'
                                 r"([^<]+)</a>", m.group(1))
            ficha["autor"] = " / ".join(
                _html.unescape(a).strip() for a in autores if a.strip())

        # propiedades: <span class="property-label">X:</span>
        #              <span class="property-value">Y</span>
        props: Dict[str, str] = {}
        for m in re.finditer(
                r'class="property-label">(.*?)</span>\s*'
                r'<span class="property-value">(.*?)</span>', html, re.S):
            k = re.sub(r"<[^>]+>|\s+", " ", m.group(1)).strip().rstrip(":")
            v = _html.unescape(
                re.sub(r"<[^>]+>|\s+", " ", m.group(2))).strip()
            props[k] = v
        ficha["isbn"] = props.get("ISBN", "")
        ficha["ean"] = props.get("EAN", "")
        ficha["anio"] = props.get("Año de publicación", "")
        ficha["coleccion"] = props.get("Serie", "")

        # sinopsis oficial: og:description lleva el HTML escapado dos veces
        m = re.search(r'<meta property="og:description" content="(.*?)"\s*/?>',
                      html, re.S)
        if m:
            desc = _html.unescape(m.group(1))
            desc = re.sub(r"<[^>]+>", " ", desc)
            ficha["sinopsis"] = _html.unescape(
                re.sub(r"\s+", " ", desc)).strip()

        # imágenes del producto (data-product-summary -> images[].url_product)
        # 'representations' son miniaturas: se reescriben a 'blobs' (original)
        imagenes: List[str] = []
        m = re.search(r'data-product-summary="(.*?)"', html, re.S)
        if m:
            try:
                datos = json.loads(_html.unescape(m.group(1)))
                for img in datos.get("images") or []:
                    u = img.get("url_product") or ""
                    if not u or "_mini" in u.rsplit("/", 1)[-1]:
                        continue
                    u = self._blob_url(urljoin(self.url_base, u))
                    if u not in imagenes:
                        imagenes.append(u)
            except Exception:
                logger.warning("data-product-summary de astiberri no se pudo parsear")
        if not imagenes:
            m = re.search(r'<meta property="og:image" content="([^"]+)"', html)
            if m:
                imagenes.append(_html.unescape(m.group(1)))
        ficha["imagen_url"] = imagenes[0] if imagenes else ""
        ficha["imagenes"] = imagenes

        # enlaces: la ficha y el 'Descargar avance' si existe
        links = [{"url": url, "etiqueta": "Ficha"}]
        m = re.search(
            r'product-document-preview_document[^>]*>\s*'
            r'<a[^>]*href="([^"]+)"', html)
        if m:
            links.append({"url": _html.unescape(m.group(1)),
                          "etiqueta": "Avance"})
        ficha["links"] = links

        # el resto del modelo común
        ficha.setdefault("titulo_original", "")
        ficha.setdefault("demografia", "")
        ficha["generos"] = []
        ficha["candidatos_meta"] = [v for v in props.values() if v]
        return ficha

    @staticmethod
    def _blob_url(u: str) -> str:
        """'.../representations/redirect/<blob>/<variante>/<archivo>' ->
        '.../blobs/redirect/<blob>/<archivo>' (la imagen a tamaño original)."""
        m = re.match(r"(.*?/active_storage/)representations/redirect/"
                     r"([^/]+)/[^/]+/([^/]+)$", u)
        if not m:
            return u
        return f"{m.group(1)}blobs/redirect/{m.group(2)}/{m.group(3)}"

    # ---------- prueba ----------

    def probar(self) -> tuple:
        """La web es pública: basta comprobar que la portada responde."""
        try:
            r = requests.get(f"{self.url_base}/", headers=_UA,
                             timeout=self.timeout)
            if r.status_code == 200:
                return (True, "Acceso correcto a astiberri.com")
            return (False, f"astiberri.com respondió {r.status_code}")
        except Exception as e:
            return (False, f"No se pudo conectar con astiberri.com: {e}")
