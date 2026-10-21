"""Generación de SEO para la ficha de producto (botón GENERAR SEO).

Lee el prompt 'manga_seo' de la tabla shopify_prompts (versión específica
del tipo si existe, si no la genérica), lo rellena con los datos reales del
formulario y llama a OpenAI una sola vez. KOOLTHINGSHOP.md se envía como
contexto de marca en el mensaje de sistema.
"""
import logging
import re
from typing import Any, Dict, Optional, Tuple

from kool_tpv.paths import PROJECT_ROOT
from kool_tpv.modulos.almacen.services.metacampos_comic_service import (
    MetacamposComicService,
)
from .openai_service import OpenAIService
from .shopify_config_service import ShopifyConfigService
from ..shopify_prompts_repository import ShopifyPromptsRepository

logger = logging.getLogger(__name__)


def _cargar_contexto_marca() -> str:
    """Manual de marca único para el mensaje de sistema de la IA."""
    try:
        p = PROJECT_ROOT / "KOOLTHINGSHOP.md"
        if p.exists():
            return p.read_text(encoding="utf-8")
    except Exception:
        logger.exception("Error leyendo KOOLTHINGSHOP.md")
    return ""


def _series_y_tomo(nombre: str) -> Tuple[str, str]:
    """Separa la numeración final: 'Acero de sol y luna 4' -> ('Acero de sol y luna', '4')."""
    m = re.match(
        r"^(.*?)\s+(?:tomo|vol(?:umen)?\.?|n[ºo°]|#)?\s*(\d+)\s*$",
        (nombre or "").strip(), re.IGNORECASE)
    if m:
        return m.group(1).strip(" ,-"), m.group(2)
    return (nombre or "").strip(), ""


class SeoFichaService:
    """Orquesta la generación SEO de la ficha (formulario -> prompt -> IA)."""

    def __init__(self, db):
        self.db = db
        self.config_service = ShopifyConfigService(db)
        self.prompts_repo = ShopifyPromptsRepository(db)

    def _tematicas_disponibles(self) -> list:
        """Nombres de las entradas del metaobjeto Temáticas (lista cerrada).

        Se lee en vivo de Shopify; si falla, la IA recibe lista vacía y solo
        salen los tags derivados del formulario.
        """
        try:
            entradas = MetacamposComicService(self.db).obtener_entradas('subgenero_comic')
            return [e.get('nombre') for e in entradas if e.get('nombre')]
        except Exception:
            logger.exception('No se pudo leer la lista de Temáticas')
            return []

    @staticmethod
    def _slug(txt: str) -> str:
        """Tag canónico: minúsculas, sin tildes, guiones ('Tatsuki Fujimoto' -> 'tatsuki-fujimoto')."""
        norm = MetacamposComicService.normalizar(txt)
        return re.sub(r'[^a-z0-9]+', '-', norm).strip('-')

    def _tags_finales(self, datos: Dict[str, Any], tematicas_lista: list, tags_ia) -> str:
        """Tags derivados del formulario + temáticos validados de la IA.

        La IA solo clasifica contra la lista cerrada: lo que no esté en ella
        se descarta y queda en el log.
        """
        vistos: Dict[str, str] = {}
        # el autor puede venir 'APELLIDO, NOMBRE' -> se reordena en un solo tag
        autor = (datos.get('author') or '').strip()
        if autor:
            if ',' in autor:
                ap, nom = autor.split(',', 1)
                autor = f"{nom.strip()} {ap.strip()}"
            s = self._slug(autor)
            if s:
                vistos[s] = s
        for campo in ('demografia', 'generos', 'subgeneros', 'tags_actuales'):
            for trozo in (datos.get(campo) or '').split(','):
                s = self._slug(trozo)
                if s:
                    vistos.setdefault(s, s)

        lista_norm = {MetacamposComicService.normalizar(n): n for n in tematicas_lista}
        aceptados, descartados = [], []
        for prop in tags_ia if isinstance(tags_ia, list) else []:
            nombre = lista_norm.get(MetacamposComicService.normalizar(str(prop)))
            if nombre:
                s = self._slug(nombre)
                if s not in vistos:
                    vistos[s] = s
                    aceptados.append(nombre)
            else:
                descartados.append(str(prop))
        if aceptados:
            logger.info('Temáticos IA aceptados: %s', ', '.join(aceptados))
        if descartados:
            logger.info('Temáticos IA descartados (fuera de la lista): %s', ', '.join(descartados))
        return ', '.join(vistos)

    def generar(self, datos: Dict[str, Any]) -> Tuple[Optional[Dict[str, str]], Optional[str]]:
        """Devuelve (dict con titulo/seo_title/seo_description/description, error)."""
        prompt = self.prompts_repo.get_texto("manga_seo", datos.get("tipo_id"))
        if not prompt:
            return None, "No hay prompt 'manga_seo' en Shopify > IA PROMPTS."

        cfg = self.config_service.get_config()
        api_key = (cfg.get("ia_api_key") or "").strip()
        if not api_key:
            return None, "Falta la OpenAI API Key en Shopify CONFIG > IA."

        nombre = (datos.get("product_name") or "").strip()
        series = (datos.get("series") or "").strip()
        tomo = (datos.get("volume_number") or "").strip()
        if not series:
            series, tomo_auto = _series_y_tomo(nombre)
            tomo = tomo or tomo_auto

        valores = {
            "product_name": nombre,
            "tipo_producto": (datos.get("tipo_producto") or "Manga").strip(),
            "series": series,
            "volume_number": tomo,
            "author": (datos.get("author") or "").strip(),
            "publisher": (datos.get("publisher") or "").strip(),
            "language": (datos.get("language") or "").strip(),
            "format": (datos.get("format") or "").strip(),
            "isbn": (datos.get("isbn") or "").strip(),
            "demografia": (datos.get("demografia") or "").strip(),
            "generos": (datos.get("generos") or "").strip(),
            "subgeneros": (datos.get("subgeneros") or "").strip(),
            "contenido": (datos.get("contenido") or "").strip(),
            "sinopsis": (datos.get("sinopsis") or "").strip(),
        }
        tematicas = self._tematicas_disponibles()
        valores["tematicas_disponibles"] = ", ".join(tematicas)
        # replace (no .format): el prompt contiene un JSON literal con llaves.
        prompt_final = prompt
        for clave, valor in valores.items():
            prompt_final = prompt_final.replace("{" + clave + "}", valor)

        model = cfg.get("ia_model") or "gpt-4o-mini"
        res, err = OpenAIService(api_key, model).generate_json(
            prompt_final, _cargar_contexto_marca())
        if err:
            return None, err
        if not isinstance(res, dict):
            return None, "La IA no devolvió un JSON válido."
        res["tags"] = self._tags_finales(datos, tematicas, res.get("tags_tematicos"))
        return res, None
