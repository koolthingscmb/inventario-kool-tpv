"""Paquete de controllers de pago."""
import logging
import json
from pathlib import Path

logger = logging.getLogger(__name__)


def load_config(config_name: str) -> dict:
    """Cargar archivo de configuración."""
    try:
        from kool_tpv.paths import CONFIG_DIR
        config_path = CONFIG_DIR / config_name
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        logger.exception(f"Error cargando {config_name}")
        return {}


def norm_color(val: str) -> str:
    """Normaliza valores de color: elimina hashes repetidos y espacios."""
    try:
        if not val:
            return ''
        if not isinstance(val, str):
            return val
        s = val.strip()
        if not s:
            return ''
        s_low = s.lower()
        if s_low in ("transparent", "none"):
            return s_low
        s = s.lstrip('#')
        return '#' + s
    except Exception:
        return val


# Importar ConfigHelper para que esté disponible
from .config_helper import PaymentConfigHelper

__all__ = ['load_config', 'norm_color', 'PaymentConfigHelper']
