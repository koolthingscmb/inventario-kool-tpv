"""Fuente ZonaLibros/Edisoft: Norma, SD Distribuciones y portales equivalentes.

El software es el mismo en todos los portales; cambian la URL y las credenciales.

Dos variantes detectadas automáticamente:
- "clientes" (Norma): login en `login.aspx` con postback `btnLogin_Click`
  (campos `ctl00$inpNIF`, `ctl00$inpuUser`, `ctl00$inpPassword`) que devuelve un
  301 a `zonalogin.aspx`, que es quien pone la cookie de sesión. El contenido
  cuelga de `/Clientes/`.
- "plus" (SD): login en la propia portada (`ctl00$inpuUser`, `ctl00$inpPassword`,
  submit `ctl00$btnLogin`, sin NIF) y contenido en la raíz.

Búsqueda: POST a `<base>/AjaxService.asmx/BuscadorArticulosResto` con JSON
`{prefix, idd}`; `idd` es el id del distribuidor (campo oculto `ctl00$idd`).
Detalle: `<base>/FichaArticulo.aspx?Libro=<CI>` con los datos rotulados.

Solo lectura. No se guardan credenciales: llegan por parámetro.
"""
import html as _html
import logging
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import requests

from .base_fuente import BaseFuente

logger = logging.getLogger(__name__)

_UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}


class ZonaLibrosSource(BaseFuente):
    """Portal ZonaLibros: login + búsqueda por EAN/ISBN + ficha."""

    def __init__(self, url: str, credenciales: Dict[str, str],
                 nombre: str = "zonalibros", timeout: int = 20):
        self.url_base = url.rstrip("/")
        self.creds = credenciales or {}
        self._nombre = nombre
        self.timeout = timeout
        self._sesion: Optional[requests.Session] = None
        self._ruta_base = ""          # "/Clientes" o "" (variante plus)
        self._idd: Optional[str] = None

    @property
    def id(self) -> str:
        return "zonalibros"

    # ---------- login ----------

    def _campos_ocultos(self, html: str) -> Dict[str, str]:
        datos = {}
        for m in re.finditer(r"<input[^>]*>", html):
            tag = m.group(0)
            if 'type="hidden"' in tag:
                n = re.search(r'name="([^"]+)"', tag)
                v = re.search(r'value="([^"]*)"', tag)
                if n:
                    datos[n.group(1)] = v.group(1) if v else ""
        return datos

    def _login_clientes(self, s: requests.Session) -> bool:
        """Variante Norma/MilkyWay: postback en login.aspx + zonalogin.aspx."""
        r = s.get(f"{self.url_base}/login.aspx", timeout=self.timeout)
        data = self._campos_ocultos(r.text)
        data.update({
            "__EVENTTARGET": "btnLogin_Click",
            "ctl00$inpNIF": self.creds.get("nif", ""),
            "ctl00$inpuUser": self.creds.get("usuario", ""),
            "ctl00$inpPassword": self.creds.get("password", ""),
        })
        r = s.post(f"{self.url_base}/login.aspx", data=data,
                   timeout=self.timeout, allow_redirects=False)
        loc = r.headers.get("location", "")
        if "zonalogin" not in loc:
            return False
        s.get(urljoin(self.url_base + "/", loc), timeout=self.timeout,
              allow_redirects=False)
        return "ZONALIBROS.ASPXAUTH" in s.cookies

    def _login_plus(self, s: requests.Session) -> bool:
        """Variante SD: login en la portada, sin NIF."""
        r = s.get(self.url_base + "/", timeout=self.timeout)
        data = self._campos_ocultos(r.text)
        data.update({
            "ctl00$inpuUser": self.creds.get("usuario", ""),
            "ctl00$inpPassword": self.creds.get("password", ""),
            "ctl00$btnLogin": "Entrar",
        })
        r = s.post(self.url_base + "/", data=data, timeout=self.timeout,
                   allow_redirects=False)
        if r.status_code not in (301, 302):
            return False
        r = s.get(self.url_base + "/", timeout=self.timeout)
        m = re.search(r'id="IsAuthenticated"[^>]*value="([^"]*)"', r.text)
        return bool(m and m.group(1).lower() == "true")

    def _detectar_variante(self, s: requests.Session) -> str:
        r = s.get(self.url_base + "/", timeout=self.timeout)
        t = r.text
        if "ctl00$inpNIF" in t or "login.aspx" in r.url:
            return "clientes"
        return "plus"

    def _entrar(self) -> bool:
        """Crea sesión, detecta la variante y hace login. True si dentro."""
        s = requests.Session()
        s.headers.update(_UA)
        try:
            if self._detectar_variante(s) == "clientes":
                ok = self._login_clientes(s)
                ruta = "/Clientes"
            else:
                ok = self._login_plus(s)
                ruta = ""
            if not ok:
                logger.warning("Login fallido en %s", self.url_base)
                return False
            self._sesion = s
            self._ruta_base = ruta
            self._leer_idd()
            return True
        except Exception:
            logger.exception("Error de conexión con %s", self.url_base)
            return False

    def _leer_idd(self) -> None:
        """Lee el id de distribuidor (campo oculto `idd`) de una página interna."""
        pagina = self._ruta_base + "/Inicio.aspx" if self._ruta_base else "/"
        try:
            r = self._sesion.get(self.url_base + pagina, timeout=self.timeout)
            m = re.search(r'id="idd"[^>]*value="([^"]+)"', r.text)
            if not m:
                m = re.search(r'name="ctl00\$idd"[^>]*value="([^"]+)"', r.text)
            self._idd = m.group(1) if m else None
        except Exception:
            logger.exception("No se pudo leer idd en %s", self.url_base)

    # ---------- búsqueda y ficha ----------

    def buscar(self, consulta: str) -> List[Dict[str, Any]]:
        """Busca por EAN/ISBN o término; devuelve resultados normalizados."""
        consulta = (consulta or "").strip()
        if not consulta:
            return []
        if self._sesion is None and not self._entrar():
            return []
        if not self._idd:
            logger.warning("%s sin idd de distribuidor", self.url_base)
            return []
        try:
            r = self._sesion.post(
                f"{self.url_base}{self._ruta_base}/AjaxService.asmx/BuscadorArticulosResto",
                json={"prefix": consulta, "idd": self._idd},
                headers={"Content-Type": "application/json; charset=utf-8"},
                timeout=self.timeout)
            if r.status_code != 200:
                return []
            datos = r.json().get("d") or []
            articulos = datos[0] if datos and isinstance(datos[0], list) else datos
            return [self._normalizar_articulo(a) for a in articulos]
        except Exception:
            logger.exception("Error buscando en %s", self.url_base)
            return []

    def detalle(self, identificador: Any) -> Optional[Dict[str, Any]]:
        """Ficha completa. `identificador` es el dict de buscar() o un CI."""
        if self._sesion is None and not self._entrar():
            return None
        ci = identificador.get("_ci") if isinstance(identificador, dict) \
            else str(identificador)
        if not ci:
            return None
        try:
            r = self._sesion.get(
                f"{self.url_base}{self._ruta_base}/FichaArticulo.aspx",
                params={"Libro": ci}, timeout=self.timeout)
            if r.status_code != 200:
                return None
            return self._parsear_ficha(r.text, ci)
        except Exception:
            logger.exception("Error en ficha %s de %s", ci, self.url_base)
            return None

    # ---------- parsing ----------

    def _normalizar_articulo(self, a: Dict[str, Any]) -> Dict[str, Any]:
        """Del JSON ArticuloDist al modelo común."""
        return {
            "titulo": a.get("Titulo") or "",
            "titulo_original": "",
            "autor": (a.get("Autor") or "").strip().rstrip(","),
            "anio": "",
            "editorial": a.get("Editorial") or "",
            "isbn": a.get("ISBN") or "",
            "ean": a.get("EAN") or a.get("IsbnSinGuion") or "",
            "coleccion": a.get("Coleccion") or "",
            "demografia": self._demografia(a.get("Tema") or ""),
            "generos": [],
            "sinopsis": "",
            "imagen_url": a.get("Imagen") or "",
            "url_ficha": urljoin(
                self.url_base + self._ruta_base + "/", a.get("URLArt") or ""),
            "_ci": a.get("CI") or "",
        }

    @staticmethod
    def _demografia(materia: str) -> str:
        """El campo Materia de ZonaLibros viene como 'SHONEN-N/D-N/D':
        la demografía es el primer tramo. 'N/D' o vacío -> ''."""
        d = (materia or "").split("-")[0].strip()
        return "" if d.upper() in ("", "N/D") else d

    def _parsear_ficha(self, html: str, ci: str) -> Dict[str, Any]:
        """Los campos llevan id fijo `ctl00_MainContent_txt*` en Norma
        (txtTitulo, txtAutor, txtEditorial, txtISBN, txtEan, txtColeccion,
        txtCategoria, txtFormato, txtNumPag, txtPublicacion, txtIdioma,
        txtSinpsis...). En SD los ids son los mismos pero SIN el prefijo
        `ctl00_MainContent_` (misma plataforma, maquetación distinta).
        El prefijo opcional deja fuera el bloque "del mismo autor"
        (`dtlMismoAutor_*`) y los inputs del buscador (`txb*`)."""
        def campo(nombre: str) -> str:
            m = re.search(
                r'id="(?:ctl00_MainContent_)?' + nombre + r'"[^>]*>(.*?)</',
                html, flags=re.S)
            if not m:
                return ""
            texto = _html.unescape(re.sub(r"<[^>]+>", " ", m.group(1)))
            return re.sub(r"\s+", " ", texto).strip()

        imagen = ""
        m = re.search(r'src="([^"]*zonalibros\.com/img/[^"]+)"', html)
        if m:
            imagen = m.group(1)

        anio = ""
        m = re.search(r"(\d{4})", campo("txtPublicacion"))
        if m:
            anio = m.group(1)

        return {
            "titulo": campo("txtTitulo"),
            "titulo_original": "",
            "autor": campo("txtAutor"),
            "anio": anio,
            "editorial": campo("txtEditorial"),
            "isbn": campo("txtISBN"),
            "ean": campo("txtEan"),
            "coleccion": campo("txtColeccion"),
            # la etiqueta "Materia" de la web pinta el campo txtCategoria
            "demografia": self._demografia(campo("txtCategoria")),
            "generos": [],
            "sinopsis": campo("txtSinpsis"),
            "imagen_url": imagen,
            "url_ficha": f"{self.url_base}{self._ruta_base}/FichaArticulo.aspx?Libro={ci}",
            "_ci": ci,
        }

    # ---------- prueba ----------

    def probar(self) -> tuple:
        """Login + una búsqueda de EAN para verificar credenciales."""
        try:
            if not self._entrar():
                return (False, f"No se pudo iniciar sesión en {self.url_base}")
            return (True, f"Login correcto en {self._nombre} "
                          f"(distribuidor {self._idd})")
        except Exception as e:
            return (False, f"Error en {self._nombre}: {e}")
