"""Fuente Azeta Distribuciones: portal de cliente de azetadistribuciones.es.

Azeta distribuye Distrito Manga (Penguin) y otras editoriales. Hace falta
login con las credenciales de cliente (usuario y contraseña de la fuente):
`POST /html/identificacion/autentifica.php` con `fr_nombre` y `fr_clave`.

Búsqueda por EAN: `GET /html/lib/buscar/listaLibros.php?patron=<ean>`. Con un
EAN único la web redirige directamente a la ficha `detalle.php`; si no hay
coincidencia exacta se devuelve "no encontrado" (nunca otra ficha).

La ficha aporta: título (`h2` de `.bookinfo`), autor (`buscarAutor('...')`),
filas `filaDetalle` (editorial, EAN, colección, idioma, fecha de edición),
sinopsis (`#textoSinopsisLibro`) y las imágenes del propio libro en su CDN
(`/imagenes/<ean7>/<ean12>.JPG` más `_NN`). La página también enseña libros
sugeridos: solo se cogen las imágenes que llevan el prefijo del EAN buscado.
No se usan precios, descuentos ni stock.

Las etiquetas salen en el idioma de la cuenta (catalán o castellano): se
reconocen por su inicio. Solo lectura.
"""
import html as _html
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


def _limpio(texto: str) -> str:
    """Quita etiquetas HTML, entidades y espacios repetidos."""
    return re.sub(r"\s+", " ", _html.unescape(
        re.sub(r"<[^>]+>", " ", texto or ""))).strip()


def _norm(texto: str) -> str:
    """Minúsculas sin acentos ni signos: para reconocer etiquetas."""
    t = unicodedata.normalize("NFKD", texto or "")
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "", t.lower())


class AzetaWebSource(BaseFuente):
    """Portal de cliente de Azeta. Busca por EAN/ISBN (flujo estándar)."""

    def __init__(self, url: str, credenciales: Dict[str, str],
                 timeout: int = 20):
        self.url_base = (url or "").rstrip("/")
        self.creds = credenciales or {}
        self.timeout = timeout
        self._sesion: Optional[requests.Session] = None

    @property
    def id(self) -> str:
        return "azeta_web"

    # ---------- login ----------

    def _entrar(self) -> bool:
        """Crea la sesión y hace login. True si entra en el área de cliente."""
        s = requests.Session()
        s.headers.update(_UA)
        try:
            s.get(f"{self.url_base}/", timeout=self.timeout)
            r = s.post(f"{self.url_base}/html/identificacion/autentifica.php",
                       data={"fr_nombre": self.creds.get("usuario", ""),
                             "fr_clave": self.creds.get("password", ""),
                             "g-recaptcha-response": ""},
                       timeout=self.timeout)
            if "/html/lib/" not in r.url:
                logger.warning("Login fallido en %s", self.url_base)
                return False
            self._sesion = s
            return True
        except Exception:
            logger.exception("Error de conexión con %s", self.url_base)
            return False

    def _get_buscador(self, ean: str) -> Optional[requests.Response]:
        """Pide la búsqueda; si la sesión caducó, entra de nuevo una vez."""
        for _ in range(2):
            if self._sesion is None and not self._entrar():
                return None
            r = self._sesion.get(
                f"{self.url_base}/html/lib/buscar/listaLibros.php",
                params={"patron": ean, "boton": "Cercar"},
                timeout=self.timeout)
            if "/html/lib/" in r.url:
                return r
            self._sesion = None
        return None

    # ---------- búsqueda y ficha ----------

    def buscar(self, consulta: str) -> List[Dict[str, Any]]:
        """EAN/ISBN -> [ficha] si la web lleva directo a una ficha cuyo EAN
        coincide; [] en cualquier otro caso."""
        ean = re.sub(r"[^0-9]", "", consulta or "")
        if not ean:
            return []
        try:
            r = self._get_buscador(ean)
        except Exception:
            logger.exception("No se pudo buscar en %s", self.url_base)
            return []
        if r is None or r.status_code != 200 or "detalle.php" not in r.url:
            return []
        ficha = self._parsear_ficha(r.text, r.url, ean)
        if not ficha or re.sub(r"[^0-9]", "", ficha.get("ean", "")) != ean:
            return []
        ficha["_ficha"] = True  # detalle() la devuelve tal cual
        return [ficha]

    def detalle(self, identificador: Any) -> Optional[Dict[str, Any]]:
        """La ficha ya llega parseada desde `buscar()`."""
        if isinstance(identificador, dict) and identificador.get("_ficha"):
            return identificador
        return None

    # ---------- parseo ----------

    def _parsear_ficha(self, html: str, url_respuesta: str,
                       ean: str) -> Dict[str, Any]:
        ficha: Dict[str, Any] = {}
        ficha["url_ficha"] = re.sub(r"[&?]ajax=?$", "", url_respuesta)

        m = re.search(r'<div class="bookinfo">(.*?)<div class="detalleArticulo"',
                      html, re.S)
        info = m.group(1) if m else ""
        m = re.search(r"<h2[^>]*>(.*?)</h2>", info, re.S)
        if m:
            ficha["titulo"] = _limpio(m.group(1))
        autores = []
        for a in re.findall(r"buscarAutor\('([^']*)'\)", info):
            a = _html.unescape(a).strip()
            if a and a not in autores:
                autores.append(a)
        ficha["autor"] = " / ".join(autores)

        # filas rotuladas: etiqueta (en catalán o castellano) -> valor
        campos: Dict[str, str] = {}
        for m in re.finditer(
                r'<div class="cabeceraDetalle">([^<]*)</div>\s*<div>(.*?)</div>',
                html, re.S):
            campos[_norm(m.group(1))] = _limpio(m.group(2))[:200]

        def campo(*inicios: str) -> str:
            for k, v in campos.items():
                if any(k.startswith(i) for i in inicios):
                    return v
            return ""

        ficha["editorial"] = campo("editorial")
        ficha["ean"] = campo("ean")
        ficha["isbn"] = ""
        ficha["coleccion"] = campo("colleccio", "coleccion")
        m = re.search(r"(\d{4})", campo("data", "fecha"))
        if m:
            ficha["anio"] = m.group(1)

        m = re.search(r'id="textoSinopsisLibro"[^>]*>(.*?)</div>', html, re.S)
        if m:
            ficha["sinopsis"] = _limpio(m.group(1))

        # imágenes del propio libro: /imagenes/<ean7>/<ean12>[_NN].ext
        ean7, ean12 = ean[:7], ean[:12]
        patron = (r'(?:src|href)="([^"]*/imagenes/+' + re.escape(ean7) + "/"
                  + re.escape(ean12) + r'(?:_\d+)?\.(?:jpe?g|png|webp|gif))'
                  r'(?:\?[^"]*)?"')
        imagenes: List[str] = []
        for m in re.finditer(patron, html, re.I):
            u = urljoin(url_respuesta, m.group(1))
            if u not in imagenes:
                imagenes.append(u)
        principal = next((u for u in imagenes
                          if not re.search(r"_\d+\.", u)), "")
        extras = sorted(u for u in imagenes if u != principal)
        ficha["imagen_url"] = principal or (extras[0] if extras else "")
        ficha["imagenes"] = ([principal] if principal else []) + extras

        # el resto del modelo común
        ficha.setdefault("titulo_original", "")
        ficha.setdefault("demografia", "")
        ficha["generos"] = []
        ficha["candidatos_meta"] = [v for v in campos.values() if v]
        return ficha

    # ---------- prueba ----------

    def probar(self) -> tuple:
        """Login con las credenciales guardadas."""
        if not (self.creds.get("usuario") and self.creds.get("password")):
            return (False, "Faltan usuario y contraseña de Azeta")
        self._sesion = None
        if self._entrar():
            return (True, "Login correcto en Azeta")
        return (False, f"No se pudo iniciar sesión en {self.url_base}")
