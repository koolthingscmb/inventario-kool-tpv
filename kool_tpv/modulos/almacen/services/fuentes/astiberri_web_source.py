"""Fuente Astiberri: web pública astiberri.com (sin login).

`buscar()` tiene dos caminos según la consulta:

- Dígitos (EAN/ISBN): el buscador `/search?key=keyword&value=` indexa el
  ISBN y, llamado con la cabecera X-Requested-With, devuelve la ficha
  exacta. OJO: `/search` figura como Disallow en su robots.txt; se usa por
  decisión del propietario (herramienta propia, consultas puntuales).
- Texto: candidatas `/products/<slug>` generadas del NOMBRE (sin
  peticiones) más las que devuelve el mismo buscador por título.

Cada ficha candidata se verifica comparando su EAN/ISBN publicado con el
escaneado (en la propia fuente para la vía EAN, en el servicio para la
vía nombre) — una candidata equivocada simplemente no coincide.

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
_MAX_BUSCADOR = 5


class AstiberriWebSource(BaseFuente):
    """Web pública de Astiberri: EAN por `/search` y nombre por slugs."""

    # Marca para el servicio: EAN directo primero y nombre (slugs +
    # verificación por ISBN de la ficha) como plan B
    busca_por_ean_y_nombre = True

    def __init__(self, url: str, timeout: int = 20):
        self.url_base = (url or "").rstrip("/")
        self.timeout = timeout

    @property
    def id(self) -> str:
        return "astiberri_web"

    # ---------- búsqueda y ficha ----------

    def buscar(self, consulta: str) -> List[Dict[str, Any]]:
        """Dos caminos según la consulta (ver docstring del módulo)."""
        consulta = (consulta or "").strip()
        if re.fullmatch(r"\d{9,13}", consulta.replace("-", "")):
            return self._buscar_por_ean(consulta)
        slugs = list(dict.fromkeys(
            self._slugs(consulta) + self._slugs_del_buscador(consulta)))
        return [{"titulo": slug, "url_ficha": f"{self.url_base}/products/{slug}"}
                for slug in slugs]

    def _buscar_por_ean(self, ean: str) -> List[Dict[str, Any]]:
        """Búsqueda directa por EAN/ISBN: el buscador lo indexa y devuelve
        la ficha exacta. Cada candidata se verifica descargando su ficha,
        que viaja adjunta para que `detalle` no la pida dos veces."""
        ean_digits = ean.replace("-", "")
        resultados = []
        for slug in self._slugs_del_buscador(ean_digits):
            url = f"{self.url_base}/products/{slug}"
            ficha = self.detalle({"url_ficha": url})
            if not ficha:
                continue
            if (ficha.get("ean") or ficha.get("isbn") or ""
                    ).replace("-", "") != ean_digits:
                continue
            resultados.append({
                "titulo": ficha.get("titulo") or slug,
                "url_ficha": url,
                "ean": ficha.get("ean") or ficha.get("isbn") or "",
                "isbn": ficha.get("isbn") or "",
                "_detalle": ficha,
            })
        return resultados

    def _slugs_del_buscador(self, texto: str) -> List[str]:
        """Slugs /products/... que devuelve el buscador público
        (`key=keyword&value=`). La respuesta HTML llega filtrada por
        relevancia; se deduplican conservando el orden."""
        try:
            r = requests.get(
                f"{self.url_base}/search",
                params={"key": "keyword", "value": texto},
                headers={**_UA, "X-Requested-With": "XMLHttpRequest"},
                timeout=self.timeout)
            if r.status_code != 200:
                return []
        except Exception:
            logger.exception("El buscador de astiberri no respondió")
            return []
        return list(dict.fromkeys(
            re.findall(r'href="/products/([^"?#]+)', r.text)))[:_MAX_BUSCADOR]

    def detalle(self, identificador: Any) -> Optional[Dict[str, Any]]:
        """Descarga y parsea la ficha; None si no es una ficha de producto."""
        if isinstance(identificador, dict) and identificador.get("_detalle"):
            return identificador["_detalle"]
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
