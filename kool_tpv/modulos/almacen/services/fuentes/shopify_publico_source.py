"""Fuente Shopify pública: tiendas de editoriales montadas en Shopify.

Sin login. Dos endpoints JSON que toda tienda Shopify expone:
- `GET /search/suggest.json?q=<q>&resources[type]=product` -> sugerencias
  (acepta EAN/ISBN y texto; devuelve título y handle del producto).
- `GET /products/<handle>.json` -> ficha completa: título, descripción
  (sinopsis), imágenes, tags (autor/géneros), SKU/barcode (EAN/ISBN).

Ejemplo verificado: milkywayediciones.com. Solo lectura.
"""
import html as _html
import logging
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, unquote

import requests

from .base_fuente import BaseFuente

logger = logging.getLogger(__name__)

_UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}


class ShopifyPublicoSource(BaseFuente):
    """Tienda Shopify pública de una editorial (sin credenciales)."""

    def __init__(self, url: str, timeout: int = 20):
        self.url_base = url.rstrip("/")
        self.timeout = timeout

    @property
    def id(self) -> str:
        return "shopify"

    # ---------- búsqueda y ficha ----------

    def buscar(self, consulta: str) -> List[Dict[str, Any]]:
        """Busca por EAN/ISBN/título vía suggest.json; devuelve resultados."""
        consulta = (consulta or "").strip()
        if not consulta:
            return []
        try:
            r = requests.get(
                f"{self.url_base}/search/suggest.json",
                params={"q": consulta, "resources[type]": "product",
                        "resources[limit]": "10"},
                headers=_UA, timeout=self.timeout)
            if r.status_code != 200:
                return []
            productos = (r.json().get("resources", {})
                         .get("results", {}).get("products", []))
            return [self._normalizar_sugerencia(p) for p in productos]
        except Exception:
            logger.exception("Error buscando en %s", self.url_base)
            return []

    def detalle(self, identificador: Any) -> Optional[Dict[str, Any]]:
        """Ficha completa del producto (handle o dict de buscar())."""
        handle = identificador.get("_handle") if isinstance(identificador, dict) \
            else str(identificador)
        if not handle:
            return None
        try:
            r = requests.get(f"{self.url_base}/products/{handle}.json",
                             headers=_UA, timeout=self.timeout)
            if r.status_code != 200:
                return None
            ficha = self._normalizar_producto(r.json().get("product", {}), handle)
        except Exception:
            logger.exception("Error en ficha %s de %s", handle, self.url_base)
            return None
        avance = self._enlace_avance(handle)
        if avance:
            ficha["links"] = [{"url": ficha["url_ficha"], "etiqueta": "Ficha"},
                              {"url": avance, "etiqueta": "Avance"}]
        return ficha

    def _enlace_avance(self, handle: str) -> str:
        """El JSON no trae el avance: se lee la página del producto y se coge
        el enlace cuyo texto es 'Leer avance'. Sin él, cadena vacía."""
        try:
            r = requests.get(f"{self.url_base}/products/{handle}",
                             headers=_UA, timeout=self.timeout)
            if r.status_code != 200:
                return ""
            m = re.search(r'<a[^>]*href="([^"]+)"[^>]*>\s*leer\s+avance\s*</a>',
                          r.text, re.I)
            return _html.unescape(m.group(1)) if m else ""
        except Exception:
            logger.warning("No se pudo leer el avance de %s", handle)
            return ""

    # ---------- normalización ----------

    def _normalizar_sugerencia(self, p: Dict[str, Any]) -> Dict[str, Any]:
        url = p.get("url", "")
        handle = url.split("/products/")[-1].split("?")[0] if "/products/" in url else ""
        return {
            "titulo": p.get("title") or "",
            "titulo_original": "",
            "autor": "",
            "anio": "",
            "editorial": p.get("vendor") or "",
            "isbn": "",
            "ean": "",
            "coleccion": "",
            "generos": [],
            "sinopsis": "",
            "imagen_url": (p.get("image") or {}).get("src", "")
                if isinstance(p.get("image"), dict) else (p.get("image") or ""),
            "url_ficha": urljoin(self.url_base, url),
            "_handle": handle,
        }

    def _normalizar_producto(self, p: Dict[str, Any], handle: str) -> Dict[str, Any]:
        """Del product.json al modelo común. La descripción es la sinopsis;
        el SKU suele ser el EAN y barcode el ISBN con guiones."""
        titulo = p.get("title") or ""
        sinopsis = _html.unescape(re.sub(r"<[^>]+>", " ", p.get("body_html") or ""))
        sinopsis = re.sub(r"\s+", " ", sinopsis).strip()
        variante = (p.get("variants") or [{}])[0]
        sku = variante.get("sku") or ""
        barcode = variante.get("barcode") or ""
        ean, isbn = (sku, barcode) if re.fullmatch(r"\d{12,13}", sku) else ("", barcode or sku)
        imagenes = [i.get("src", "") for i in p.get("images", [])]
        # tags llega como string separado por comas en el product.json público
        raw_tags = p.get("tags") or []
        tags = [t.strip() for t in raw_tags.split(",") if t.strip()] \
            if isinstance(raw_tags, str) else [str(t) for t in raw_tags]
        # el product.json NO trae metacampos: la página HTML los lleva como
        # enlaces a colecciones 'filter.p.m.custom.<metacampo>=<valor>'
        # (Género, Autor...). Se extraen como candidatos para el comparador.
        candidatos = list(tags)
        try:
            url_html = f"{self.url_base}/products/{handle}"
            rf = requests.get(url_html, headers=_UA, timeout=self.timeout)
            if rf.status_code == 200:
                for m in re.finditer(
                        r'filter\.p\.m\.custom\.\w+=([^"&\s<]+)', rf.text):
                    v = _html.unescape(unquote(m.group(1))).strip()
                    if v and v not in candidatos:
                        candidatos.append(v)
        except Exception:
            logger.warning("No se pudo leer la página HTML de %s", handle)
        anio = ""
        m = re.search(r"(\d{4})", p.get("published_at") or "")
        if m:
            anio = m.group(1)
        return {
            "titulo": titulo,
            "titulo_original": "",
            "autor": self._autor_de_tags(tags, titulo),
            "demografia": self._demografia_de_tags(tags),
            "candidatos_meta": candidatos,
            "anio": anio,
            "editorial": p.get("vendor") or "",
            "isbn": isbn,
            "ean": ean,
            "coleccion": p.get("product_type") or "",
            "generos": [],
            "sinopsis": sinopsis,
            "imagen_url": imagenes[0] if imagenes else "",
            "imagenes": imagenes,
            "url_ficha": f"{self.url_base}/products/{handle}",
            "_handle": handle,
        }

    def _autor_de_tags(self, tags: List[str], titulo: str = "") -> str:
        """En las tiendas de editorial el autor suele venir como tag propio.
        Heurística: tag que no es una categoría conocida ni parte del título."""
        genericos = {"manga", "comic", "novela", "shojo", "shonen", "seinen",
                     "josei", "bl", "yaoi", "tomos únicos", "tomos unicos",
                     "novedad", "preventa", "oferta", "artbook", "libro"}
        titulo_norm = titulo.lower().strip()
        for tag in tags:
            t = tag.lower().strip()
            if t not in genericos and t not in titulo_norm:
                return tag.strip()
        return ""

    def _demografia_de_tags(self, tags: List[str]) -> str:
        """Extrae la demografía de las etiquetas de Shopify."""
        demogs = {"shonen", "seinen", "shojo", "josei", "bl", "yaoi"}
        for tag in tags:
            t = tag.lower().strip()
            if t in demogs:
                return t.upper()
        return ""

    def probar(self) -> tuple:
        try:
            r = requests.get(f"{self.url_base}/search/suggest.json",
                             params={"q": "a", "resources[type]": "product",
                                     "resources[limit]": "1"},
                             headers=_UA, timeout=self.timeout)
            if r.status_code == 200:
                return (True, f"Tienda Shopify accesible: {self.url_base}")
            return (False, f"{self.url_base} respondió {r.status_code}")
        except Exception as e:
            return (False, f"Error en {self.url_base}: {e}")
