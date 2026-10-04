"""Preparación de los trabajos de subida de PRODUCTOS NUEVOS a Shopify.

La pantalla SUBIDA recoge lo que hay en los campos y lo pasa a este builder, que devuelve la lista
de datos listos para ShopifyProductService.product_set (uno por variante TPV, o uno solo si el tipo
agrupa variantes). No conoce widgets: todo entra por parámetros.
"""
import logging
from typing import Any, Dict, List, Optional

from .producto_content_service import ProductoContentService, slugify_diseno
from .shopify_config_service import ShopifyConfigService
from .shopify_product_service import ShopifyProductService
from .shopify_upload_builder import ShopifyUploadBuilder

logger = logging.getLogger(__name__)


class ErrorPreparacion(Exception):
    """Error de validación esperado: el mensaje se muestra tal cual al usuario."""


class ShopifyNuevoBuilder:
    VENDOR_POR_DEFECTO = "Kool Things"
    GENERO_AGRUPADO = "Pack"

    def __init__(self, db, product_service: Optional[ShopifyProductService] = None,
                 content_service: Optional[ProductoContentService] = None,
                 upload_builder: Optional[ShopifyUploadBuilder] = None):
        self.product_service = product_service or ShopifyProductService(db)
        self.content_service = content_service or ProductoContentService(db)
        self.upload_builder = upload_builder or ShopifyUploadBuilder(db)
        self.config_service = ShopifyConfigService(db)

    def construir_trabajos(self, base: Dict[str, Any], titulo: str, beneficio: str, tipo_nombre: str,
                           tipo_id: Optional[int], variantes_disponibles: List[Dict[str, Any]],
                           cuerpos: Dict[str, str], imagenes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Devuelve los 'datos' de product_set para un producto nuevo.

        base: datos comunes ya calculados por la pantalla (tags, SEO, estado, taxonomía, recargo...).
        cuerpos: descripción HTML por nombre de variante, en el orden de la pantalla.
        imagenes: imágenes locales [{path, alt}].
        Lanza ErrorPreparacion si no hay variantes activas o no hay stock que subir.
        """
        if not variantes_disponibles:
            raise ErrorPreparacion("El tipo seleccionado no tiene variantes activas para web")

        cfg = self.config_service.get_config()
        vendor = cfg.get("marca") or self.VENDOR_POR_DEFECTO
        iniciales = self.product_service.iniciales_diseno(titulo)
        slug_titulo = slugify_diseno(titulo)
        con_sorpresa = self.upload_builder.aplica_sorpresa(tipo_nombre)
        agrupar = base.get("agrupar_variantes", False)

        trabajos: List[Dict[str, Any]] = []
        todas_las_variantes: List[Dict[str, Any]] = []

        for v_info in variantes_disponibles:
            variante = v_info["nombre"]
            variantes = self.product_service.get_variantes_stock(v_info["id"])
            if not variantes:
                continue

            for v in variantes:
                v["cantidad"] = int(v.get("cantidad") or 0)
                if agrupar:
                    # El nombre de la variante TPV se convierte en una opción de Shopify
                    v["tpv_variante_nombre"] = variante

            # Color "Sorpresa": solo en camisetas, una opción extra por talla (sin control de inventario)
            if con_sorpresa:
                variantes.extend(self.upload_builder.variantes_sorpresa(
                    tipo_nombre, variante, [v["talla"] for v in variantes], marcar_variante_tpv=agrupar))

            if agrupar:
                todas_las_variantes.extend(variantes)
                continue

            # Flujo normal: un producto por variante
            datos = dict(base)
            if base.get("use_variant_as_type"):
                datos["product_type"] = variante
            datos.update({
                "title": f"{titulo} | {variante}",
                "handle": f"{slug_titulo}-{slugify_diseno(variante)}",
                "description_html": cuerpos.get(variante, ""),
                "seo_title": self.content_service.seo_title_for(titulo, variante, beneficio=beneficio, tipo_id=tipo_id),
                "tags": base["tags"] + [variante],
                "variantes": variantes,
                "iniciales": iniciales,
                "imagenes": [dict(i) for i in imagenes],
                "vendor": vendor,
                "diseno_codigo": slug_titulo,
                "genero": variante,
            })
            trabajos.append(datos)

        # Si agrupamos, UN SOLO trabajo con todas las variantes
        if agrupar and todas_las_variantes:
            self._preparar_agrupadas(todas_las_variantes)
            datos = dict(base)
            datos.update({
                "title": titulo,
                "handle": slug_titulo,
                "description_html": next(iter(cuerpos.values()), ""),
                "seo_title": self.content_service.seo_title_for(titulo, "", beneficio=beneficio, tipo_id=tipo_id),
                "tags": base["tags"],
                "variantes": todas_las_variantes,
                "iniciales": iniciales,
                "imagenes": [dict(i) for i in imagenes],
                "vendor": vendor,
                "diseno_codigo": slug_titulo,
                "genero": self.GENERO_AGRUPADO,
            })
            trabajos.append(datos)

        if not trabajos:
            raise ErrorPreparacion("No hay stock para las variantes seleccionadas")
        return trabajos

    @staticmethod
    def _preparar_agrupadas(variantes: List[Dict[str, Any]]):
        """El nombre de la variante TPV pasa a ser el valor de la opción 'Talla' de Shopify."""
        for v in variantes:
            talla_original = v.get("talla") or ""
            variante_tpv = v.get("tpv_variante_nombre") or ""
            v["requiere_talla"] = 1   # fuerza que el motor cree la opción en Shopify
            v["requiere_color"] = 0   # normalmente las láminas no tienen opción color
            if not talla_original or talla_original.upper() == "ÚNICA":
                v["talla"] = variante_tpv
            else:
                v["talla"] = f"{variante_tpv} {talla_original}"
