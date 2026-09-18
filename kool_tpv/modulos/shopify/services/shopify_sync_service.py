import logging
import requests
import json
import uuid
from typing import List, Dict, Any, Optional, Tuple
from .shopify_config_service import ShopifyConfigService
from ..shopify_repository import ShopifyRepository

logger = logging.getLogger(__name__)

class ShopifySyncService:
    """Servicio para la sincronización real de stock y datos con Shopify."""

    DEFAULT_API_VERSION = "2026-07"

    def __init__(self, db):
        self.db = db
        self.config_service = ShopifyConfigService(db)
        self.repo = ShopifyRepository(db)

    def _get_api_context(self) -> Optional[Tuple[str, str, str, str]]:
        """Obtiene las credenciales y el contexto de la API desde la configuración."""
        cfg = self.config_service.get_config()
        shop_url = cfg.get("shop_url")
        token = cfg.get("access_token")
        location_id = cfg.get("location_id")
        api_version = cfg.get("api_version") or self.DEFAULT_API_VERSION

        if not shop_url or not token or not location_id:
            logger.error("Configuración de Shopify incompleta (URL, Token o Location ID faltante).")
            return None

        # Limpiar URL por si viene con https:// o .myshopify.com
        shop_url = shop_url.replace("https://", "").replace("http://", "")
        if not shop_url.endswith(".myshopify.com"):
            shop_url = f"{shop_url}.myshopify.com"

        return shop_url, token, location_id, api_version

    def sync_stock_by_sku_prefix(self, sku_prefix: str, quantity: int, reason: Optional[str] = None) -> Dict[str, Any]:
        """Busca todas las variantes en Shopify que empiecen por el prefijo y actualiza su stock."""
        def _fail(msg: str) -> Dict[str, Any]:
            self.repo.add_sync_log(None, "SYNC_STOCK_PREFIX", "error", f"{sku_prefix}: {msg}")
            return {"success": False, "message": msg}

        ctx = self._get_api_context()
        if not ctx:
            return _fail("Configuración incompleta")

        shop_url, token, location_id, api_version = ctx
        # Usamos HTTPS y la URL completa
        endpoint = f"https://{shop_url}/admin/api/{api_version}/graphql.json"
        headers = {
            "X-Shopify-Access-Token": token,
            "Content-Type": "application/json"
        }
        location_gid = f"gid://shopify/Location/{location_id}"

        inventory_items = []
        has_next_page = True
        cursor = None

        # El script original buscaba por prefijo literal. 
        # Aseguramos que el prefijo sea exacto para evitar errores de redondedo de búsqueda.
        search_query = f"sku:{sku_prefix}*"

        while has_next_page:
            query = """
            query($cursor: String, $query: String, $locationId: ID!) {
                productVariants(first: 250, after: $cursor, query: $query) {
                    edges {
                        node {
                            sku
                            inventoryItem {
                                id
                                inventoryLevel(locationId: $locationId) {
                                    quantities(names: ["available"]) {
                                        name
                                        quantity
                                    }
                                }
                            }
                        }
                    }
                    pageInfo {
                        hasNextPage
                        endCursor
                    }
                }
            }
            """
            variables = {"cursor": cursor, "query": search_query, "locationId": location_gid}

            try:
                response = requests.post(endpoint, headers=headers, json={"query": query, "variables": variables}, timeout=15)
                if response.status_code != 200:
                    return _fail(f"Error HTTP {response.status_code}: {response.text}")
                
                data = response.json()
                if "errors" in data:
                    return _fail(f"Error GraphQL: {json.dumps(data['errors'])}")

                edges = data.get("data", {}).get("productVariants", {}).get("edges", [])
                for edge in edges:
                    node = edge.get("node", {})
                    sku_shopify = (node.get("sku") or "").strip()
                    # Comprobación de prefijo para asegurar que no actualizamos de más
                    if sku_shopify.startswith(sku_prefix):
                        inv_item = node.get("inventoryItem") or {}
                        inv_id = (inv_item.get("id") or "").split("/")[-1]
                        if inv_id:
                            current = 0
                            level = inv_item.get("inventoryLevel") or {}
                            for q in (level.get("quantities") or []):
                                if q.get("name") == "available":
                                    current = q.get("quantity") or 0
                                    break
                            inventory_items.append({"inv_id": inv_id, "current": int(current)})

                page_info = data.get("data", {}).get("productVariants", {}).get("pageInfo", {})
                has_next_page = page_info.get("hasNextPage", False)
                cursor = page_info.get("endCursor")

            except Exception as e:
                return _fail(f"Fallo de conexión: {str(e)}")

        if not inventory_items:
            self.repo.add_sync_log(None, "SYNC_STOCK_PREFIX", "error", f"{sku_prefix}: sin variantes en la web con ese SKU")
            return {"success": True, "message": "No se encontraron variantes", "updated": 0}

        # Actualizar en lote (SOBREESCRIBIR STOCK REAL)
        exito = self._update_stock_batch(inventory_items, quantity, endpoint, headers, location_id)
        
        if exito:
            count = len(inventory_items)
            if reason:
                msg = f"{reason} | {sku_prefix} -> Stock: {quantity} ({count} items)"
            else:
                msg = f"Sincronizados {count} items para {sku_prefix} -> Stock: {quantity}"
            
            self.repo.add_sync_log(None, "SYNC_STOCK_PREFIX", "success", msg)
            return {"success": True, "message": msg, "updated": count}
        else:
            return _fail("Error al aplicar el stock en Shopify")

    def _update_stock_batch(self, items: List[Dict[str, Any]], quantity: int, endpoint: str, headers: Dict, location_id: str) -> bool:
        """Actualiza el stock de una lista de items de inventario en lotes."""
        LIMIT = 250
        
        for i in range(0, len(items), LIMIT):
            lote = items[i:i + LIMIT]
            
            changes = [
                {
                    "inventoryItemId": f"gid://shopify/InventoryItem/{it['inv_id']}",
                    "locationId": f"gid://shopify/Location/{location_id}",
                    "quantity": int(quantity),
                    "changeFromQuantity": int(it["current"])
                }
                for it in lote
            ]

            mutation = """
            mutation inventorySetOnHandQuantities($input: InventorySetOnHandQuantitiesInput!, $idempotencyKey: String!) {
                inventorySetOnHandQuantities(input: $input) @idempotent(key: $idempotencyKey) {
                    userErrors {
                        field
                        message
                    }
                }
            }
            """
            payload = {
                "query": mutation,
                "variables": {
                    "input": {
                        "reason": "correction",
                        "setQuantities": changes
                    },
                    "idempotencyKey": str(uuid.uuid4())
                }
            }

            try:
                response = requests.post(endpoint, headers=headers, json=payload, timeout=15)
                data = response.json()

                if "errors" in data or data.get("data", {}).get("inventorySetOnHandQuantities", {}).get("userErrors"):
                    err_msg = json.dumps(data.get("errors") or data.get("data", {}).get("inventorySetOnHandQuantities", {}).get("userErrors"))
                    logger.error(f"Error actualizando lote de stock: {err_msg}")
                    return False
            except Exception:
                logger.exception("Error de red actualizando lote de stock")
                return False

        return True
