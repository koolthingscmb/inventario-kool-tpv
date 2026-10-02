import logging
import json
import requests
import time
from typing import List, Dict, Any, Optional, Tuple
from .shopify_config_service import ShopifyConfigService

logger = logging.getLogger(__name__)

class ShopifyAuthService:
    """Servicio centralizado para la autenticación con Shopify (OAuth y Legacy)."""

    def __init__(self, db):
        self.db = db
        self.config_service = ShopifyConfigService(db)

    def get_token(self) -> Optional[str]:
        """Obtiene un token válido, ya sea el persistente (shpat) o uno generado por OAuth."""
        cfg = self.config_service.get_config()
        
        cid = cfg.get("client_id")
        sec = cfg.get("client_secret")
        
        # Prioridad 1: Flujo OAuth (Client Credentials) si hay ID y Secreto
        if cid and sec:
            return self._obtener_token_oauth(cfg)
            
        # Prioridad 2: Token Legacy (shpat)
        return cfg.get("access_token")

    def _obtener_token_oauth(self, cfg: Dict[str, Any]) -> Optional[str]:
        """Gestiona la obtención y caché del token OAuth."""
        # 1. Comprobar caché en BD
        current_token = self.db.fetch_one("SELECT valor FROM configuracion WHERE clave = 'shopify_temp_token'")
        expiry = self.db.fetch_one("SELECT valor FROM configuracion WHERE clave = 'shopify_temp_token_expiry'")
        
        ahora = int(time.time())
        if current_token and expiry:
            try:
                exp_time = int(expiry[0])
                if exp_time > (ahora + 300): # 5 min de margen
                    return current_token[0]
            except: pass
                
        # 2. Si no hay o ha caducado, pedir uno nuevo
        token, _ = self.solicitar_nuevo_token(cfg)
        return token

    def solicitar_nuevo_token(self, cfg: Optional[Dict] = None) -> Tuple[Optional[str], Optional[str]]:
        """Hace la llamada técnica a Shopify para generar un access_token."""
        if cfg is None:
            cfg = self.config_service.get_config()
            
        shop = cfg.get("shop_url", "").replace("https://", "").replace("http://", "").split("/")[0]
        cid = cfg.get("client_id")
        sec = cfg.get("client_secret")
        
        if not shop or not cid or not sec:
            return None, "Faltan credenciales (URL, Client ID o Secret)"
            
        url = f"https://{shop}/admin/oauth/access_token"
        payload = {
            "grant_type": "client_credentials",
            "client_id": cid,
            "client_secret": sec
        }
        
        try:
            # Formato x-www-form-urlencoded según indica el agente
            resp = requests.post(url, data=payload, timeout=15)
            if resp.status_code != 200:
                return None, f"Shopify Auth {resp.status_code}: {resp.text}"
                
            data = resp.json()
            token = data.get("access_token")
            if not token:
                return None, "La respuesta de Shopify no contiene access_token"
                
            # Guardar en caché (duración aprox 24h)
            expires_in = data.get("expires_in", 86400)
            exp_time = int(time.time()) + int(expires_in)
            
            self.db.execute_query("INSERT OR REPLACE INTO configuracion (clave, valor) VALUES (?, ?)", ("shopify_temp_token", token))
            self.db.execute_query("INSERT OR REPLACE INTO configuracion (clave, valor) VALUES (?, ?)", ("shopify_temp_token_expiry", str(exp_time)))
            
            return token, None
        except Exception as e:
            logger.exception("Error solicitando token OAuth")
            return None, str(e)
