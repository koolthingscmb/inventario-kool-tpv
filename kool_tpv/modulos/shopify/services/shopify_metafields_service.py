import logging
import json
import requests
from typing import List, Dict, Any, Optional, Tuple
from .shopify_config_service import ShopifyConfigService
from .shopify_auth_service import ShopifyAuthService

logger = logging.getLogger(__name__)

class ShopifyMetafieldsService:
    """Servicio especializado en la gestión avanzada de metacampos y metaobjetos."""

    DEFAULT_API_VERSION = "2026-07"

    def __init__(self, db):
        self.db = db
        self.config_service = ShopifyConfigService(db)
        self.auth_service = ShopifyAuthService(db)

    def _get_api_context(self) -> Optional[Tuple[str, str]]:
        """Obtiene credenciales y endpoint de la API, gestionando el token automático."""
        cfg = self.config_service.get_config()
        shop_url = cfg.get("shop_url")
        token = self.auth_service.get_token()

        if not shop_url or not token:
            return None

        shop_url = shop_url.replace("https://", "").replace("http://", "")
        if not shop_url.endswith(".myshopify.com"):
            shop_url = f"{shop_url}.myshopify.com"

        api_version = cfg.get("api_version") or self.DEFAULT_API_VERSION
        endpoint = f"https://{shop_url}/admin/api/{api_version}/graphql.json"
        headers = {"X-Shopify-Access-Token": token, "Content-Type": "application/json"}
        return endpoint, headers

    def obtener_nuevo_access_token(self) -> Tuple[Optional[str], Optional[str]]:
        """Solicita un nuevo token usando el servicio de autenticación."""
        return self.auth_service.solicitar_nuevo_token()

    def _graphql(self, query: str, variables: Optional[Dict] = None) -> Tuple[Optional[Dict], Optional[str]]:
        ctx = self._get_api_context()
        if not ctx:
            return None, "Configuración de Shopify incompleta"
        
        endpoint, headers = ctx
        try:
            resp = requests.post(endpoint, headers=headers, json={"query": query, "variables": variables or {}}, timeout=30)
            if resp.status_code != 200:
                return None, f"Error HTTP {resp.status_code}: {resp.text[:200]}"
            
            data = resp.json()
            if "errors" in data:
                return None, f"GraphQL: {json.dumps(data['errors'])}"
            return data.get("data"), None
        except Exception as e:
            return None, str(e)

    def obtener_definiciones_custom(self) -> List[Dict[str, Any]]:
        """Carga todas las definiciones de metacampos del namespace 'custom'."""
        definitions = []
        has_next = True
        cursor = None

        query = """
        query DefinicionesCustom($after: String) {
          metafieldDefinitions(
            ownerType: PRODUCT
            namespace: "custom"
            first: 100
            after: $after
          ) {
            nodes {
              namespace
              key
              name
              description
              type {
                name
              }
              validations {
                name
                value
              }
            }
            pageInfo {
              hasNextPage
              endCursor
            }
          }
        }
        """

        while has_next:
            data, err = self._graphql(query, {"after": cursor})
            if err:
                logger.error(f"Error cargando definiciones: {err}")
                break
            
            res = data.get("metafieldDefinitions", {})
            definitions.extend(res.get("nodes") or [])
            
            page_info = res.get("pageInfo", {})
            has_next = page_info.get("hasNextPage", False)
            cursor = page_info.get("endCursor")

        return definitions

    def obtener_entradas_metaobjeto(self, type_name: str) -> List[Dict[str, Any]]:
        """Trae todas las entradas de un tipo de metaobjeto (ej: 'mecanicas')."""
        entries = []
        has_next = True
        cursor = None

        query = """
        query EntradasMetaobjeto($type: String!, $after: String) {
          metaobjects(type: $type, first: 100, after: $after) {
            nodes {
              id
              displayName
              handle
            }
            pageInfo {
              hasNextPage
              endCursor
            }
          }
        }
        """

        while has_next:
            data, err = self._graphql(query, {"type": type_name, "after": cursor})
            if err:
                logger.error(f"Error cargando metaobjetos {type_name}: {err}")
                break
            
            res = data.get("metaobjects", {})
            entries.extend(res.get("nodes") or [])
            
            page_info = res.get("pageInfo", {})
            has_next = page_info.get("hasNextPage", False)
            cursor = page_info.get("endCursor")

        return entries

    def obtener_tipo_metaobjeto_por_definicion(self, definition_id: str) -> Optional[str]:
        """Obtiene el identificador técnico (type) a partir del GID de la definición."""
        query = """
        query GetMetaobjectType($id: ID!) {
          metaobjectDefinition(id: $id) {
            type
          }
        }
        """
        data, err = self._graphql(query, {"id": definition_id})

        if err:
            logger.error("Error al consultar la definición de metaobjeto: %s", err)
            return None

        if not data or not data.get("metaobjectDefinition"):
            logger.error(
                "La definición de metaobjeto no aparece para el ID %s: %r",
                definition_id, data
            )
            return None

        return data["metaobjectDefinition"]["type"]

    def obtener_valores_producto(self, product_id: str) -> Dict[Tuple[str, str], Dict[str, Any]]:
        """Trae todos los metacampos con valor de un producto (paginado)."""
        metafields = {}
        has_next = True
        cursor = None

        query = """
        query MetacamposProducto($productId: ID!, $after: String) {
          product(id: $productId) {
            metafields(first: 100, after: $after) {
              nodes {
                id
                namespace
                key
                value
                type
              }
              pageInfo {
                hasNextPage
                endCursor
              }
            }
          }
        }
        """

        while has_next:
            data, err = self._graphql(query, {"productId": product_id, "after": cursor})
            if err:
                logger.error(f"Error cargando valores del producto: {err}")
                break
            
            prod = data.get("product")
            if not prod: break
            
            res = prod.get("metafields", {})
            for mf in (res.get("nodes") or []):
                metafields[(mf["namespace"], mf["key"])] = mf
            
            page_info = res.get("pageInfo", {})
            has_next = page_info.get("hasNextPage", False)
            cursor = page_info.get("endCursor")

        return metafields
