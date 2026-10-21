"""Fuente Panini: web pública panini.es (sin login).

El buscador de la web NO indexa el ISBN: solo encuentra por texto. Por eso
`buscar()` recibe el NOMBRE del producto y las fichas candidatas se verifican
después en el servicio comparando su `pnn_isbn` con el EAN escaneado (hay
ediciones repetidas del mismo tomo: sin esa comprobación se cogería la mala).

La web está detrás de una cola anti-bots (Queue-it) que deja pasar a los
rastreadores de búsqueda: se usa el User-Agent de Googlebot. Si Panini
empieza a verificarlo de verdad esta fuente dejará de encontrar resultados;
no rompe nada, simplemente devuelve "no encontrado".
"""
import html as _html
import json
import logging
import re
from typing import Any, Dict, List, Optional

import requests

from .base_fuente import BaseFuente

logger = logging.getLogger(__name__)

# panini.es deja pasar la cola a los rastreadores de búsqueda
_UA = {"User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; "
                     "+http://www.google.com/bot.html)"}


class PaniniWebSource(BaseFuente):
    """Web pública de Panini España. `buscar` recibe el NOMBRE, no el EAN."""

    # Marca para el servicio: esta fuente busca por nombre y verifica por ISBN
    busca_por_nombre = True

    def __init__(self, url: str, timeout: int = 20):
        self.url_base = (url or "").rstrip("/")
        self.timeout = timeout

    @property
    def id(self) -> str:
        return "panini_web"

    # ---------- búsqueda y ficha ----------

    def buscar(self, consulta: str) -> List[Dict[str, Any]]:
        """Devuelve las fichas candidatas por nombre (sin verificar aún)."""
        consulta = (consulta or "").strip()
        if not consulta:
            return []
        try:
            r = requests.get(f"{self.url_base}/search/ajax/suggest/",
                             params={"q": consulta}, headers=_UA,
                             timeout=self.timeout)
            datos = r.json()
        except Exception:
            logger.warning("panini.es no devolvió JSON (¿cola Queue-it?)")
            return []
        salida = []
        for item in datos:
            if not isinstance(item, dict) or item.get("type") != "product":
                continue
            url_ficha = item.get("url") or ""
            if not url_ficha:
                continue
            salida.append({
                "titulo": _html.unescape(item.get("title") or "").strip(),
                "url_ficha": url_ficha,
                "imagen_url": item.get("image") or "",
            })
        return salida

    def detalle(self, identificador: Any) -> Optional[Dict[str, Any]]:
        """Descarga y parsea la ficha pública del candidato."""
        url = identificador.get("url_ficha") if isinstance(identificador, dict) \
            else str(identificador or "")
        if not url:
            return None
        try:
            r = requests.get(url, headers=_UA, timeout=self.timeout)
        except Exception:
            logger.exception("No se pudo abrir la ficha %s", url)
            return None
        if "queue-it" in r.url:
            logger.warning("panini.es mandó la ficha a la cola: %s", url)
            return None
        return self._parsear_ficha(r.text, url)

    def _parsear_ficha(self, html: str, url: str) -> Dict[str, Any]:
        ficha: Dict[str, Any] = {"url_ficha": url}

        # JSON-LD del producto: título, portada y sinopsis oficial
        m = re.search(r'<script type="application/ld\+json">(.*?)</script>',
                      html, re.S)
        if m:
            try:
                ld = json.loads(m.group(1))
                ficha["titulo"] = ld.get("name") or ""
                ficha["imagen_url"] = ld.get("image") or ""
                desc = re.sub(r"<[^>]+>", " ", ld.get("description") or "")
                ficha["sinopsis"] = _html.unescape(
                    re.sub(r"\s+", " ", desc)).strip()
            except Exception:
                logger.warning("JSON-LD de panini.es no se pudo parsear")

        # Ficha técnica: <li class="item pnn_*"><strong>label</strong><span>valor
        candidatos: List[str] = []
        for cls, _lab, val in re.findall(
                r'<li class="item (pnn_[a-z_]+)">\s*<strong class="label">'
                r'([^<]+)</strong>\s*<span class="data">\s*(.*?)\s*</span>',
                html, re.S):
            v = _html.unescape(re.sub(r"<[^>]+>|\s+", " ", val)).strip()
            candidatos.append(v)
            if cls == "pnn_authors_display":
                ficha["autor"] = v
            elif cls == "pnn_isbn":
                ficha["isbn"] = v
                ficha["ean"] = v
            elif cls == "pnn_release_date":
                ficha["anio"] = self._anio(v)
        ficha["candidatos_meta"] = candidatos
        return ficha

    @staticmethod
    def _anio(fecha: str) -> str:
        """'13 abr 2022' -> '2022'."""
        m = re.search(r"(?:19|20)\d{2}", fecha or "")
        return m.group(0) if m else ""

    def probar(self) -> tuple:
        """La web es pública: basta ver que no nos manda a la cola."""
        try:
            r = requests.get(self.url_base + "/", headers=_UA,
                             timeout=self.timeout)
            if "queue-it" in r.url or len(r.text) < 10000:
                return (False, "panini.es nos manda a la cola anti-bots")
            return (True, "Acceso correcto a panini.es")
        except Exception as e:
            return (False, f"No se pudo conectar con panini.es: {e}")
