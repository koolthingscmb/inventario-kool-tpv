"""Registro de fuentes: editorial escrita -> fuente que la busca.

Pregunta a `FuentesEditorialService` (tablas `fuentes`/`editoriales`) qué
fuente cubre esa editorial e instancia la clase adecuada según su
`plataforma`:

    "zonalibros"  -> ZonaLibrosSource(url, credenciales)    # Norma, SD...
    "planeta"     -> PlanetaSource(url, credenciales)
    "shopify"     -> ShopifyPublicoSource(url)              # sin credenciales
    "panini_web"   -> PaniniWebSource(url)                  # web pública, por nombre
    "ivrea_web"    -> IvreaWebSource(url)                   # web pública, por nombre
    "udl_web"      -> UdlWebSource(url)                     # web pública, por EAN
    "astiberri_web" -> AstiberriWebSource(url)              # web pública, por nombre
    "azeta_web"    -> AzetaWebSource(url, credenciales)     # portal de cliente, por EAN

Añadir una plataforma nueva = una clase BaseFuente + una línea en
TIPOS_FUENTE. Las clases son código interno: nunca se editan desde la UI.
"""
import logging
from typing import Any, Dict, List, Optional

from .astiberri_web_source import AstiberriWebSource
from .azeta_web_source import AzetaWebSource
from .base_fuente import BaseFuente
from .ivrea_web_source import IvreaWebSource
from .panini_web_source import PaniniWebSource
from .planeta_source import PlanetaSource
from .shopify_publico_source import ShopifyPublicoSource
from .udl_web_source import UdlWebSource
from .zonalibros_source import ZonaLibrosSource

logger = logging.getLogger(__name__)


def _creds(f: Dict[str, Any]) -> Dict[str, str]:
    return {"nif": f.get("nif", ""), "usuario": f.get("usuario", ""),
            "password": f.get("password", "")}


def _crear_zonalibros(f: Dict[str, Any]) -> BaseFuente:
    return ZonaLibrosSource(url=f.get("url", ""), credenciales=_creds(f),
                            nombre=f.get("nombre") or str(f.get("id", "")))


def _crear_planeta(f: Dict[str, Any]) -> BaseFuente:
    return PlanetaSource(url=f.get("url", ""), credenciales=_creds(f))


def _crear_shopify(f: Dict[str, Any]) -> BaseFuente:
    return ShopifyPublicoSource(url=f.get("url", ""))


def _crear_panini_web(f: Dict[str, Any]) -> BaseFuente:
    return PaniniWebSource(url=f.get("url", ""))


def _crear_ivrea_web(f: Dict[str, Any]) -> BaseFuente:
    return IvreaWebSource(url=f.get("url", ""))


def _crear_udl_web(f: Dict[str, Any]) -> BaseFuente:
    return UdlWebSource(url=f.get("url", ""))


def _crear_astiberri_web(f: Dict[str, Any]) -> BaseFuente:
    return AstiberriWebSource(url=f.get("url", ""))


def _crear_azeta_web(f: Dict[str, Any]) -> BaseFuente:
    return AzetaWebSource(url=f.get("url", ""), credenciales=_creds(f))


TIPOS_FUENTE = {
    "zonalibros": _crear_zonalibros,
    "planeta": _crear_planeta,
    "shopify": _crear_shopify,
    "panini_web": _crear_panini_web,
    "ivrea_web": _crear_ivrea_web,
    "udl_web": _crear_udl_web,
    "astiberri_web": _crear_astiberri_web,
    "azeta_web": _crear_azeta_web,
}


class RegistroFuentes:
    """Resuelve qué fuente toca para cada editorial usando el servicio."""

    def __init__(self, servicio):
        """`servicio` es una instancia de FuentesEditorialService."""
        self.servicio = servicio

    def fuente_para_editorial(self, texto_editorial: str) -> Optional[BaseFuente]:
        """Devuelve la fuente principal lista para usar, o None si no hay."""
        fuente = self.servicio.fuente_para_editorial(texto_editorial)
        if not fuente:
            return None
        return self._crear(fuente)

    def fuentes_para_editorial(self, texto_editorial: str) -> List[BaseFuente]:
        """Fuentes listas para usar: [principal, reserva si la hay]."""
        salida = []
        for datos in self.servicio.fuentes_para_editorial(texto_editorial):
            fuente = self._crear(datos)
            if fuente:
                salida.append(fuente)
        return salida

    def fuente_para_portal(self, fuente_id: Any) -> Optional[BaseFuente]:
        """Instancia la fuente por su id en la tabla `editoriales_fuentes`."""
        fuente = self.servicio.fuente_por_id(fuente_id)
        if not fuente:
            return None
        return self._crear(fuente)

    def _crear(self, fuente: Dict[str, Any]) -> Optional[BaseFuente]:
        creador = TIPOS_FUENTE.get(fuente.get("plataforma"))
        if not creador:
            logger.warning("Plataforma desconocida: %s",
                           fuente.get("plataforma"))
            return None
        return creador(fuente)
