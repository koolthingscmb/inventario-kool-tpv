"""
Loader para ui_dialogs.json - Configuración unificada de dialogs.

Patrón singleton/cache: el JSON se lee una sola vez en memoria.
"""
from pathlib import Path
import logging
import json
from typing import Dict, Any, Optional

# Cache global (carga una sola vez)
_UI_DIALOGS_CACHE: Optional[Dict[str, Any]] = None


def load_ui_dialogs() -> Dict[str, Any]:
    """Carga configuración de dialogs desde ui_dialogs.json con cache.

    Returns:
        Dict con la estructura: {"dialogs": {"info": {...}, "warning": {...}, ...}}
        Si falla, retorna diccionario vacío.
    """
    global _UI_DIALOGS_CACHE

    if _UI_DIALOGS_CACHE is not None:
        return _UI_DIALOGS_CACHE

    try:
        config_dir = Path(__file__).resolve().parent
        ui_dialogs_path = config_dir / "ui_dialogs.json"

        with open(ui_dialogs_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        _UI_DIALOGS_CACHE = data
        return _UI_DIALOGS_CACHE

    except FileNotFoundError:
        logging.error("No se encontró ui_dialogs.json")
        _UI_DIALOGS_CACHE = {}
        return _UI_DIALOGS_CACHE
    except json.JSONDecodeError as e:
        logging.error(f"Error parseando ui_dialogs.json: {e}")
        _UI_DIALOGS_CACHE = {}
        return _UI_DIALOGS_CACHE
    except Exception:
        logging.exception("Error cargando ui_dialogs.json")
        _UI_DIALOGS_CACHE = {}
        return _UI_DIALOGS_CACHE


def get_dialog_config(dialog_type: str) -> Dict[str, Any]:
    """Obtiene configuración completa de un tipo de dialog específico.

    Args:
        dialog_type: 'info', 'warning', 'error', 'success', 'password', 'input'

    Returns:
        Dict con window, colors, fonts, spacing, buttons. Vacío si no existe.
    """
    config = load_ui_dialogs()
    dialogs = config.get('dialogs', {})
    return dialogs.get(dialog_type, {})


def clear_cache():
    """Limpia el cache. Útil para hot-reload en desarrollo."""
    global _UI_DIALOGS_CACHE
    _UI_DIALOGS_CACHE = None
