"""Fuente Devir: portal B2B b2bdevir.es (Magento, requiere login de cliente).

Flujo: form_key de /customer/account/login -> POST a loginPost con
login[username]/login[password]. Búsqueda por EAN o nombre en
/catalogsearch/result/?q=. La ficha aporta título, autor/editorial,
descripción (sinopsis), atributos técnicos (jugadores, edad, duración...) e
imágenes. No se importan precios ni stock.

Solo lectura. Las credenciales llegan por parámetro (tabla editoriales_fuentes).
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
                    "AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36",
       "Accept-Language": "es-ES,es;q=0.9"}

# fragmentos del nombre del atributo (normalizado) -> campo normalizado.
# Devir usa nombres largos: 'Edad mínima recomendada', 'Duración de la
# partida', 'Mínimo de jugadores'...
_ATRIBUTOS = {
    "autor": "autor",
    "ilustracion": "ilustrador",
    "ilustrador": "ilustrador",
    "editor": "editor",
    "edad": "edad",
    "duracion": "duracion",
    "tiempo de juego": "duracion",
    "mecanicas": "mecanicas",
}

# atributos aparte que se combinan en 'jugadores' como "min-max"
_JUGADORES_MIN = "minimodejugadores"
_JUGADORES_MAX = "maximodejugadores"

_MAX_CANDIDATAS = 8


def _norm(texto: str) -> str:
    t = unicodedata.normalize("NFKD", texto or "")
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "", t.lower())


def _texto(html: str) -> str:
    return re.sub(r"\s+", " ", _html.unescape(
        re.sub(r"<[^>]+>", " ", html or ""))).strip()


class DevirWebSource(BaseFuente):
    """Portal B2B de Devir (Magento): login + búsqueda + ficha."""

    # la ficha técnica de Devir no publica el EAN de forma fiable: el match
    # principal es por nombre cuando basta (el servicio marca verifica_isbn)
    busca_por_ean_y_nombre = True

    def __init__(self, url: str, credenciales: Dict[str, str],
                 timeout: int = 20):
        self.url_base = url.rstrip("/")
        self.creds = credenciales or {}
        self.timeout = timeout
        self._sesion: Optional[requests.Session] = None

    @property
    def id(self) -> str:
        return "devir_web"

    # ----------------- sesión -----------------

    def _login(self) -> bool:
        """Loguea con usuario/contraseña del B2B. True si quedó dentro."""
        if self._sesion is not None:
            return True
        usuario = (self.creds.get("usuario") or "").strip()
        password = (self.creds.get("password") or "").strip()
        if not usuario or not password:
            logger.error("Devir: faltan credenciales en la fuente")
            return False
        sesion = requests.Session()
        sesion.headers.update(_UA)
        try:
            pagina_login = sesion.get(
                f"{self.url_base}/customer/account/login/",
                timeout=self.timeout)
            m = re.search(r'name="form_key"\s+type="hidden"\s+value="([^"]+)"',
                          pagina_login.text)
            if not m:
                logger.error("Devir: no aparece el form_key de login")
                return False
            r = sesion.post(
                f"{self.url_base}/customer/account/loginPost/",
                data={
                    "login[username]": usuario,
                    "login[password]": password,
                    "form_key": m.group(1),
                },
                timeout=self.timeout, allow_redirects=True)
        except Exception:
            logger.exception("Devir: error de conexión en el login")
            return False
        dentro = "customer/account" in (r.url or "") or \
            "Cerrar sesión" in r.text or "Mi cuenta" in r.text
        if not dentro:
            logger.error("Devir: login rechazado (usuario/contraseña)")
            return False
        self._sesion = sesion
        return True

    def probar(self) -> tuple:
        if self._login():
            return (True, "Login correcto en el B2B de Devir")
        return (False, "No se pudo entrar en el B2B (revisa usuario/contraseña)")

    def _get(self, url: str, params: Optional[Dict[str, str]] = None
             ) -> Optional[str]:
        if not self._login() or self._sesion is None:
            return None
        try:
            r = self._sesion.get(url, params=params, timeout=self.timeout)
            if r.status_code != 200:
                logger.warning("Devir: HTTP %s en %s", r.status_code, url)
                return None
            if "customer/account/login" in (r.url or ""):
                # sesión caducada a mitad: reintenta una vez
                self._sesion = None
                if not self._login():
                    return None
                r = self._sesion.get(url, params=params,
                                     timeout=self.timeout)
                if r.status_code != 200:
                    return None
            return r.text
        except Exception:
            logger.exception("Devir: error leyendo %s", url)
            return None

    # ----------------- búsqueda -----------------

    def buscar(self, consulta: str) -> List[Dict[str, Any]]:
        """Busca por EAN o nombre en /catalogsearch/result/."""
        consulta = (consulta or "").strip()
        if not consulta:
            return []
        html = self._get(f"{self.url_base}/catalogsearch/result/",
                         params={"q": consulta})
        if not html:
            return []

        # Magento/Porto: <a class="product-item-link" href="url">título</a>
        resultados = []
        for m in re.finditer(
                r'class="product-item-link"[^>]*href="(' +
                re.escape(self.url_base) + r'/[^"]+?)"[^>]*>(.*?)</a>',
                html, re.S):
            url = _html.unescape(m.group(1))
            titulo = _texto(m.group(2))
            if url not in [r["url_ficha"] for r in resultados]:
                resultados.append({"url_ficha": url, "titulo": titulo})
        if not resultados:
            for m in re.finditer(
                    r'href="(' + re.escape(self.url_base) +
                    r'/[^"]+?)"[^>]*class="[^"]*product-item-link"[^>]*>(.*?)</a>',
                    html, re.S):
                url = _html.unescape(m.group(1))
                titulo = _texto(m.group(2))
                if url not in [r["url_ficha"] for r in resultados]:
                    resultados.append({"url_ficha": url, "titulo": titulo})

        # prioriza las que contienen la consulta (EAN o nombre)
        norm = _norm(consulta)
        if norm:
            resultados.sort(key=lambda r: 0 if norm in _norm(
                r.get("titulo") or r["url_ficha"]) else 1)
        return resultados[:_MAX_CANDIDATAS]

    # ----------------- ficha -----------------

    def detalle(self, identificador: Any) -> Optional[Dict[str, Any]]:
        url = identificador.get("url_ficha") if isinstance(identificador, dict) \
            else str(identificador or "")
        if not url:
            return None
        html = self._get(url)
        if not html:
            return None
        return self._parsear_ficha(html, url)

    def _parsear_ficha(self, h: str, url: str) -> Dict[str, Any]:
        datos: Dict[str, Any] = {"url_ficha": url,
                                 "editorial": "Devir"}

        m = re.search(r'og:title[^>]*content="([^"]+)', h)
        if m:
            datos["titulo"] = _html.unescape(m.group(1)).strip()
        m = re.search(r'og:image[^>]*content="([^"]+)', h)
        if m:
            datos["imagen_url"] = m.group(1)

        # EAN/ISBN si la ficha lo muestra
        m = re.search(r'(?:EAN|ISBN)[^0-9]{0,20}(\d{13})', h, re.I)
        if m:
            datos["ean"] = m.group(1)

        # atributos técnicos de Magento: pares etiqueta/valor
        jug_min = jug_max = None
        for m in re.finditer(
                r'<th[^>]*>\s*(.*?)\s*</th>\s*<td[^>]*>\s*(.*?)\s*</td>',
                h, re.S):
            clave = _norm(_texto(m.group(1)))
            valor = _texto(m.group(2))
            if not valor:
                continue
            if clave == _JUGADORES_MIN:
                jug_min = valor
                continue
            if clave == _JUGADORES_MAX:
                jug_max = valor
                continue
            for fragmento, campo in _ATRIBUTOS.items():
                if fragmento in clave and campo not in datos:
                    datos[campo] = valor
                    break
        if jug_min or jug_max:
            datos["jugadores"] = f"{jug_min or '?'}-{jug_max or '?'}"

        # descripción corta o larga de Magento
        m = re.search(r'class="product attribute description"[^>]*>'
                      r'(.*?)</div>', h, re.S)
        if not m:
            m = re.search(r'name="description" content="([^"]+)"', h)
        if m:
            sinopsis = _texto(m.group(1))
            if sinopsis:
                datos["sinopsis"] = sinopsis

        # galería de imágenes
        galeria = sorted(set(re.findall(
            r'(media/catalog/product/[^"\'<>]+?\.(?:png|jpe?g|webp))', h)))
        if galeria:
            datos["imagenes"] = [i if i.startswith("http")
                                 else self.url_base + "/" + i
                                 for i in galeria]
        return datos
