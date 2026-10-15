"""Servicio OBTENER del formulario de producto.

Dado un EAN y la editorial elegida en el combo, resuelve la fuente de esa
editorial (tabla `editoriales` -> `editoriales_fuentes` -> plataforma),
hace `buscar(ean)` + `detalle()` y devuelve la ficha normalizada.

Solo lectura: nunca escribe en la base de datos ni en portales. Toda la
red se ejecuta aquí, en el hilo que levante la UI; la UI solo pinta.
"""
import logging
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

    def obtener(self, texto_editorial: str, ean: str) -> Dict[str, Any]:
        """Devuelve la ficha normalizada del EAN en la fuente de la editorial.

        Lanza ValueError con mensaje claro si falta algún dato o la fuente
        no encuentra el EAN.
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
