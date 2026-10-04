"""Preparación de los datos de EDICIÓN de un producto existente en Shopify.

La pantalla SUBIDA (modo EDITAR) recoge lo que hay en los campos y lo pasa a este builder, que devuelve
los datos listos para ShopifyProductService.product_set. No conoce widgets: todo entra por parámetros.

Dos caminos para las variantes:
  - Con SKUs preparados (subvista SKUS): se usan tal cual y se añade Sorpresa conservando SKU/precio.
  - Sin SKUs: se reenvían las variantes que ya tiene el producto en Shopify, sin tocar stock ni precio.
"""
import logging
from typing import Any, Dict, List, Optional

from .producto_content_service import slugify_diseno
from .shopify_upload_builder import ShopifyUploadBuilder

logger = logging.getLogger(__name__)


class ShopifyEdicionBuilder:
    def __init__(self, db, upload_builder: Optional[ShopifyUploadBuilder] = None):
        self.upload_builder = upload_builder or ShopifyUploadBuilder(db)

    def construir_datos(self, base: Dict[str, Any], producto: Dict[str, Any], titulo_base: str,
                        variante_combo: str, tipo_nombre: str, skus_preparados: Optional[Dict[str, Any]],
                        primer_cuerpo: Optional[str], imagenes_locales: List[Dict[str, Any]],
                        imagenes_web: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Devuelve los 'datos' de product_set para actualizar el producto cargado.

        base: datos comunes ya calculados por la pantalla (tags, SEO, estado, taxonomía, recargo...).
        variante_combo: variante TPV seleccionada en la pantalla.
        skus_preparados: resultado de la subvista SKUS (o None).
        primer_cuerpo: HTML de la primera caja BODY de la pantalla (None si no hay cajas).
        """
        base = dict(base)
        prod = producto

        if skus_preparados:
            variantes_preparadas = list(skus_preparados.get("variantes") or [])
            variante_nombre = skus_preparados.get("genero") or variante_combo
            diseno = skus_preparados.get("diseno")
            diseno_codigo = diseno.codigo if diseno else (prod.get("handle") or slugify_diseno(titulo_base))

            # Color "Sorpresa": conserva el SKU/precio que ya tenga en Shopify y va sin control de inventario
            if self.upload_builder.aplica_sorpresa(tipo_nombre):
                variantes_preparadas.extend(self.upload_builder.variantes_sorpresa(
                    tipo_nombre, variante_nombre, [v["talla"] for v in variantes_preparadas],
                    existentes=self.upload_builder.sorpresas_existentes(prod)))

            base_variantes = variantes_preparadas
            # Evitar que product_set vuelva a construir el SKU (ya vienen listos)
            base["codigo_categoria"] = ""
            base["iniciales"] = ""
        else:
            # Flujo estándar: solo lo que ya tiene Shopify
            variantes_existentes = []
            for v in prod.get("variants", {}).get("nodes", []):
                v_talla, v_color = "", ""
                for opt in v.get("selectedOptions", []):
                    if opt["name"].upper() == "TALLA": v_talla = opt["value"]
                    if opt["name"].upper() == "COLOR": v_color = opt["value"]

                variantes_existentes.append({
                    "sku": v.get("sku") or "",
                    "precio": str(v.get("price") or "0"),
                    "color": v_color,
                    "talla": v_talla,
                    "cantidad": -1,  # No tocar stock si no pasamos por SKUs
                    # El precio viene de Shopify tal cual: no sumarle el recargo otra vez
                    "precio_ya_final": True,
                    # Sorpresa sin control de inventario también al editar sin pasar por SKUs
                    "tracked": not self.upload_builder.es_color_sorpresa(v_color),
                })
            variante_nombre = variante_combo
            diseno_codigo = prod.get("handle") or slugify_diseno(titulo_base)
            base_variantes = variantes_existentes

        # Reconstruir las opciones del producto para Shopify
        product_options = []
        for o in prod.get("options", []):
            values = []
            for x in o.get("values", []):
                if isinstance(x, dict):
                    values.append({"name": x.get("name", "")})
                else:
                    values.append({"name": x})
            product_options.append({"name": o["name"], "values": values})

        datos = dict(base)

        # Si el tipo usa variantes como tipo, el product_type es el nombre de la variante
        if base.get("use_variant_as_type") and variante_nombre:
            datos["product_type"] = variante_nombre

        # Reconstruir el título igual que en modo nuevo: base + variante
        title = titulo_base
        if not base.get("agrupar_variantes", False) and variante_nombre:
            title = f"{titulo_base} | {variante_nombre}"

        datos.update({
            "title": title,
            "handle": prod.get("handle") or slugify_diseno(titulo_base),
            "description_html": primer_cuerpo if primer_cuerpo is not None else prod.get("descriptionHtml") or "",
            "product_id": prod["id"],
            "variantes_input": None,
            "variantes": base_variantes,
            "product_options": product_options,
            "imagenes": imagenes_locales,
            "imagenes_url": imagenes_web,
            "diseno_codigo": diseno_codigo,
            "genero": variante_nombre,
        })
        return datos
