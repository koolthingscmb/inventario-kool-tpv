"""Fuente UDL Libros: web pública udllibros.com (sin login).

UDL distribuye La Cúpula, Astiberri y muchas editoriales pequeñas.
Búsqueda por EAN/ISBN: POST `fr_patron` a `/html/busqueda/lista.php`. Si el
código es único la web devuelve la ficha directamente; si no, una lista con
enlaces `/libro-<slug>-<codigo>`.

La ficha aporta: título y autor (en el `<h1 class="title">`), campos
rotulados (`<div class="def">`), sinopsis oficial (`div.sinopsisHTML`),
portada en `/imagenes/<ean7>/<ean12>.JPG` más 'Otras imágenes del libro'
(`<ean12>_NN.jpg`) y el enlace Calameo del extracto
('Primer capítulo / Extracto'). No se usan precios ni stock.

Solo lectura.
"""
import html as _html
import logging
import re
from typing import Any, Dict, List, Optional
from urllib.parse import unquote, urljoin

import requests

from .base_fuente import BaseFuente

logger = logging.getLogger(__name__)

_UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 Chrome/120.0 Safari/537.36"}


class UdlWebSource(BaseFuente):
    """Web pública de UDL Libros. Busca por EAN/ISBN (flujo estándar)."""

    def __init__(self, url: str, timeout: int = 20):
        self.url_base = (url or "").rstrip("/")  # ej. https://www.udllibros.com
        self.timeout = timeout

    @property
    def id(self) -> str:
        return "udl_web"

    # ---------- búsqueda y ficha ----------

    def buscar(self, consulta: str) -> List[Dict[str, Any]]:
        """POST fr_patron=EAN. Ficha directa -> [ficha con _ficha=True];
        lista de resultados -> candidatos con url_ficha /libro-*."""
        consulta = (consulta or "").strip()
        if not consulta:
            return []
        try:
            r = requests.post(f"{self.url_base}/html/busqueda/lista.php",
                              data={"fr_patron": consulta},
                              headers=_UA, timeout=self.timeout)
            if r.status_code != 200:
                return []
        except Exception:
            logger.exception("No se pudo buscar en %s", self.url_base)
            return []

        if 'class="def">EAN<' in r.text:
            # match único: la respuesta YA es la ficha
            ficha = self._parsear_ficha(r.text, r.url)
            if ficha:
                ficha["_ficha"] = True  # detalle() la devuelve tal cual
                return [ficha]
            return []

        # lista de resultados: enlaces /libro-<slug>-<codigo>
        salida, vistos = [], set()
        for m in re.finditer(
                r'href="(https://www\.udllibros\.com/libro-([^"]+))"',
                r.text):
            url, resto = m.groups()
            if url in vistos:
                continue
            vistos.add(url)
            slug, _, codigo = resto.rpartition("-")
            salida.append({
                "titulo": unquote(slug).replace("_", " ").strip(),
                "url_ficha": url,
                "_codigo": codigo,
            })
        return salida

    def detalle(self, identificador: Any) -> Optional[Dict[str, Any]]:
        """Si `identificador` ya es la ficha parseada la devuelve; si es
        una url /libro-*, la descarga y parsea."""
        if isinstance(identificador, dict):
            if identificador.get("_ficha"):
                return identificador
            url = identificador.get("url_ficha") or ""
        else:
            url = str(identificador or "")
        if not url:
            return None
        try:
            r = requests.get(url, headers=_UA, timeout=self.timeout)
            if r.status_code != 200:
                return None
            return self._parsear_ficha(r.text, r.url)
        except Exception:
            logger.exception("No se pudo abrir la ficha %s", url)
            return None

    # ---------- parseo ----------

    def _parsear_ficha(self, html: str, url_respuesta: str) -> Dict[str, Any]:
        ficha: Dict[str, Any] = {}

        m = re.search(r'rel="canonical"[^>]*href="([^"]+)"', html)
        url_ficha = m.group(1) if m else url_respuesta
        ficha["url_ficha"] = url_ficha

        # h1: 'TITULO <em><a href="/autor-..">AUTOR</a></em>'
        m = re.search(r'<h1[^>]*class="title"[^>]*>(.*?)</h1>', html, re.S)
        if m:
            h1 = m.group(1)
            ma = re.search(r"<em>.*?<a[^>]*>(.*?)</a>", h1, re.S)
            if ma:
                ficha["autor"] = _html.unescape(
                    re.sub(r"<[^>]+>", "", ma.group(1))).strip()
            titulo = re.sub(r"<em>.*?</em>", "", h1, flags=re.S)
            ficha["titulo"] = _html.unescape(
                re.sub(r"<[^>]+>", " ", titulo)).strip()

        # campos rotulados <div class="def">X</div><div>Y</div>
        defs: Dict[str, str] = {}
        for m in re.finditer(
                r'<div class="def">(.*?)</div>\s*<div>(.*?)</div>',
                html, re.S):
            k = _html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip()
            v = _html.unescape(re.sub(r"<[^>]+>", " ", m.group(2))).strip()
            defs[k] = v
        ficha["editorial"] = defs.get("Editorial", "")
        ficha["coleccion"] = defs.get("Colección", "")
        ficha["ean"] = defs.get("EAN", "")
        ficha["isbn"] = defs.get("ISBN", "")
        m = re.search(r"(\d{4})", defs.get("F. lanzamiento", ""))
        if m:
            ficha["anio"] = m.group(1)

        # sinopsis oficial
        m = re.search(r'class="sinopsisHTML"[^>]*>(.*?)</div>', html, re.S)
        if m:
            ficha["sinopsis"] = re.sub(
                r"\s+", " ", _html.unescape(
                    re.sub(r"<[^>]+>", " ", m.group(1)))).strip()

        # portada principal + 'Otras imágenes del libro' (_01, _02...)
        imagenes = []
        for m in re.finditer(
                r'(?:src|href)="([^"]*/imagenes/+\d+/[^"]+?\.(?:jpe?g|png|webp))'
                r'(?:\?[^"]*)?"', html, re.I):
            u = urljoin(self.url_base, m.group(1))
            if u not in imagenes:
                imagenes.append(u)
        principal = next((u for u in imagenes
                          if not re.search(r"_\d+\.", u)), "")
        extras = sorted(u for u in imagenes if u != principal)
        ficha["imagen_url"] = principal or (extras[0] if extras else "")
        ficha["imagenes"] = ([principal] if principal else []) + extras

        # extracto Calameo ('Primer capítulo / Extracto')
        m = re.search(r'https?://[^"\'<>\s]*calameo\.com[^"\'<>\s]*',
                      html, re.I)
        links = [{"url": url_ficha, "etiqueta": "Ficha"}]
        if m:
            links.append({"url": _html.unescape(m.group(0)),
                          "etiqueta": "Avance"})
        ficha["links"] = links

        # el resto del modelo común
        ficha.setdefault("titulo_original", "")
        ficha.setdefault("demografia", "")
        ficha["generos"] = []
        ficha["candidatos_meta"] = [v for v in defs.values() if v]
        return ficha

    # ---------- prueba ----------

    def probar(self) -> tuple:
        """La web es pública: basta comprobar que la búsqueda responde."""
        try:
            r = requests.post(f"{self.url_base}/html/busqueda/lista.php",
                              data={"fr_patron": "a"},
                              headers=_UA, timeout=self.timeout)
            if r.status_code == 200:
                return (True, "Acceso correcto a udllibros.com")
            return (False, f"udllibros.com respondió {r.status_code}")
        except Exception as e:
            return (False, f"No se pudo conectar con udllibros.com: {e}")
