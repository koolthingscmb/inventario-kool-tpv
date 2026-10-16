"""Fuente Ivrea: web pública editorialivrea.com/ESP (sin login).

Las fichas son de SERIE, no de tomo: sinopsis general, demografía, guión,
dibujo, nombre original japonés y una galería con la portada de cada tomo.
La web no publica el ISBN de los tomos, así que el servicio elige la
candidata por coincidencia exacta de nombre de serie (verifica_isbn = False).

Detalle técnico: el buscador es AJAX (plugin Ivory Search) y exige un nonce
que se publica en la portada; se obtiene en cada búsqueda con la sesión.
"""
import html as _html
import logging
import re
from typing import Any, Dict, List, Optional

import requests

from .base_fuente import BaseFuente

logger = logging.getLogger(__name__)

_UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 Chrome/120.0 Safari/537.36"}

# encabezados de sección que no son datos (los bullets llevan "•")
_CABECERAS = {"manga", "cómic", "comic", "información sobre la obra",
              "portadas", "¿dónde conseguir este título?",
              "también te pueden gustar", "novela", "manhwa"}


class IvreaWebSource(BaseFuente):
    """Web pública de Ivrea España. `buscar` recibe el NOMBRE, no el EAN."""

    # el servicio le pasa el nombre del producto en vez del EAN
    busca_por_nombre = True
    # no hay ISBN en la ficha: el match se hace por nombre de serie
    verifica_isbn = False

    def __init__(self, url: str, timeout: int = 20):
        self.url_base = (url or "").rstrip("/")  # ej. https://www.editorialivrea.com/ESP
        self.timeout = timeout

    @property
    def id(self) -> str:
        return "ivrea_web"

    # ---------- búsqueda y ficha ----------

    def buscar(self, consulta: str) -> List[Dict[str, Any]]:
        consulta = (consulta or "").strip()
        if not consulta:
            return []
        # la web busca series: 'ONE PUNCH MAN 01' -> 'ONE PUNCH MAN', y el
        # número se guarda para elegir luego la portada de ese tomo.
        # el marcador (nº/vol/tomo/#) va como palabra suelta o no va.
        num = re.search(r"(?:\s+(?:n[ºo°]|núm|vol|tomo|#)\.?\s*|\s+)"
                        r"(\d+)(?:[/\-]\d+)?\s*$", consulta, re.I)
        numero_tomo = int(num.group(1)) if num else None
        consulta = consulta[:num.start()].strip() if num else consulta
        if not consulta:
            return []
        try:
            s = requests.Session()
            s.headers.update(_UA)
            r = s.get(self.url_base + "/", timeout=self.timeout)
            m = re.search(r'ajax_nonce["\']?\s*:\s*"([^"]+)"', r.text)
            if not m:
                logger.warning("No se encontró el nonce de búsqueda en Ivrea")
                return []
            r = s.post(f"{self.url_base}/wp-admin/admin-ajax.php", data={
                "action": "is_ajax_load_posts", "security": m.group(1),
                "s": consulta, "id": "307", "page": "1"},
                timeout=self.timeout)
        except Exception:
            logger.exception("No se pudo buscar en editorialivrea.com")
            return []

        salida: List[Dict[str, Any]] = []
        vistos = set()
        for m in re.finditer(
                r'<a[^>]+href="([^"]*/titulo/[^"]+)"[^>]*>(.*?)</a>',
                r.text, re.S):
            url, inner = m.groups()
            titulo = _html.unescape(
                re.sub(r"<[^>]+>|\s+", " ", inner)).strip()
            if url in vistos:
                # la serie sale 2 veces (imagen sin texto + enlace con título)
                if titulo and salida and salida[-1]["url_ficha"] == url:
                    salida[-1]["titulo"] = titulo
                continue
            vistos.add(url)
            slug = url.rstrip("/").rsplit("/", 1)[-1]
            salida.append({
                "titulo": titulo or slug.replace("-", " "),
                "url_ficha": url,
                "slug": slug,
                "numero_tomo": numero_tomo,
            })
        return salida

    def detalle(self, identificador: Any) -> Optional[Dict[str, Any]]:
        url = identificador.get("url_ficha") if isinstance(identificador, dict) \
            else str(identificador or "")
        numero_tomo = identificador.get("numero_tomo") \
            if isinstance(identificador, dict) else None
        if not url:
            return None
        try:
            r = requests.get(url, headers=_UA, timeout=self.timeout)
        except Exception:
            logger.exception("No se pudo abrir la ficha %s", url)
            return None
        return self._parsear_ficha(r.text, url, numero_tomo)

    # ---------- parseo ----------

    def _parsear_ficha(self, html: str, url: str,
                       numero_tomo: Optional[int]) -> Dict[str, Any]:
        ficha: Dict[str, Any] = {"url_ficha": url}
        guion, dibujo = "", ""
        sinopsis, tras_cabecera = "", False

        # título de la serie desde <title> ('X – Editorial Ivrea España')
        m = re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I)
        if m:
            titulo = _html.unescape(m.group(1)).split("–")[0].strip()
            if titulo:
                ficha["titulo"] = titulo

        # bloques de texto de la ficha: bullets '• CAMPO: valor' y la sinopsis
        for b in re.findall(
                r'wpb_text_column[^>]*>\s*<div class="wpb_wrapper">(.*?)'
                r'</div>\s*</div>', html, re.S):
            txt = _html.unescape(re.sub(r"<[^>]+>", " ", b))
            txt = re.sub(r"\s+", " ", txt).strip()
            if not txt:
                continue
            m = re.match(r"•\s*([^:]+):\s*(.+)", txt)
            if m:
                campo, valor = m.group(1).strip().upper(), m.group(2).strip()
                if campo.startswith("NOMBRE ORIGINAL"):
                    ficha["titulo_original"] = valor
                elif campo.startswith("GUIÓN") or campo.startswith("GUION"):
                    guion = valor
                elif campo.startswith("DIBUJO"):
                    dibujo = valor
                elif campo.startswith("DEMOGRAF"):
                    ficha["demografia"] = valor
                elif campo.startswith("FAMILIA"):
                    ficha["coleccion"] = valor
                elif campo.startswith("ESTADO EN ESPA"):
                    ficha["estado"] = valor
                continue
            # la sinopsis va tras el encabezado 'INFORMACIÓN SOBRE LA OBRA'
            if txt.lower() == "información sobre la obra":
                tras_cabecera = True
                continue
            if txt.lower() in _CABECERAS:
                continue
            if tras_cabecera and len(txt) > len(sinopsis):
                sinopsis = txt
            elif not sinopsis and len(txt) > 60:
                sinopsis = txt

        if sinopsis:
            ficha["sinopsis"] = sinopsis
        autores = [a for a in (guion, dibujo) if a]
        if autores:
            ficha["autor"] = " / ".join(autores)

        # galería 'PORTADAS': photo-gallery/<serie>/<nombre><NN>.jpg
        portadas = list(dict.fromkeys(re.findall(
            r'(https://www\.editorialivrea\.com/[^"\s]+?\.jpe?g)', html)))
        ficha["imagen_url"] = self._portada_tomo(portadas, numero_tomo)
        return ficha

    @staticmethod
    def _portada_tomo(portadas: List[str],
                      numero_tomo: Optional[int]) -> str:
        """Elige la portada del tomo N por el número del nombre del archivo.
        Prefiere la galería y la imagen grande (sin sufijo -WxH)."""
        galeria = [u for u in portadas if "/photo-gallery/" in u]
        grandes = [u for u in portadas
                   if not re.search(r"-\d+x\d+\.jpe?g", u)]
        if numero_tomo is not None:
            for grupo in (galeria, grandes, portadas):
                for u in grupo:
                    m = re.search(r"(\d+)(?:-\d+x\d+)?\.jpe?g", u)
                    if m and int(m.group(1)) == numero_tomo:
                        return u
        for u in galeria + grandes + portadas:
            return u
        return ""

    def probar(self) -> tuple:
        """La web es pública: basta comprobar que responde y es Ivrea."""
        try:
            r = requests.get(self.url_base + "/", headers=_UA,
                             timeout=self.timeout)
            if r.status_code != 200 or "ivrea" not in r.text.lower():
                return (False, "editorialivrea.com no respondió bien")
            return (True, "Acceso correcto a editorialivrea.com")
        except Exception as e:
            return (False, f"No se pudo conectar con editorialivrea.com: {e}")
