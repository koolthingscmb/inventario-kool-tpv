"""Fuente SD Games: web pública playsdgames.com (WordPress/WooCommerce, sin login).

Búsqueda por nombre con el buscador nativo de la web (`/?s=`): devuelve las
URLs `/producto/<slug>/` candidatas y el servicio elige la ficha. No hay EAN
público en la web, así que se busca por nombre y el usuario confirma el juego.

La ficha aporta: título, autor (`AUTOR/A`), ilustración, edad, jugadores,
duración, descripción (sinopsis), categorías (tipo de juego / tipo de jugador)
e imágenes (og:image + galería). No se importan precios ni existencias.

Solo lectura.
"""
import html as _html
import logging
import re
import unicodedata
from typing import Any, Dict, List, Optional

import requests

from .base_fuente import BaseFuente

logger = logging.getLogger(__name__)

_UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 Chrome/120.0 Safari/537.36"}

# etiquetas H2 de la ficha -> campo normalizado
_ETIQUETAS = {
    "AUTOR/A": "autor",
    "ILUSTRACIÓN": "ilustrador",
    "EDAD": "edad",
    "JUGADORES": "jugadores",
    "DURACIÓN": "duracion",
}

_MAX_CANDIDATAS = 8


def _norm(texto: str) -> str:
    """Minúsculas sin acentos ni signos: para comparar nombres y slugs."""
    t = unicodedata.normalize("NFKD", texto or "")
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "", t.lower())


def _texto(html: str) -> str:
    return re.sub(r"\s+", " ", _html.unescape(
        re.sub(r"<[^>]+>", " ", html or ""))).strip()


class SdGamesWebSource(BaseFuente):
    """Web pública de Play SD Games. `buscar` recibe el NOMBRE, no el EAN.

    La web no publica EAN/ISBN, así que no hay forma de verificar el resultado
    por código: se marca `verifica_isbn = False` y el servicio empareja por
    título (igual que ivrea_web).
    """

    busca_por_nombre = True
    verifica_isbn = False

    def __init__(self, url: str, timeout: int = 20):
        self.url_base = url.rstrip("/")
        self.timeout = timeout

    @property
    def id(self) -> str:
        return "sdgames_web"

    def probar(self) -> tuple:
        try:
            r = requests.get(self.url_base, headers=_UA, timeout=self.timeout)
            ok = r.status_code == 200
            return (ok, "Web accesible" if ok else f"HTTP {r.status_code}")
        except Exception as e:
            return (False, str(e))

    # ----------------- búsqueda -----------------

    def buscar(self, consulta: str) -> List[Dict[str, Any]]:
        """Busca por nombre con el buscador de la web. Devuelve candidatas."""
        consulta = (consulta or "").strip()
        if not consulta:
            return []
        try:
            r = requests.get(self.url_base, params={"s": consulta},
                             headers=_UA, timeout=self.timeout)
            if r.status_code != 200:
                logger.warning("SD Games: HTTP %s buscando '%s'",
                               r.status_code, consulta)
                return []
        except Exception as e:
            logger.exception("SD Games: error buscando '%s'", consulta)
            return []

        urls = []
        for m in re.finditer(r'(/producto/[a-z0-9\-]+/)', r.text):
            u = m.group(1)
            if u not in urls:
                urls.append(u)

        candidatas = []
        norm = _norm(consulta)
        for u in urls:
            slug = u.strip("/").split("/")[-1]
            if norm and norm in _norm(slug):
                candidatas.append({"url_ficha": self.url_base + u,
                                   "slug": slug,
                                   "titulo": re.sub(r"-\d+$", "", slug)
                                             .replace("-", " ")})
        # si ninguna coincide por slug, se devuelven las primeras igualmente
        if not candidatas:
            for u in urls[:_MAX_CANDIDATAS]:
                slug = u.strip("/").split("/")[-1]
                candidatas.append({"url_ficha": self.url_base + u,
                                   "slug": slug,
                                   "titulo": re.sub(r"-\d+$", "", slug)
                                             .replace("-", " ")})
        return candidatas[:_MAX_CANDIDATAS]

    # ----------------- ficha -----------------

    def detalle(self, identificador: Any) -> Optional[Dict[str, Any]]:
        url = identificador.get("url_ficha") if isinstance(identificador, dict) \
            else str(identificador or "")
        if not url:
            return None
        try:
            r = requests.get(url, headers=_UA, timeout=self.timeout)
            if r.status_code != 200:
                logger.warning("SD Games: HTTP %s en %s", r.status_code, url)
                return None
        except Exception:
            logger.exception("SD Games: error leyendo ficha %s", url)
            return None
        return self._parsear_ficha(r.text, url)

    def _parsear_ficha(self, h: str, url: str) -> Dict[str, Any]:
        datos: Dict[str, Any] = {"url_ficha": url,
                                 "editorial": "SD Games"}

        m = re.search(r'og:title[^>]*content="([^"]+)', h)
        if m:
            datos["titulo"] = re.sub(r"\s*-\s*Play SD Games.*$", "",
                                     _html.unescape(m.group(1))).strip()

        # etiqueta H2 -> valor en el H2 siguiente
        for etiqueta, campo in _ETIQUETAS.items():
            m = re.search(re.escape(etiqueta) + r'</h2>.*?'
                          r'elementor-heading-title[^>]*>(.*?)</h2>',
                          h, re.S | re.I)
            if m:
                valor = _texto(m.group(1))
                # si lo que sigue es otra etiqueta, la ficha no tiene ese dato
                if valor and valor.upper() not in {
                        e.upper() for e in _ETIQUETAS} | {"DESCRIPCIÓN"}:
                    datos[campo] = valor

        # descripción: texto tras la etiqueta hasta los productos relacionados
        m = re.search(r'descripción</h[0-9]>(.*?)(?:PRODUCTOS RELACIONADOS|'
                      r'<div class="ecs-posts)', h, re.S | re.I)
        if m:
            sinopsis = _texto(m.group(1))
            if sinopsis:
                datos["sinopsis"] = sinopsis

        # categorías propias del producto: primer bloque contiguo de enlaces
        # 'juegos-categorias' (los siguientes son de productos relacionados)
        m = re.search(
            r'((?:<a[^>]*juegos-categorias/[^>]*>\s*[^<]+</a>\s*,?\s*)+)', h)
        if m:
            generos = sorted({g.strip() for g in re.findall(
                r'>\s*([^<]+)</a>', m.group(1)) if g.strip()})
            if generos:
                datos["generos"] = generos
        if generos:
            datos["generos"] = [g.strip() for g in generos]

        imagen = re.search(r'og:image[^>]*content="([^"]+)', h)
        if imagen:
            datos["imagen_url"] = imagen.group(1)

        galeria = sorted(set(re.findall(
            r'(wp-content/uploads/[^"\'<>]+?\.(?:png|jpe?g|webp))', h)))
        if galeria:
            datos["imagenes"] = ["https://" + "playsdgames.com/" + i
                                 if i.startswith("wp-") else i for i in galeria]

        return datos
