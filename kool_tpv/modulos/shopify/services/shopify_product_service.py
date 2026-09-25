import logging
import json
import mimetypes
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

import requests

from .shopify_config_service import ShopifyConfigService
from ..shopify_repository import ShopifyRepository
from kool_tpv.modulos.produccion.repositories.produccion_tallas_grupos_repository import ProduccionTallasGruposRepository

logger = logging.getLogger(__name__)

class ShopifyProductService:
    """Crea y actualiza productos en Shopify desde el TPV (subvista SUBIDA).

    Usa la mutación productSet (idempotente por handle/ID), staged uploads
    para imágenes locales y publishablePublish para los canales de venta.
    """

    # La versión se edita en CONFIG -> GENERAL. Fallback si está vacía.
    DEFAULT_API_VERSION = "2026-07"

    def __init__(self, db):
        self.db = db
        self.config_service = ShopifyConfigService(db)
        self.repo = ShopifyRepository(db)

    # ------------------------------------------------------------------
    # Infraestructura
    # ------------------------------------------------------------------

    def _api_context(self) -> Optional[Tuple[str, Dict[str, str], str]]:
        cfg = self.config_service.get_config()
        shop_url = cfg.get("shop_url")
        token = cfg.get("access_token")
        location_id = cfg.get("location_id")
        if not shop_url or not token:
            return None
        shop_url = shop_url.replace("https://", "").replace("http://", "")
        if not shop_url.endswith(".myshopify.com"):
            shop_url = f"{shop_url}.myshopify.com"
        api_version = cfg.get("api_version") or self.DEFAULT_API_VERSION
        endpoint = f"https://{shop_url}/admin/api/{api_version}/graphql.json"
        headers = {"X-Shopify-Access-Token": token, "Content-Type": "application/json"}
        return endpoint, headers, location_id

    def _graphql(self, endpoint: str, headers: Dict, query: str, variables: Dict) -> Tuple[Optional[Dict], Optional[str]]:
        try:
            resp = requests.post(endpoint, headers=headers, json={"query": query, "variables": variables}, timeout=30)
            if resp.status_code != 200:
                return None, f"HTTP {resp.status_code}: {resp.text[:300]}"
            data = resp.json()
            if data.get("errors"):
                return None, f"GraphQL: {json.dumps(data['errors'])[:500]}"
            return data.get("data"), None
        except Exception as e:
            return None, f"Conexión: {e}"

    # ------------------------------------------------------------------
    # Datos locales: variantes del género y SKU
    # ------------------------------------------------------------------

    def get_variantes_stock(self, variante_id: int) -> List[Dict[str, Any]]:
        """Filas de stock base (color x talla) para una variante (Hombre, Mujer...).

        Incluye flags de la variante (talla/color requeridos y precio web).
        """
        rows = self.db.fetch_all(
            """
            SELECT s.sku, c.nombre AS color, t.nombre AS talla, s.cantidad,
                   tv.requiere_talla, tv.requiere_color, tv.precio_web
            FROM produccion_stock_colores_tallas s
            JOIN tipos_variantes tv ON tv.id = s.variante_id
            LEFT JOIN produccion_colores c ON c.id = s.color_id
            LEFT JOIN produccion_tallas t ON t.id = s.talla_id
            WHERE s.variante_id = ?
            ORDER BY c.nombre, t.orden, t.nombre
            """,
            (variante_id,)
        )
        return [dict(r) for r in (rows or [])]

    @staticmethod
    def build_sku(base_sku: str, codigo_categoria: str = "", iniciales: str = "") -> str:
        """SKU web: base + sufijo + iniciales diseño."""
        partes = [p for p in (base_sku, codigo_categoria, iniciales) if p]
        return "-".join(partes)

    @staticmethod
    def iniciales_diseno(nombre: str) -> str:
        """Iniciales del diseño para el sufijo del SKU (ej: 'Hulk Buster' -> 'HB')."""
        palabras = [p for p in nombre.replace("-", " ").split() if p]
        return "".join(p[0] for p in palabras).upper()[:4]

    # ------------------------------------------------------------------
    # Imágenes: staged upload de archivos locales
    # ------------------------------------------------------------------

    def staged_upload(self, endpoint: str, headers: Dict, file_path: str) -> Optional[str]:
        """Sube un archivo local a Shopify. Devuelve el resourceUrl para productSet."""
        path = Path(file_path)
        mime = mimetypes.guess_type(str(path))[0] or "image/jpeg"

        mutation = """
        mutation stagedUploadsCreate($input: [StagedUploadInput!]!) {
            stagedUploadsCreate(input: $input) {
                stagedTargets { url resourceUrl parameters { name value } }
                userErrors { field message }
            }
        }
        """
        data, err = self._graphql(endpoint, headers, mutation, {
            "input": [{"resource": "IMAGE", "filename": path.name, "mimeType": mime, "httpMethod": "POST"}]
        })
        if err:
            logger.error(f"stagedUploadsCreate: {err}")
            return None
        result = data.get("stagedUploadsCreate", {})
        if result.get("userErrors"):
            logger.error(f"stagedUploadsCreate userErrors: {result['userErrors']}")
            return None
        target = (result.get("stagedTargets") or [{}])[0]
        url, resource_url = target.get("url"), target.get("resourceUrl")
        if not url or not resource_url:
            return None

        fields = {p["name"]: p["value"] for p in target.get("parameters", [])}
        try:
            with open(path, "rb") as f:
                resp = requests.post(url, data=fields, files={"file": (path.name, f, mime)}, timeout=60)
            if resp.status_code not in (200, 201, 204):
                logger.error(f"Subida de imagen fallida ({resp.status_code}): {resp.text[:200]}")
                return None
        except Exception:
            logger.exception(f"Error subiendo {path.name}")
            return None
        return resource_url

    # ------------------------------------------------------------------
    # Crear / actualizar producto (productSet)
    # ------------------------------------------------------------------

    def product_set(self, datos: Dict[str, Any]) -> Dict[str, Any]:
        """Crea o actualiza un producto. Si datos['product_id'] existe -> edición.

        datos: {
          handle, title, description_html, tags (list), seo_title, seo_desc,
          precio, recargo_tallas, variantes (rows de get_variantes_stock),
          codigo_categoria, iniciales, imagenes [{path, alt}],
          taxonomy_gid, status ('DRAFT'|'ACTIVE'), product_id (opcional),
          stock_sorpresa (opcional -> pone stock 50 a todas las variantes)
        }
        """
        ctx = self._api_context()
        if not ctx:
            return {"success": False, "message": "Configuración de Shopify incompleta"}
        endpoint, headers, location_id = ctx

        # 1) Subir imágenes locales -> staged uploads (alt = "{título} - {alt}")
        files_input = []
        for img in datos.get("imagenes", []):
            url = self.staged_upload(endpoint, headers, img["path"])
            if url:
                alt = img.get("alt", "")
                files_input.append({
                    "filename": Path(img["path"]).name,
                    "originalSource": url,
                    "alt": f"{datos['title']} - {alt}" if alt else datos["title"],
                    "contentType": "IMAGE",
                    "duplicateResolutionMode": "REPLACE",
                })
            else:
                return {"success": False, "message": f"Fallo subiendo imagen: {img['path']}"}

        # Imágenes ya existentes en Shopify (modo edición: se reenvían por URL)
        for img in datos.get("imagenes_url", []):
            url = img["url"]
            # Extraer nombre real de la URL (ej: imagen.jpg?v=123 -> imagen.jpg)
            filename = url.split('/')[-1].split('?')[0]
            if not filename:
                filename = "imagen_web.jpg"
            
            files_input.append({
                "filename": filename,
                "originalSource": url,
                "alt": img.get("alt", datos["title"]),
                "contentType": "IMAGE",
                "duplicateResolutionMode": "REPLACE",
            })

        # 2) Construir opciones y variantes
        variantes_input = datos.get("variantes_input")
        product_options = datos.get("product_options")
        sku_qty = {}
        if variantes_input is None:
            colores, tallas = [], []
            variantes_input = []
            
            def _parse_float(val):
                if val is None or str(val).lower() == 'none' or str(val).strip() == '':
                    return 0.0
                try:
                    return float(str(val).replace(',', '.').replace('€', '').strip() or 0)
                except:
                    return 0.0

            precio_base = _parse_float(datos.get("precio"))
            recargo = _parse_float(datos.get("recargo_tallas"))
            
            # Obtener tallas grandes del grupo configurado
            tallas_grandes = set()
            grupo_id = datos.get("recargo_grupo_id")
            if grupo_id and str(grupo_id).lower() != 'none':
                try:
                    repo_grupos = ProduccionTallasGruposRepository(self.db)
                    nombres = repo_grupos.get_nombres_tallas_por_grupo(int(grupo_id))
                    tallas_grandes = {n.strip().upper() for n in nombres}
                    if not tallas_grandes:
                        logger.warning(f"El grupo de tallas ID {grupo_id} está vacío o no existe.")
                except Exception:
                    logger.exception(f"Error cargando tallas grandes del grupo {grupo_id}")

            for v in datos.get("variantes", []):
                color, talla = v.get("color") or "", v.get("talla") or ""
                requiere_color = bool(v.get("requiere_color", 1))
                requiere_talla = bool(v.get("requiere_talla", 1))

                if requiere_color and color and color not in colores:
                    colores.append(color)
                if requiere_talla and talla and talla not in tallas:
                    tallas.append(talla)

                # Precio: precio_web > precio explícito > base
                precio_variante_cents = v.get("precio_web") or 0
                if precio_variante_cents:
                    precio_variante = float(precio_variante_cents) / 100
                elif v.get("precio") is not None:
                    precio_variante = float(v["precio"])
                else:
                    precio_variante = precio_base

                # Aplicar recargo si la talla es grande y no es un precio explícito (ej: Sorpresa)
                if v.get("precio") is None and talla.strip().upper() in tallas_grandes:
                    precio_variante += recargo

                built_sku = self.build_sku(v["sku"], datos.get("codigo_categoria", ""), datos.get("iniciales", ""))
                sku_qty[built_sku] = int(v.get("cantidad") or 0)

                option_values = []
                if requiere_talla and talla:
                    option_values.append({"optionName": "Talla", "name": talla})
                if requiere_color and color:
                    option_values.append({"optionName": "Color", "name": color})

                variantes_input.append({
                    "sku": built_sku,
                    "price": f"{precio_variante:.2f}",
                    "inventoryItem": {"tracked": True},
                    "optionValues": option_values,
                })
            product_options = []
            if tallas:
                product_options.append({"name": "Talla", "values": [{"name": t} for t in tallas]})
            if colores:
                product_options.append({"name": "Color", "values": [{"name": c} for c in colores]})

        # 3) Input del producto
        product_input = {
            "title": datos["title"],
            "handle": datos["handle"],
            "descriptionHtml": datos.get("description_html", ""),
            "tags": datos.get("tags", []),
            "status": datos.get("status", "DRAFT"),
            "seo": {"title": datos.get("seo_title", ""), "description": datos.get("seo_desc", "")},
            "variants": variantes_input,
        }
        if product_options:
            product_input["productOptions"] = product_options
        if datos.get("taxonomy_gid"):
            product_input["category"] = datos["taxonomy_gid"]
        if datos.get("product_type"):
            product_input["productType"] = datos["product_type"]
        if datos.get("vendor"):
            product_input["vendor"] = datos["vendor"]
        if datos.get("template_suffix"):
            product_input["templateSuffix"] = datos["template_suffix"]
        if files_input:
            product_input["files"] = files_input

        mutation = """
        mutation productSet($input: ProductSetInput!, $identifier: ProductSetIdentifiers) {
            productSet(input: $input, identifier: $identifier, synchronous: true) {
                product {
                    id handle title status
                    variants(first: 250) { nodes { id sku inventoryItem { id } } }
                }
                userErrors { field message }
            }
        }
        """
        identifier = {"id": datos["product_id"]} if datos.get("product_id") else None
        data, err = self._graphql(endpoint, headers, mutation, {"input": product_input, "identifier": identifier})
        if err:
            self.repo.add_sync_log(None, "PRODUCT_SET", "error", err)
            return {"success": False, "message": err}

        result = data.get("productSet", {})
        if result.get("userErrors"):
            msg = json.dumps(result["userErrors"])[:500]
            self.repo.add_sync_log(None, "PRODUCT_SET", "error", msg)
            return {"success": False, "message": msg}

        product = result.get("product", {})
        product_id, handle = product.get("id"), product.get("handle")

        # 4) Asignar stock por variante (si viene del TPV y es positivo)
        if sku_qty and location_id:
            quantities = []
            for v in product.get("variants", {}).get("nodes", []):
                inv_id = v.get("inventoryItem", {}).get("id")
                sku = v.get("sku")
                qty = sku_qty.get(sku)
                if inv_id and qty is not None and qty > 0:
                    quantities.append({
                        "inventory_item_id": inv_id,
                        "quantity": qty,
                    })
            if quantities:
                ok = self._set_inventory(endpoint, headers, quantities, location_id)
                if not ok:
                    logger.warning(f"Producto {handle} creado pero falló el stock")

        # 5) Mapeo local
        if datos.get("diseno_codigo") and datos.get("genero"):
            self.repo.upsert_diseno_mapping(datos["diseno_codigo"], datos["genero"], product_id, handle)

        # 6) Publicar en los canales de venta (como hacía el script)
        pub = self.publicar_en_canales(product_id)
        if not pub.get("success"):
            logger.warning(f"Producto {handle}: no se pudo publicar en canales: {pub.get('message')}")

        accion = "PRODUCT_UPDATE" if datos.get("product_id") else "PRODUCT_CREATE"
        self.repo.add_sync_log(None, accion, "success", f"{handle} -> {product_id}")
        return {"success": True, "product_id": product_id, "handle": handle,
                "status": product.get("status"), "message": f"Producto {handle} OK"}

    def _set_inventory(self, endpoint, headers, quantities, location_id) -> bool:
        changes = [{
            "inventoryItemId": q["inventory_item_id"],
            "locationId": f"gid://shopify/Location/{location_id}",
            "quantity": int(q["quantity"]),
            "changeFromQuantity": 0,
        } for q in quantities]
        data, err = self._graphql(endpoint, headers, """
            mutation inventorySetOnHandQuantities($input: InventorySetOnHandQuantitiesInput!, $idempotencyKey: String!) {
                inventorySetOnHandQuantities(input: $input) @idempotent(key: $idempotencyKey) {
                    userErrors { field message }
                    inventoryAdjustmentGroup { createdAt reason }
                }
            }
        """, {
            "input": {"reason": "correction", "setQuantities": changes},
            "idempotencyKey": str(uuid.uuid4()),
        })
        if err:
            logger.error(f"Error stock: {err}")
            return False
        errs = data.get("inventorySetOnHandQuantities", {}).get("userErrors")
        if errs:
            logger.error(f"userErrors stock: {errs}")
            return False
        return True

    # ------------------------------------------------------------------
    # Publicar en canales
    # ------------------------------------------------------------------

    def publicar_en_canales(self, product_id: str) -> Dict[str, Any]:
        """Publica el producto en todos los canales (como hacía el script)."""
        ctx = self._api_context()
        if not ctx:
            return {"success": False, "message": "Configuración incompleta"}
        endpoint, headers, _ = ctx

        data, err = self._graphql(endpoint, headers, """
            { publications(first: 50) { edges { node { id name } } } }
        """, {})
        if err:
            return {"success": False, "message": err}
        pubs = [e["node"]["id"] for e in data.get("publications", {}).get("edges", [])]
        if not pubs:
            return {"success": False, "message": "No hay canales de publicación"}

        data, err = self._graphql(endpoint, headers, """
            mutation publishablePublish($id: ID!, $input: [PublicationInput!]!) {
                publishablePublish(id: $id, input: $input) {
                    publishable { availablePublicationsCount { count } }
                    userErrors { field message }
                }
            }
        """, {"id": product_id, "input": [{"publicationId": p} for p in pubs]})
        if err:
            return {"success": False, "message": err}
        errs = data.get("publishablePublish", {}).get("userErrors")
        if errs:
            return {"success": False, "message": json.dumps(errs)[:300]}
        self.repo.add_sync_log(None, "PRODUCT_PUBLISH", "success", f"{product_id} publicado en {len(pubs)} canales")
        return {"success": True, "message": f"Publicado en {len(pubs)} canales"}

    # ------------------------------------------------------------------
    # Actualizar SKUs de variantes existentes
    # ------------------------------------------------------------------

    def actualizar_skus(self, product_id: str, variantes: List[Dict[str, str]]) -> Dict[str, Any]:
        """Actualiza solo los SKUs de variantes existentes (productVariantsBulkUpdate).

        variantes: [{"id": gid_variante, "sku": "..."}]
        """
        ctx = self._api_context()
        if not ctx:
            return {"success": False, "message": "Configuración de Shopify incompleta"}
        endpoint, headers, _ = ctx

        inputs = [{"id": v["id"], "inventoryItem": {"sku": v["sku"]}}
                  for v in variantes if v.get("id") and v.get("sku")]
        if not inputs:
            return {"success": False, "message": "Sin SKUs que actualizar"}

        data, err = self._graphql(endpoint, headers, """
            mutation productVariantsBulkUpdate($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
                productVariantsBulkUpdate(productId: $productId, variants: $variants) {
                    productVariants { id sku }
                    userErrors { field message }
                }
            }
        """, {"productId": product_id, "variants": inputs})
        if err:
            self.repo.add_sync_log(None, "SKU_UPDATE", "error", err)
            return {"success": False, "message": err}

        result = data.get("productVariantsBulkUpdate", {})
        if result.get("userErrors"):
            msg = json.dumps(result["userErrors"])[:500]
            self.repo.add_sync_log(None, "SKU_UPDATE", "error", msg)
            return {"success": False, "message": msg}

        n = len(result.get("productVariants") or [])
        self.repo.add_sync_log(None, "SKU_UPDATE", "success",
                               f"{n} SKUs actualizados en {product_id}")
        return {"success": True, "message": f"{n} SKUs actualizados"}

    # ------------------------------------------------------------------
    # Modo EDITAR: buscar y cargar productos de Shopify
    # ------------------------------------------------------------------

    def buscar_productos(self, texto: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Busca productos en Shopify por título/handle/SKU."""
        ctx = self._api_context()
        if not ctx:
            return []
        endpoint, headers, _ = ctx
        data, err = self._graphql(endpoint, headers, """
            query($q: String!, $limit: Int!) {
                products(first: $limit, query: $q) {
                    edges { node { id title handle status } }
                }
            }
        """, {"q": f"*{texto}*", "limit": limit})
        if err or not data:
            logger.error(f"buscar_productos: {err}")
            return []
        return [e["node"] for e in data.get("products", {}).get("edges", [])]

    def cargar_producto(self, product_id: str) -> Optional[Dict[str, Any]]:
        """Carga todos los datos editables de un producto existente."""
        ctx = self._api_context()
        if not ctx:
            return None
        endpoint, headers, _ = ctx
        data, err = self._graphql(endpoint, headers, """
            query($id: ID!) {
                product(id: $id) {
                    id title handle status descriptionHtml tags productType
                    seo { title description }
                    options { name values }
                    variants(first: 250) {
                        nodes { id sku price selectedOptions { name value } }
                    }
                    media(first: 50) {
                        nodes { id alt ... on MediaImage { image { url } } }
                    }
                }
            }
        """, {"id": product_id})
        if err or not data or not data.get("product"):
            logger.error(f"cargar_producto {product_id}: {err}")
            return None
        return data["product"]
