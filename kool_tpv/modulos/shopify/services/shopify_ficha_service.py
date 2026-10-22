"""Sube a Shopify el producto de la ficha de Almacén (crear_producto).

Monta el dict `datos` que espera ShopifyProductService.product_set() a partir
del get_data() del formulario: editorial -> vendor, tipo del TPV -> productType,
taxonomy de la ficha, plantilla de CONFIG -> templateSuffix, metacampos de cómic
resueltos a GIDs y portadas locales por EAN.

En actualización, reenvía los metacampos, colecciones e imágenes del producto
Shopify que la ficha no gestiona, porque productSet sustituye las listas
completas (ver AGENTS.md).
"""
import json
import logging
import re
from html import escape
from pathlib import Path
from typing import Any, Dict, List, Optional

from kool_tpv.modulos.almacen.producto_repository import ProductoRepository
from kool_tpv.modulos.almacen.services.metacampos_comic_service import MetacamposComicService
from kool_tpv.modulos.almacen.services.portadas_service import PortadasService
from kool_tpv.modulos.shopify.services.producto_content_service import slugify_diseno
from kool_tpv.modulos.shopify.services.shopify_config_service import ShopifyConfigService
from kool_tpv.modulos.shopify.services.shopify_product_service import ShopifyProductService
from kool_tpv.modulos.shopify.shopify_repository import ShopifyRepository

logger = logging.getLogger(__name__)


class ShopifyFichaService:
    """Orquesta la subida del producto de la ficha a Shopify."""

    # Metacampos de cómic gestionados por la ficha (clave -> ¿valor único?)
    METACAMPOS_PROPIOS = {
        "demografia": True,
        "genero_comic": False,
        "subgenero_comic": False,
        "contenido_adultos": False,
    }
    # Los title_tag/description_tag de global van por el campo SEO, no por metacampo
    _SEO_KEYS = {"title_tag", "description_tag"}

    def __init__(self, db):
        self.db = db
        self.repo = ShopifyRepository(db)
        self.productos = ShopifyProductService(db)
        self.config = ShopifyConfigService(db)
        self.metacampos_svc = MetacamposComicService(db)
        self.portadas = PortadasService()
        self.producto_repo = ProductoRepository(db)

    # ---------- lecturas para el diálogo previo ----------

    def estado_subida(self, producto_id: int) -> Dict[str, Any]:
        """Estado de sincronización del producto TPV: mapping + pending_sync."""
        mapping = self.repo.get_mapping_by_product_id(producto_id) or {}
        prod = self.producto_repo.get_by_id(producto_id) or {}
        return {
            "mapeado": bool(mapping),
            "shopify_id": mapping.get("shopify_product_id"),
            "handle": mapping.get("handle"),
            "pending_sync": bool(prod.get("pending_sync")),
        }

    def buscar_por_ean(self, ean: str) -> Optional[Dict[str, Any]]:
        """Producto de Shopify que ya lleva ese barcode. Solo lectura."""
        return self.productos.buscar_por_barcode(ean)

    # ---------- montaje del payload ----------

    @staticmethod
    def _primer_ean(codigos: str) -> str:
        for parte in re.split(r"[,;\s]+", codigos or ""):
            if parte.strip():
                return parte.strip()
        return ""

    @staticmethod
    def _descripcion_html(texto: str) -> str:
        """La ficha guarda texto plano; lo envolvemos en HTML mínimo."""
        texto = (texto or "").strip()
        if not texto:
            return ""
        if "<" in texto:
            return texto
        return "".join(f"<p>{escape(p)}</p>" for p in texto.split("\n") if p.strip())

    def _metacampos_ficha(self, metacampos_json: str) -> List[Dict[str, Any]]:
        """Nombres de la ficha -> GIDs (validados contra las entradas de Shopify)."""
        try:
            valores = json.loads(metacampos_json or "{}") or {}
        except Exception:
            logger.exception("Metacampos de la ficha no son JSON válido")
            return []
        metafields = []
        for clave, unico in self.METACAMPOS_PROPIOS.items():
            valor = valores.get(clave)
            if not valor:
                continue
            nombres = [valor] if isinstance(valor, str) else list(valor)
            nombres = [n for n in nombres if str(n).strip()]
            if not nombres:
                continue
            entradas = self.metacampos_svc.obtener_entradas(clave)
            gids = self.metacampos_svc.gids_de_nombres(entradas, nombres)
            perdidos = set(nombres) - {
                e["nombre"] for e in entradas if e["gid"] in gids}
            for n in perdidos:
                logger.warning("Metacampo %s: '%s' no existe en Shopify, se omite", clave, n)
            if not gids:
                continue
            metafields.append({
                "namespace": "custom",
                "key": clave,
                "type": "metaobject_reference" if unico else "list.metaobject_reference",
                "value": gids[0] if unico else json.dumps(gids),
            })
        return metafields

    @staticmethod
    def _metacampos_a_conservar(existente: Dict[str, Any],
                                metafields_ficha: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Metacampos del producto Shopify que la ficha no gestiona: se reenvían
        tal cual para que productSet no los borre."""
        propios = set(ShopifyFichaService.METACAMPOS_PROPIOS)
        conservar = []
        for mf in existente.get("metafields", {}).get("nodes", []):
            if not str(mf.get("value") or "").strip():
                continue
            if mf.get("namespace") == "custom" and mf.get("key") in propios:
                continue
            if mf.get("namespace") == "global" and mf.get("key") in ShopifyFichaService._SEO_KEYS:
                continue
            conservar.append({
                "namespace": mf["namespace"],
                "key": mf["key"],
                "value": mf["value"],
                "type": mf["type"],
            })
        return conservar

    def _imagenes_ficha(self, ean: str) -> List[Dict[str, str]]:
        """Portadas locales del EAN con alt descriptivo."""
        alts = ["portada", "contraportada"]
        imagenes = []
        for i, ruta in enumerate(self.portadas.buscar(ean)):
            imagenes.append({"path": ruta,
                             "alt": alts[i] if i < len(alts) else f"imagen {i + 1}"})
        return imagenes

    @staticmethod
    def _imagenes_a_conservar(existente: Dict[str, Any],
                              imagenes_ficha: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Imágenes que ya están en Shopify y no coinciden con una portada local."""
        locales = {Path(i["path"]).name for i in imagenes_ficha}
        conservar = []
        for media in existente.get("media", {}).get("nodes", []):
            url = (media.get("image") or {}).get("url") or ""
            if not url:
                continue
            nombre = url.split("/")[-1].split("?")[0]
            if nombre and nombre in locales:
                continue
            conservar.append({"url": url, "alt": media.get("alt") or ""})
        return conservar

    def preparar_datos(self, form: Dict[str, Any], estado: str = "DRAFT",
                       existente: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """get_data() de la ficha -> dict `datos` para product_set()."""
        cfg = self.config.get_config()
        ean = self._primer_ean(form.get("codigos_barras"))
        titulo = (form.get("titulo") or form.get("nombre") or "").strip()
        handle = existente["handle"] if existente else slugify_diseno(titulo)

        try:
            cantidad = int(str(form.get("stock_actual") or "0").strip() or 0)
        except ValueError:
            cantidad = 0

        datos = {
            "title": titulo,
            "handle": handle,
            "description_html": self._descripcion_html(form.get("descripcion_shopify")),
            "tags": [t.strip() for t in (form.get("etiquetas") or "").split(",") if t.strip()],
            "seo_title": form.get("seo_title") or "",
            "seo_desc": form.get("seo_description") or "",
            "status": estado,
            "taxonomy_gid": form.get("shopify_taxonomy") or "",
            "product_type": (form.get("tipo_shop") or "").strip(),
            "vendor": (form.get("editorial") or "").strip(),
            "template_suffix": (cfg.get("template_suffix") or "").strip(),
            "precio": form.get("pvp") or "0",
            "product_options": [{"name": "Title", "values": [{"name": "Default Title"}]}],
            "variantes": [{
                "sku": ean or (form.get("sku") or "").strip(),
                "precio": form.get("pvp") or "0",
                "cantidad": cantidad,
                "barcode": ean,
                "tracked": True,
                "requiere_talla": 0,
                "requiere_color": 0,
                "option_values_extra": [{"optionName": "Title", "name": "Default Title"}],
            }],
            "imagenes": self._imagenes_ficha(ean),
        }

        metafields = self._metacampos_ficha(form.get("metacampos"))
        if existente:
            datos["product_id"] = existente["id"]
            datos["collections_existing"] = [
                c["id"] for c in existente.get("collections", {}).get("nodes", [])]
            metafields += self._metacampos_a_conservar(existente, metafields)
            datos["imagenes_url"] = self._imagenes_a_conservar(existente, datos["imagenes"])
        if metafields:
            datos["metafields"] = metafields
        return datos

    # ---------- subida ----------

    def subir(self, producto_id: int, form: Dict[str, Any], estado: str,
              shopify_id_confirmado: Optional[str] = None) -> Dict[str, Any]:
        """Sube la ficha a Shopify y, si va bien, deja trazado el estado local.

        `shopify_id_confirmado`: producto Shopify ya existente que el usuario
        decidió enlazar (lo encontró `buscar_por_ean`).
        """
        existente = None
        shopify_id = shopify_id_confirmado
        if not shopify_id:
            mapping = self.repo.get_mapping_by_product_id(producto_id)
            shopify_id = (mapping or {}).get("shopify_product_id")
        if shopify_id:
            existente = self.productos.cargar_producto(shopify_id)
            if not existente:
                logger.warning("El producto %s ya no existe en Shopify; se creará de nuevo", shopify_id)
                shopify_id = None

        datos = self.preparar_datos(form, estado=estado, existente=existente)
        if not datos["title"]:
            return {"success": False, "message": "La ficha no tiene título para Shopify"}

        res = self.productos.product_set(datos)
        if not res.get("success"):
            self.repo.add_sync_log(producto_id, "FICHA_SUBIDA", "error", res.get("message"))
            return res

        url = ""
        shop = (self.config.get_config().get("shop_url") or "").strip()
        if shop and res.get("handle"):
            url = f"https://{shop}/products/{res['handle']}"

        self.repo.upsert_mapping(producto_id, res["product_id"],
                                 handle=res.get("handle"), status=res.get("status"))
        self.repo.add_sync_log(
            producto_id, "FICHA_UPDATE" if shopify_id else "FICHA_CREATE",
            "success", f"{res.get('handle')} -> {res['product_id']}")
        if producto_id:
            self.producto_repo.marcar_sincronizado(producto_id, url)

        res["url"] = url
        return res

    # ---------- duplicados antiguos ----------

    def buscar_duplicados(self, titulo: str, excluir_id: Optional[str] = None
                          ) -> List[Dict[str, Any]]:
        """Productos de Shopify con el mismo título (los 'sku raros' antiguos).
        El recién subido se excluye siempre."""
        encontrados = self.productos.buscar_por_titulo(titulo)
        return [p for p in encontrados if p.get("id") != excluir_id]

    def borrar_productos(self, ids: List[str]) -> Dict[str, Any]:
        """Borra en Shopify los productos marcados. Devuelve borrados y errores."""
        borrados, errores = [], []
        for pid in ids or []:
            res = self.productos.borrar_producto(pid)
            if res.get("success"):
                borrados.append(pid)
                self.repo.add_sync_log(None, "FICHA_BORRADO", "success", pid)
            else:
                errores.append({"id": pid, "mensaje": res.get("message")})
                self.repo.add_sync_log(
                    None, "FICHA_BORRADO", "error", f"{pid}: {res.get('message')}")
        return {"borrados": borrados, "errores": errores}
