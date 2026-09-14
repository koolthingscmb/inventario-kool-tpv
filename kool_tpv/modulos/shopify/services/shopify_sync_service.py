import logging
import requests
import json
from typing import List, Dict, Any, Optional, Tuple
from .shopify_config_service import ShopifyConfigService
from ..shopify_repository import ShopifyRepository

logger = logging.getLogger(__name__)

class ShopifySyncService:
    """Servicio para la sincronización real de stock y datos con Shopify."""

    API_VERSION = "2024-04"

    def __init__(self, db):
        self.db = db
        self.config_service = ShopifyConfigService(db)
        self.repo = ShopifyRepository(db)

    def _get_api_context(self) -> Optional[Tuple[str, str, str]]:
        """Obtiene las credenciales y el contexto de la API desde la configuración."""
        cfg = self.config_service.get_config()
        shop_url = cfg.get("shop_url")
        token = cfg.get("access_token")
        location_id = cfg.get("location_id")

        if not shop_url or not token or not location_id:
            logger.error("Configuración de Shopify incompleta (URL, Token o Location ID faltante).")
            return None

        # Limpiar URL por si viene con https:// o .myshopify.com
        shop_url = shop_url.replace("https://", "").replace("http://", "")
        if not shop_url.endswith(".myshopify.com"):
            shop_url = f"{shop_url}.myshopify.com"

        return shop_url, token, location_id

    def sync_stock_by_sku_prefix(self, sku_prefix: str, quantity: int, reason: Optional[str] = None) -> Dict[str, Any]:
        """Busca todas las variantes en Shopify que empiecen por el prefijo y actualiza su stock."""
        ctx = self._get_api_context()
        if not ctx:
            return {"success": False, "message": "Configuración incompleta"}

        shop_url, token, location_id = ctx
        # Usamos HTTPS y la URL completa
        endpoint = f"https://{shop_url}/admin/api/{self.API_VERSION}/graphql.json"
        headers = {
            "X-Shopify-Access-Token": token,
            "Content-Type": "application/json"
        }

        inventory_item_ids = []
        has_next_page = True
        cursor = None

        # El script original buscaba por prefijo literal. 
        # Aseguramos que el prefijo sea exacto para evitar errores de redondedo de búsqueda.
        search_query = f"sku:{sku_prefix}*"

        while has_next_page:
            query = """
            query($cursor: String, $query: String) {
                productVariants(first: 250, after: $cursor, query: $query) {
                    edges {
                        node {
                            sku
                            inventoryItem { id }
                        }
                    }
                    pageInfo {
                        hasNextPage
                        endCursor
                    }
                }
            }
            """
            variables = {"cursor": cursor, "query": search_query}

            try:
                response = requests.post(endpoint, headers=headers, json={"query": query, "variables": variables}, timeout=15)
                if response.status_code != 200:
                    return {"success": False, "message": f"Error HTTP {response.status_code}: {response.text}"}
                
                data = response.json()
                if "errors" in data:
                    return {"success": False, "message": f"Error GraphQL: {json.dumps(data['errors'])}"}

                edges = data.get("data", {}).get("productVariants", {}).get("edges", [])
                for edge in edges:
                    node = edge.get("node", {})
                    sku_shopify = (node.get("sku") or "").strip()
                    # Comprobación de prefijo para asegurar que no actualizamos de más
                    if sku_shopify.startswith(sku_prefix):
                        inv_id = node.get("inventoryItem", {}).get("id", "").split("/")[-1]
                        if inv_id:
                            inventory_item_ids.append(inv_id)

                page_info = data.get("data", {}).get("productVariants", {}).get("pageInfo", {})
                has_next_page = page_info.get("hasNextPage", False)
                cursor = page_info.get("endCursor")

            except Exception as e:
                return {"success": False, "message": f"Fallo de conexión: {str(e)}"}

        if not inventory_item_ids:
            return {"success": True, "message": "No se encontraron variantes", "updated": 0}

        # Actualizar en lote (SOBREESCRIBIR STOCK REAL)
        exito = self._update_stock_batch(inventory_item_ids, quantity, endpoint, headers, location_id)
        
        if exito:
            count = len(inventory_item_ids)
            if reason:
                msg = f"{reason} | {sku_prefix} -> Stock: {quantity} ({count} items)"
            else:
                msg = f"Sincronizados {count} items para {sku_prefix} -> Stock: {quantity}"
            
            self.repo.add_sync_log(None, "SYNC_STOCK_PREFIX", "success", msg)
            return {"success": True, "message": msg, "updated": count}
        else:
            return {"success": False, "message": "Error al aplicar el stock en Shopify"}

    def _update_stock_batch(self, item_ids: List[str], quantity: int, endpoint: str, headers: Dict, location_id: str) -> bool:
        """Actualiza el stock de una lista de IDs de inventario en lotes."""
        LIMIT = 250
        
        for i in range(0, len(item_ids), LIMIT):
            lote = item_ids[i:i + LIMIT]
            
            changes = [
                {
                    "inventoryItemId": f"gid://shopify/InventoryItem/{inv_id}",
                    "locationId": f"gid://shopify/Location/{location_id}",
                    "quantity": int(quantity)
                }
                for inv_id in lote
            ]

            mutation = """
            mutation inventorySetOnHandQuantities($input: InventorySetOnHandQuantitiesInput!) {
                inventorySetOnHandQuantities(input: $input) {
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
                    }
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
