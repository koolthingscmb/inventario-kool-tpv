"""Servicio OBTENER del formulario de producto.

Dado un EAN y la editorial elegida en el combo, resuelve la fuente de esa
editorial (tabla `editoriales` -> `editoriales_fuentes` -> plataforma),
hace `buscar(ean)` + `detalle()` y devuelve la ficha normalizada.

Solo lectura: nunca escribe en la base de datos ni en portales. Toda la
red se ejecuta aquí, en el hilo que levante la UI; la UI solo pinta.
"""
import logging
import re
import unicodedata
from typing import Any, Dict

from kool_tpv.modulos.almacen.services.fuentes_editorial_service import (
    FuentesEditorialService,
)
from kool_tpv.modulos.almacen.services.fuentes.registro import RegistroFuentes

logger = logging.getLogger(__name__)


class ObtenerDatosService:
    """Obtiene los datos de un producto por EAN desde la fuente editorial."""

    def __init__(self, db):
        self.fuentes = FuentesEditorialService(db)
        self.registro = RegistroFuentes(self.fuentes)

    def obtener(self, texto_editorial: str, ean: str,
                nombre: str = "") -> Dict[str, Any]:
        """Devuelve la ficha normalizada en la fuente de la editorial.

        La mayoría de fuentes buscan por EAN; las marcadas con
        `busca_por_nombre` (p.ej. panini_web) buscan por `nombre` y se
        verifica cada ficha por su ISBN contra el EAN.

        Lanza ValueError con mensaje claro si falta algún dato o la fuente
        no encuentra el producto.
        """
        ean = (ean or "").strip()
        if not ean:
            raise ValueError("No hay EAN en el campo CÓDIGOS")
        if not (texto_editorial or "").strip():
            raise ValueError("Elige una EDITORIAL de la lista")
        fuente = self.registro.fuente_para_editorial(texto_editorial)
        if fuente is None:
            raise ValueError(
                f"La editorial '{texto_editorial}' no tiene fuente de búsqueda")

        if getattr(fuente, "busca_por_nombre", False):
            return self._obtener_por_nombre(fuente, nombre, ean)

        resultados = fuente.buscar(ean)
        if not resultados:
            raise ValueError(f"El EAN {ean} no aparece en la fuente")

        ean_limpio = ean.replace("-", "")
        elegido = next(
            (r for r in resultados
             if (r.get("ean") or r.get("isbn") or "").replace("-", "")
             == ean_limpio),
            resultados[0])
        detalle = fuente.detalle(elegido) or {}
        # la ficha puede venir con huecos: se completan con la búsqueda
        for k, v in elegido.items():
            if k not in detalle or not detalle.get(k):
                detalle[k] = v
        return detalle

    def _obtener_por_nombre(self, fuente, nombre: str,
                            ean: str) -> Dict[str, Any]:
        """Fuentes que solo buscan por texto (panini_web): se prueba cada
        candidata y solo vale la ficha cuyo ISBN coincide con el EAN."""
        nombre = (nombre or "").strip()
        if not nombre:
            raise ValueError(
                "Esta editorial busca por nombre: rellena el campo NOMBRE")
        resultados = fuente.buscar(nombre)
        if not resultados:
            raise ValueError(
                f"'{nombre}' no aparece en la web de la editorial")

        ean_limpio = ean.replace("-", "")
        verifica_isbn = getattr(fuente, "verifica_isbn", True)
        for candidato in resultados:
            # sin ISBN (ivrea_web): el match es por nombre de serie exacto
            if not verifica_isbn and not self._misma_serie(nombre, candidato):
                continue
            detalle = fuente.detalle(candidato) or {}
            if verifica_isbn:
                isbn = (detalle.get("isbn") or detalle.get("ean") or ""
                        ).replace("-", "")
                if not (isbn and isbn == ean_limpio):
                    continue
            for k, v in candidato.items():
                if not detalle.get(k):
                    detalle[k] = v
            return detalle
        if verifica_isbn:
            raise ValueError(
                f"Ninguna ficha de '{nombre}' coincide con el EAN {ean}")
        raise ValueError(
            f"Ninguna serie de la web coincide con '{nombre}'")

    @classmethod
    def _misma_serie(cls, nombre: str, candidato: Dict[str, Any]) -> bool:
        """'ONE PUNCH MAN 01' == la serie 'One Punch-Man' (número fuera)."""
        serie = cls._norm(cls._sin_numero(nombre))
        return bool(serie) and serie == cls._norm(
            candidato.get("titulo") or "")

    @staticmethod
    def _sin_numero(nombre: str) -> str:
        """Quita el número de tomo del final: 'x nº 01/11', 'x vol.2', 'x 04'.
        El marcador (nº/vol/tomo/#) va como palabra suelta o no va."""
        return re.sub(r"(?:\s+(?:n[ºo°]|núm|vol|tomo|#)\.?\s*|\s+)"
                      r"\d+(?:[/\-]\d+)?\s*$", "", nombre,
                      flags=re.I).strip()

    @staticmethod
    def _norm(texto: str) -> str:
        """Minúsculas, sin acentos ni signos: para comparar títulos."""
        t = unicodedata.normalize("NFKD", texto or "")
        t = "".join(c for c in t if not unicodedata.combining(c))
        return re.sub(r"[^a-z0-9]+", "", t.lower())
