"""PortadasService: único dueño de la carpeta `assets/portadas/` y de la
convención de nombres de las imágenes descargadas de las fuentes.

Convención: `<ean>.<ext>` para la primera imagen, `<ean>_2.<ext>`, `<ean>_3.<ext>`...
para el resto. Enlazar producto <-> archivo se hace siempre por el EAN, sin
guardar rutas en la base de datos.

Usado por OBTENER (descargar) y por la futura subida a Shopify (buscar).
"""
import logging
from typing import List
from urllib.parse import urlsplit

import requests

from kool_tpv.paths import PORTADAS_DIR

logger = logging.getLogger(__name__)

_EXTENSIONES = (".jpg", ".jpeg", ".png", ".webp", ".gif")


class PortadasService:
    """Descarga y localiza portadas por EAN en assets/portadas/."""

    # Tope por producto para no llenar el disco si una fuente
    # devuelve la galería entera de la serie
    MAX_IMAGENES = 8

    def descargar(self, ean: str, urls) -> List[str]:
        """Descarga `urls` a `portadas/<ean>.<ext>`, `<ean>_2.<ext>`...
        Devuelve las rutas guardadas. Crea la carpeta si no existe."""
        ean = (ean or "").strip()
        if not ean:
            return []
        limpias = []
        for u in urls or []:
            if u and u not in limpias:
                limpias.append(u)
        if not limpias:
            return []

        PORTADAS_DIR.mkdir(parents=True, exist_ok=True)
        guardadas = []
        for i, url in enumerate(limpias[:self.MAX_IMAGENES]):
            try:
                r = requests.get(url, timeout=20,
                                 headers={"User-Agent": "Mozilla/5.0"})
                if r.status_code != 200 or not r.content:
                    continue
                ext = self._extension(url, r.headers.get("content-type", ""))
                nombre = f"{ean}{'_' + str(i + 1) if i else ''}{ext}"
                ruta = PORTADAS_DIR / nombre
                ruta.write_bytes(r.content)
                guardadas.append(str(ruta))
            except Exception:
                logger.warning("No se pudo descargar %s", url)
        return guardadas

    def buscar(self, ean: str) -> List[str]:
        """Devuelve las rutas de todas las portadas del EAN (`<ean>.*`,
        `<ean>_2.*`...), ordenadas: la principal primero. Lista vacía si no hay."""
        ean = (ean or "").strip()
        if not ean or not PORTADAS_DIR.exists():
            return []
        return sorted(
            str(p) for p in PORTADAS_DIR.glob(f"{ean}*")
            if p.suffix.lower() in _EXTENSIONES)

    @staticmethod
    def _extension(url: str, content_type: str) -> str:
        suf = urlsplit(url).path.rsplit(".", 1)[-1].lower()
        if suf in ("jpg", "jpeg", "png", "webp", "gif"):
            return "." + suf
        if "png" in content_type:
            return ".png"
        if "webp" in content_type:
            return ".webp"
        return ".jpg"
