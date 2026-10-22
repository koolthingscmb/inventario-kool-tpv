import logging
import requests
import json
import uuid
import threading
from typing import List, Dict, Any, Optional, Tuple
from .shopify_config_service import ShopifyConfigService
from .shopify_auth_service import ShopifyAuthService
from ..shopify_repository import ShopifyRepository

logger = logging.getLogger(__name__)

class ShopifySyncService:
    """Servicio para la sincronización real de stock y datos con Shopify."""

    DEFAULT_API_VERSION = "2026-07"

    # Candado de clase: el trabajador de sync corre de uno en uno en toda la app
    _sync_lock = threading.Lock()

    def __init__(self, db):
        self.db = db
        self.config_service = ShopifyConfigService(db)
        self.auth_service = ShopifyAuthService(db)
        self.repo = ShopifyRepository(db)
        self._ctx_error = None

    def _get_api_context(self) -> Optional[Tuple[str, str, str, str]]:
        """Obtiene las credenciales y el contexto de la API desde la configuración."""
        cfg = self.config_service.get_config()
        shop_url = cfg.get("shop_url")
        location_id = cfg.get("location_id")
        api_version = cfg.get("api_version") or self.DEFAULT_API_VERSION
        self._ctx_error = None

        if not shop_url or not location_id:
            self._ctx_error = "Configuración de Shopify incompleta (falta URL de tienda o almacén)"
            logger.error(self._ctx_error)
            return None

        token = self.auth_service.get_token()
        if not token:
            motivo = getattr(self.auth_service, 'last_error', None) or "respuesta vacía"
            self._ctx_error = f"No se pudo obtener el token de Shopify: {motivo}"
            logger.error(self._ctx_error)
            return None

        # Limpiar URL por si viene con https:// o .myshopify.com
        shop_url = shop_url.replace("https://", "").replace("http://", "")
        if not shop_url.endswith(".myshopify.com"):
            shop_url = f"{shop_url}.myshopify.com"

        return shop_url, token, location_id, api_version

    def sync_stock_by_sku_prefix(self, sku_prefix: str, quantity: int, reason: Optional[str] = None) -> Dict[str, Any]:
        """Busca todas las variantes en Shopify que empiecen por el prefijo y actualiza su stock."""
        res = self._ejecutar_sync_stock(sku_prefix, quantity)
        count = res.get("updated", 0)
        if res.get("success") and count:
            if reason:
                msg = f"{reason} | {sku_prefix} -> Stock: {quantity} ({count} items)"
            else:
                msg = f"Sincronizados {count} items para {sku_prefix} -> Stock: {quantity}"
            self.repo.add_sync_log(None, "SYNC_STOCK_PREFIX", "success", msg, sku=sku_prefix, cantidad=quantity)
            res["message"] = msg
        elif res.get("success"):
            self.repo.add_sync_log(None, "SYNC_STOCK_PREFIX", "sin_variantes",
                                   f"{sku_prefix}: sin variantes en la web con ese SKU",
                                   sku=sku_prefix, cantidad=quantity)
        else:
            self.repo.add_sync_log(None, "SYNC_STOCK_PREFIX", "error",
                                   f"{sku_prefix}: {res.get('message')}",
                                   sku=sku_prefix, cantidad=quantity)
        return res

    def _ejecutar_sync_stock(self, sku_prefix: str, quantity: int) -> Dict[str, Any]:
        """Núcleo del sync por prefijo de SKU: actualiza el stock en Shopify. No escribe en el log."""
        def _fail(msg: str) -> Dict[str, Any]:
            return {"success": False, "message": msg}

        ctx = self._get_api_context()
        if not ctx:
            return _fail(self._ctx_error or "Configuración incompleta")

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
                                    quantities(names: ["on_hand"]) {
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
                                if q.get("name") == "on_hand":
                                    current = q.get("quantity") or 0
                                    break
                            inventory_items.append({"inv_id": inv_id, "current": int(current)})

                page_info = data.get("data", {}).get("productVariants", {}).get("pageInfo", {})
                has_next_page = page_info.get("hasNextPage", False)
                cursor = page_info.get("endCursor")

            except Exception as e:
                return _fail(f"Fallo de conexión: {str(e)}")

        if not inventory_items:
            return {"success": True, "message": "No se encontraron variantes", "updated": 0}

        # Actualizar en lote (SOBREESCRIBIR STOCK REAL)
        exito = self._update_stock_batch(inventory_items, quantity, endpoint, headers, location_id)
        
        if exito:
            return {"success": True, "message": "OK", "updated": len(inventory_items)}
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
            mutation inventorySetQuantities($input: InventorySetQuantitiesInput!, $idempotencyKey: String!) {
                inventorySetQuantities(input: $input) @idempotent(key: $idempotencyKey) {
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
                        "name": "on_hand",
                        "reason": "correction",
                        "quantities": changes
                    },
                    "idempotencyKey": str(uuid.uuid4())
                }
            }

            try:
                response = requests.post(endpoint, headers=headers, json=payload, timeout=15)
                data = response.json()

                if "errors" in data or data.get("data", {}).get("inventorySetQuantities", {}).get("userErrors"):
                    err_msg = json.dumps(data.get("errors") or data.get("data", {}).get("inventorySetQuantities", {}).get("userErrors"))
                    logger.error(f"Error actualizando lote de stock: {err_msg}")
                    return False
            except Exception:
                logger.exception("Error de red actualizando lote de stock")
                return False

        return True

    # --- Trabajador de la cola de sincronización ---

    def procesar_pendientes_async(self, reintentar_errores: bool = False) -> None:
        """Lanza el trabajador de sync en segundo plano. Nunca hay dos a la vez."""
        threading.Thread(
            target=self.procesar_pendientes,
            kwargs={"reintentar_errores": reintentar_errores},
            daemon=True
        ).start()

    def procesar_pendientes(self, reintentar_errores: bool = False) -> int:
        """Procesa los encargos 'pendiente' del log de sync, de uno en uno.

        Un solo trabajador a la vez: el token de Shopify se renueva una vez
        por tanda, no en una estampida de hilos. Con `reintentar_errores`
        también vuelve a intentar los errores que aún tengan intentos.
        """
        if not ShopifySyncService._sync_lock.acquire(blocking=False):
            return 0
        try:
            procesados = 0
            if reintentar_errores:
                for row in self.repo.get_errores_reintentables():
                    self.repo.incrementar_reintentos(row["id"])
                    procesados += self._procesar_encargo(row)
            # Repite hasta vaciar la cola (pueden llegar encargos mientras trabaja)
            while True:
                pendientes = self.repo.get_pendientes()
                if not pendientes:
                    break
                for row in pendientes:
                    procesados += self._procesar_encargo(row)
            return procesados
        finally:
            ShopifySyncService._sync_lock.release()

    def _procesar_encargo(self, row: Dict[str, Any]) -> int:
        """Ejecuta un encargo de sync y deja su resultado real en el propio registro."""
        sku = (row.get("sku") or "").strip()
        if not sku:
            self.repo.marcar_resultado(row["id"], "error", "Encargo de sync sin SKU")
            return 0

        cantidad = row.get("cantidad")
        if cantidad is None:
            st = self.db.fetch_one(
                "SELECT cantidad FROM produccion_stock_colores_tallas WHERE sku = ?", (sku,))
            cantidad = st[0] if st else 0

        res = self._ejecutar_sync_stock(sku, int(cantidad))
        if res.get("success") and res.get("updated", 0) > 0:
            motivo = row.get("mensaje") or "Sincronización de stock"
            msg = f"{motivo} | {sku} -> Stock: {cantidad} ({res['updated']} items)"
            self.repo.marcar_resultado(row["id"], "success", msg)
            self._mostrar_toast(f"Shopify: {sku} actualizado", "success")
            return 1
        if res.get("success"):
            self.repo.marcar_resultado(row["id"], "sin_variantes",
                                       f"{sku}: sin variantes en la web con ese SKU")
            self._mostrar_toast(f"Shopify: {sku} no existe en la web", "warning")
            return 0
        self.repo.marcar_resultado(row["id"], "error", f"{sku}: {res.get('message')}")
        self._mostrar_toast(f"Shopify: {sku} NO sincronizado ({res.get('message')})", "error")
        return 0

    def _mostrar_toast(self, mensaje: str, tipo: str = "success") -> None:
        """Muestra un toast en el hilo de la UI desde el trabajador de sync."""
        try:
            import tkinter as tk
            from kool_tpv.utils.widgets.notificaciones.toast_widget import ToastWidget
            root = getattr(tk, "_default_root", None)
            if root:
                root.after(0, lambda: ToastWidget.show(root, mensaje, tipo=tipo))
        except Exception:
            pass
