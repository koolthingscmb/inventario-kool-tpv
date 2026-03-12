"""Config Loader - Helper para cargar configuraciones centralizadas.

Provee funciones para:
 - Cargar paletas de colores por módulo
 - Cargar estilos de botones de acción (resolviendo el `style` hacia paleta)
 - Crear botones automáticamente desde config centralizada
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any

import customtkinter as ctk

logger = logging.getLogger(__name__)

# Delegate creation to ButtonFactory instead of old palette/layout system
from kool_tpv.utils.factories.button_factory import ButtonFactory

# Paths a archivos de configuración
_CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"
_COLORS_CONFIG = _CONFIG_DIR / "colors_config.json"
_FONT_CONFIG = _CONFIG_DIR / "font_config.json"
_LAYOUT_CONFIG = _CONFIG_DIR / "layout_config.json"
_BUTTONS_ACTIONS_CONFIG = _CONFIG_DIR / "buttons_actions_config.json"

# Cache para evitar leer JSON múltiples veces
_colors_cache: Optional[Dict[str, Any]] = None
_fonts_cache: Optional[Dict[str, Any]] = None
_layout_cache: Optional[Dict[str, Any]] = None
_buttons_cache: Optional[Dict[str, Any]] = None


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        if not path.exists():
            logger.warning('%s no encontrado', path)
            return {}
        with path.open('r', encoding='utf-8') as fh:
            return json.load(fh) or {}
    except Exception:
        logger.exception('Error leyendo JSON: %s', path)
        return {}


def load_colors(module: Optional[str] = None) -> Dict[str, Any]:
    global _colors_cache
    if _colors_cache is None:
        _colors_cache = _load_json(_COLORS_CONFIG)
    if module is None:
        return _colors_cache
    return _colors_cache.get(module, {})


def load_font_config() -> Dict[str, Any]:
    global _fonts_cache
    if _fonts_cache is None:
        _fonts_cache = _load_json(_FONT_CONFIG)
    return _fonts_cache


def load_layout_config() -> Dict[str, Any]:
    global _layout_cache
    if _layout_cache is None:
        _layout_cache = _load_json(_LAYOUT_CONFIG)
    return _layout_cache


def load_button_style(button_key: str) -> Dict[str, Any]:
    """Leer mapping minimalista de `buttons_actions_config.json`.

    El archivo ahora contiene solo `text` y `style` (y opcional `state`).
    """
    global _buttons_cache
    if _buttons_cache is None:
        _buttons_cache = _load_json(_BUTTONS_ACTIONS_CONFIG)
    return _buttons_cache.get(button_key, {})


def create_action_button(parent, button_key: str, command, **overrides) -> ctk.CTkButton:
    """Crear botón de acción delegando a `ButtonFactory` usando un `style_key` map.

    - Mantiene la firma y compatibilidad con `button_key` existentes.
    - Mapea `button_key` a `style_key` y delega la creación a la fábrica.
    """
    try:
        mapping = {
            'guardar': 'action_primary',
            'nuevo_limpiar': 'action_secondary',
            'cancelar': 'action_secondary',
            'eliminar': 'action_danger',
            'sincronizar': 'action_success',
            'buscar_data': 'action_secondary',
            'consultar_albaranes': 'action_secondary',
            'mapeo_csv': 'action_warning',
            'exportar': 'action_warning',
            'imprimir': 'action_secondary',
        }

        style_key = mapping.get(button_key, 'action_primary')
        text = (button_key or '').upper()

        # Delegate to ButtonFactory and pass-through any overrides
        return ButtonFactory.create_button(
            parent=parent,
            text=text,
            command=command,
            style_key=style_key,
            **overrides,
        )

    except Exception:
        logger.exception('Error creando botón desde ButtonFactory para %s', button_key)
        try:
            return ctk.CTkButton(parent, text=(button_key or '').upper(), command=command)
        except Exception:
            raise


# Legacy default helpers removed: styling is centralized in config JSON and ButtonFactory.
