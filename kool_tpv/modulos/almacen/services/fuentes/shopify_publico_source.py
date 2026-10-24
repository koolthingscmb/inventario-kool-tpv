"""Fuente Shopify pública: tiendas de editoriales montadas en Shopify.

Sin login. La búsqueda `GET /search/suggest.json?q=<q>&resources[type]=product`
ya devuelve la ficha casi completa: título, sinopsis (`body`), tags (serie,
autor, demografía), portada y vendor. Con esa sola petición basta.

Las páginas `/products/<handle>` y `product.json` de estas tiendas llevan la
protección de Shopify contra peticiones automáticas (HTTP 429), que salta en
seguida. Por eso `detalle()` NO depende de ellas: monta la ficha con lo que ya
trajo la búsqueda y solo intenta la página una vez, de forma opcional, para
completar el enlace «Leer avance», el ISBN con guiones y los metacampos. Si
falla o limita, la ficha se devuelve igual de completa.

Ejemplo verificado: milkywayediciones.com. Solo lectura.
"""
import html as _html
import json
import logging
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, unquote, urlparse

import requests

from .base_fuente import BaseFuente

logger = logging.getLogger(__name__)

_UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}


class ShopifyPublicoSource(BaseFuente):
    """Tienda Shopify pública de una editorial (sin credenciales)."""

    # Tags que no son autor ni serie: categorías genéricas de estas tiendas
    _TAGS_GENERICOS = {"manga", "comic", "novela", "shojo", "shonen", "seinen",
                       "josei", "bl", "yaoi", "tomos únicos", "tomos unicos",
                       "novedad", "preventa", "oferta", "artbook", "libro"}
    _DEMOGRAFIAS = {"shonen", "seinen", "shojo", "josei", "bl", "yaoi",
                    "kodomo", "kodomomuke"}

    def __init__(self, url: str, timeout: int = 20):
        self.url_base = url.rstrip("/")
        self.timeout = timeout

    @property
    def id(self) -> str:
        return "shopify"

    # ---------- búsqueda (única petición obligatoria) ----------

    def buscar(self, consulta: str) -> List[Dict[str, Any]]:
        """Busca por EAN/ISBN/título vía suggest.json; la respuesta ya trae
        sinopsis, tags, portada y vendor — la ficha casi hecha."""
        consulta = (consulta or "").strip()
        if not consulta:
            return []
        try:
            r = requests.get(
                f"{self.url_base}/search/suggest.json",
                params={"q": consulta, "resources[type]": "product",
                        "resources[limit]": "10"},
                headers=_UA, timeout=self.timeout)
            if r.status_code == 429:
                raise ValueError(
                    f"{urlparse(self.url_base).netloc} está limitando las "
                    "peticiones. Espera un minuto y vuelve a intentarlo.")
            if r.status_code != 200:
                return []
            productos = (r.json().get("resources", {})
                         .get("results", {}).get("products", []))
            ean = consulta if re.fullmatch(r"\d{10,13}", consulta) else ""
            return [self._normalizar_sugerencia(p, ean) for p in productos]
        except ValueError:
            raise
        except Exception:
            logger.exception("Error buscando en %s", self.url_base)
            return []

    # ---------- ficha (0 peticiones + 1 opcional) ----------

    def detalle(self, identificador: Any) -> Optional[Dict[str, Any]]:
        """Devuelve la ficha completa construida desde la sugerencia.

        Después intenta la página del producto UNA vez, solo para sumar el
        enlace de avance, el ISBN con guiones y los metacampos. Cualquier
        fallo ahí se ignora: la ficha ya está completa."""
        sugerencia = identificador if isinstance(identificador, dict) else {}
        handle = sugerencia.get("_handle") or str(identificador or "")
        ficha = dict(sugerencia)
        ficha["_handle"] = handle
        if not handle:
            return ficha
        try:
            r = requests.get(f"{self.url_base}/products/{handle}",
                             headers=_UA, timeout=self.timeout)
            if r.status_code != 200:
                if r.status_code == 429:
                    logger.info("%s limitó la página de %s; ficha sin extras",
                                self.url_base, handle)
                return ficha
            self._completar_desde_pagina(ficha, r.text, handle)
        except Exception:
            logger.warning("Extras de la página de %s no disponibles", handle)
        return ficha

    # ---------- normalización ----------

    def _normalizar_sugerencia(self, p: Dict[str, Any],
                               ean: str = "") -> Dict[str, Any]:
        """Del producto de suggest.json al modelo común. `body` es la sinopsis
        en HTML; `tags` trae serie, autor y demografía."""
        url = p.get("url", "")
        handle = url.split("/products/")[-1].split("?")[0] if "/products/" in url else ""
        tags = p.get("tags") or []
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]

        titulo = p.get("title") or ""
        imagen = ""
        if isinstance(p.get("image"), dict):
            imagen = p["image"].get("src") or ""
        elif p.get("image"):
            imagen = p["image"]
        if not imagen and isinstance(p.get("featured_image"), dict):
            imagen = p["featured_image"].get("url") or ""

        return {
            "titulo": titulo,
            "titulo_original": "",
            "autor": self._autor_de_tags(tags, titulo),
            "demografia": self._demografia_de_tags(tags),
            "candidatos_meta": list(tags),
            "anio": "",
            "editorial": p.get("vendor") or "",
            "isbn": "",
            "ean": ean,
            "coleccion": self._serie_de_tags(tags, titulo),
            "generos": [],
            "sinopsis": self._limpiar(p.get("body") or ""),
            "imagen_url": imagen,
            "imagenes": [imagen] if imagen else [],
            "url_ficha": urljoin(self.url_base, f"/products/{handle}")
                if handle else urljoin(self.url_base, url),
            "_handle": handle,
            "_ean_busqueda": ean,
        }

    def _completar_desde_pagina(self, ficha: Dict[str, Any], texto: str,
                                handle: str) -> None:
        """Extras que solo están en la página HTML (mejor esfuerzo):
        enlace 'Leer avance', ISBN con guiones, título original y metacampos
        filter.p.m.custom.* -> candidatos del comparador."""
        m = re.search(r'<a[^>]*href="([^"]+)"[^>]*>\s*leer\s+avance\s*</a>',
                      texto, re.I)
        if m:
            avance = _html.unescape(m.group(1))
            ficha["links"] = [{"url": ficha["url_ficha"], "etiqueta": "Ficha"},
                              {"url": avance, "etiqueta": "Avance"}]

        isbn = self._campo_meta(texto, "isbn")
        if isbn:
            ficha["isbn"] = isbn
            if not ficha.get("ean"):
                digitos = re.sub(r"\D", "", isbn)
                if len(digitos) in (10, 13):
                    ficha["ean"] = digitos

        if not ficha.get("titulo_original"):
            ficha["titulo_original"] = self._campo_meta(
                texto, "titulo-original") or ""

        # el bloque de autor de la página es más fiable que la heurística
        autor = self._campo_meta(texto, "author", etiqueta="h3")
        if autor:
            ficha["autor"] = autor

        candidatos = ficha.setdefault("candidatos_meta", [])
        for m in re.finditer(r"filter\.p\.m\.custom\.(\w+)=([^\"&\s<]+)", texto):
            valor = _html.unescape(unquote(m.group(2))).strip()
            if valor and valor not in candidatos:
                candidatos.append(valor)
        if not ficha.get("demografia"):
            ficha["demografia"] = self._demografia_de_tags(candidatos)

    def _campo_meta(self, texto: str, nombre: str,
                    etiqueta: str = "span") -> str:
        """Bloque `<div class="product-main__<nombre>">...<span>valor</span>`."""
        m = re.search(
            rf'class="product-main__{re.escape(nombre)}".*?'
            rf'<{etiqueta}[^>]*>(.*?)</{etiqueta}>',
            texto, re.S)
        return self._limpiar(m.group(1)) if m else ""

    # ---------- ayudas ----------

    @staticmethod
    def _limpiar(fragmento: str) -> str:
        """Quita etiquetas HTML y compacta espacios."""
        valor = re.sub(r"<[^>]+>", " ", fragmento or "")
        return re.sub(r"\s+", " ", _html.unescape(valor)).strip()

    def _autor_de_tags(self, tags: List[str], titulo: str = "") -> str:
        """Tag que no es categoría conocida ni parte del título -> autor."""
        titulo_norm = titulo.lower().strip()
        for tag in tags:
            t = tag.lower().strip()
            if t not in self._TAGS_GENERICOS and t not in titulo_norm:
                return tag.strip()
        return ""

    def _serie_de_tags(self, tags: List[str], titulo: str) -> str:
        """Tag que sí aparece en el título -> nombre de la serie."""
        titulo_norm = titulo.lower()
        for tag in tags:
            if tag.lower().strip() in titulo_norm:
                return tag.strip()
        return ""

    def _demografia_de_tags(self, tags: List[str]) -> str:
        for tag in tags:
            if tag.lower().strip() in self._DEMOGRAFIAS:
                return tag.strip().upper()
        return ""

    def probar(self) -> tuple:
        try:
            r = requests.get(f"{self.url_base}/search/suggest.json",
                             params={"q": "a", "resources[type]": "product",
                                     "resources[limit]": "1"},
                             headers=_UA, timeout=self.timeout)
            if r.status_code == 200:
                return (True, f"Tienda Shopify accesible: {self.url_base}")
            if r.status_code == 429:
                return (False, f"{self.url_base} está limitando las peticiones")
            return (False, f"{self.url_base} respondió {r.status_code}")
        except Exception as e:
            return (False, f"Error en {self.url_base}: {e}")
