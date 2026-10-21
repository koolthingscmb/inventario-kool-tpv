import logging
import unicodedata
from typing import Any, Dict, List, Optional, Tuple

from kool_tpv.modulos.shopify.services.shopify_metafields_service import ShopifyMetafieldsService

logger = logging.getLogger(__name__)


class MetacamposComicService:
    """Lee en vivo de Shopify las opciones de los metacampos de cómic.

    No guarda nada: cada llamada pide a Shopify las definiciones de metacampos
    y las entradas de sus metaobjetos, así que los valores que se ofrecen son
    siempre los que existen en la tienda en ese momento.
    """

    # clave del metacampo en Shopify -> (título del grupo en el diálogo, selección única)
    GRUPOS = (
        ("demografia", "DEMOGRAFÍA", True),
        ("genero_comic", "GÉNERO", False),
        ("subgenero_comic", "SUBGÉNERO", False),
        ("contenido_adultos", "CONTENIDO", False),
    )

    def __init__(self, db):
        self.meta_service = ShopifyMetafieldsService(db)

    @staticmethod
    def normalizar(nombre: str) -> str:
        """Minúsculas, sin tildes ni espacios dobles: 'Shōnen' -> 'shonen'."""
        txt = unicodedata.normalize("NFKD", nombre or "")
        txt = "".join(c for c in txt if not unicodedata.combining(c))
        return " ".join(txt.lower().split())

    @staticmethod
    def gids_de_nombres(entradas: List[Dict[str, Any]], nombres: List[str]) -> List[str]:
        """Nombres guardados -> GIDs, comparando normalizado."""
        por_norm = {
            MetacamposComicService.normalizar(e.get("nombre")): e.get("gid")
            for e in entradas or []
        }
        return [
            por_norm[MetacamposComicService.normalizar(n)]
            for n in nombres or []
            if MetacamposComicService.normalizar(n) in por_norm
        ]

    @staticmethod
    def nombres_de_gids(entradas: List[Dict[str, Any]], gids: List[str]) -> List[str]:
        """GIDs elegidos -> nombres legibles."""
        por_gid = {e.get("gid"): e.get("nombre") for e in entradas or []}
        return [por_gid[g] for g in gids or [] if g in por_gid]

    def obtener_opciones(self) -> Tuple[Optional[Dict[str, Dict[str, Any]]], Optional[str]]:
        """Devuelve ({clave: {'titulo', 'unico', 'entradas':[{'gid','nombre'}]}}, error).

        Recorre los 4 metacampos de cómic: definición -> metaobjeto -> entradas.
        """
        try:
            definiciones = self.meta_service.obtener_definiciones_custom()
        except Exception as e:
            logger.exception("Error cargando definiciones de metacampos")
            return None, f"No se pudieron cargar los metacampos: {e}"

        por_clave = {d.get("key"): d for d in definiciones or []}
        resultado: Dict[str, Dict[str, Any]] = {}

        for clave, titulo, unico in self.GRUPOS:
            definicion = por_clave.get(clave)
            if not definicion:
                return None, f"No existe el metacampo '{clave}' en Shopify"
            def_id = next(
                (v.get("value") for v in definicion.get("validations") or []
                 if v.get("name") == "metaobject_definition_id"),
                None,
            )
            if not def_id:
                return None, f"El metacampo '{clave}' no apunta a un metaobjeto"
            tipo = self.meta_service.obtener_tipo_metaobjeto_por_definicion(def_id)
            if not tipo:
                return None, f"No se pudo resolver el metaobjeto de '{clave}'"
            entradas = self.meta_service.obtener_entradas_metaobjeto(tipo)
            resultado[clave] = {
                "titulo": titulo,
                "unico": unico,
                "entradas": [
                    {"gid": e.get("id"), "nombre": e.get("displayName") or ""}
                    for e in entradas or []
                ],
            }

        return resultado, None
