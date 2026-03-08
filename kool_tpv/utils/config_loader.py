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
    """Crear botón de acción usando estilos centralizados.

    Resolución de propiedades:
    - Color: `colors_config.components.action_buttons[style]`
    - Fuente: `font_config.components.action_button`
    - Geometría: `layout_config.components.action_button`

    `buttons_actions_config.json` aporta `text` y `style`.
    """
    try:
        btn_entry = load_button_style(button_key) or {}

        # Base text and state
        text = btn_entry.get('text', button_key.upper())
        state = btn_entry.get('state', 'normal')

        # Palette from colors config
        colors_root = load_colors() or {}
        components = colors_root.get('components', {}) if isinstance(colors_root, dict) else {}
        action_palettes = components.get('action_buttons', {}) if isinstance(components, dict) else {}
        style = btn_entry.get('style', 'primary')
        palette = action_palettes.get(style, {}) if isinstance(action_palettes, dict) else {}

        # Font from font_config
        fonts = load_font_config() or {}
        comp_fonts = fonts.get('components', {}) if isinstance(fonts, dict) else {}
        action_font = comp_fonts.get('action_button', {}) if isinstance(comp_fonts, dict) else {}

        # Layout geometry
        layout = load_layout_config() or {}
        comp_layout = layout.get('components', {}) if isinstance(layout, dict) else {}
        action_layout = comp_layout.get('action_button', {}) if isinstance(comp_layout, dict) else {}

        # Build CTk params with defaults and fallbacks
        fg_color = palette.get('bg') or palette.get('fg') or '#CCCCCC'
        hover_color = palette.get('hover') or '#DDDDDD'
        text_color = palette.get('text') or '#000000'
        border_color = palette.get('border') or '#000000'

        width = action_layout.get('width', 140)
        height = action_layout.get('height', 35)
        corner_radius = action_layout.get('corner_radius', 6)
        border_width = action_layout.get('border_width', 0)

        # Font tuple
        try:
            family = action_font.get('family', 'Courier New')
            size = int(action_font.get('size', 16))
            weight = action_font.get('weight')
            font_tuple = (family, size, weight) if weight else (family, size)
        except Exception:
            font_tuple = ('Courier New', 16)

        # Build params and apply overrides
        btn_params: Dict[str, Any] = {
            'master': parent,
            'text': text,
            'fg_color': fg_color,
            'hover_color': hover_color,
            'text_color': text_color,
            'border_color': border_color,
            'border_width': border_width,
            'corner_radius': corner_radius,
            'width': width,
            'height': height,
            'font': font_tuple,
            'command': command
        }

        # Allow overrides to replace any of these
        if overrides:
            btn_params.update(overrides)

        btn = ctk.CTkButton(**btn_params)

        if state == 'disabled':
            try:
                btn.configure(state='disabled')
            except Exception:
                pass

        logger.debug('Botón "%s" creado desde config (style=%s)', button_key, style)
        return btn

    except Exception:
        logger.exception('Error creando botón "%s" desde config', button_key)
        try:
            return ctk.CTkButton(parent, text=button_key.upper(), command=command)
        except Exception:
            raise


def _get_default_colors() -> Dict[str, str]:
    return {'primary': '#00FF00', 'secondary': '#32CD32', 'accent': '#7FFF00', 'border': '#00FF00', 'text': '#00FF00'}


def _get_default_button_style() -> Dict[str, Any]:
    return {'text': 'BOTÓN', 'fg_color': '#CCCCCC', 'hover_color': '#DDDDDD', 'text_color': '#000000', 'border_color': '#000000', 'border_width': 2, 'corner_radius': 6, 'width': 140, 'height': 50, 'font': ['Courier New', 16, 'bold'], 'state': 'normal'}
