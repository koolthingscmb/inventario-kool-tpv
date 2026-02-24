"""Config Loader - Helper para cargar configuraciones centralizadas.

Provee funciones para:

    - Cargar paletas de colores por módulo
    - Cargar estilos de botones de acción
    - Crear botones automáticamente desde config

Uso:
    from kool_tpv.utils.config_loader import load_colors, load_button_style, create_action_button
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
_BUTTONS_ACTIONS_CONFIG = _CONFIG_DIR / "buttons_actions_config.json"

# Cache para evitar leer JSON múltiples veces
_colors_cache: Optional[Dict[str, Any]] = None
_buttons_cache: Optional[Dict[str, Any]] = None


def load_colors(module: Optional[str] = None) -> Dict[str, Any]:
    """Cargar paleta de colores desde colors_config.json.

    Args:
        module: Nombre del módulo ('almacen', 'clientes', etc.)
                Si None, retorna todo el config.

    Returns:
        Dict con paleta de colores del módulo o config completo.
        Si hay error o módulo no existe, retorna colores por defecto.
    """
    global _colors_cache

    try:
        # Leer cache o cargar desde archivo
        if _colors_cache is None:
            if not _COLORS_CONFIG.exists():
                logger.error(f'colors_config.json NO encontrado en: {_COLORS_CONFIG}')
                return _get_default_colors()

            with open(_COLORS_CONFIG, 'r', encoding='utf-8') as f:
                _colors_cache = json.load(f)

        # Retornar todo o módulo específico
        if module is None:
            return _colors_cache  # type: ignore[return-value]

        if module in _colors_cache:  # type: ignore[arg-type]
            return _colors_cache[module]  # type: ignore[return-value]
        else:
            logger.warning(f'Módulo "{module}" no encontrado en colors_config.json')
            return _get_default_colors()

    except Exception:
        logger.exception('Error cargando colors_config.json')
        return _get_default_colors()


def load_button_style(button_key: str) -> Dict[str, Any]:
    """Cargar estilo de botón desde buttons_actions_config.json.

    Args:
        button_key: Clave del botón ('guardar', 'cancelar', etc.)

    Returns:
        Dict con config del botón o config por defecto si no existe.
    """
    global _buttons_cache

    try:
        # Leer cache o cargar desde archivo
        if _buttons_cache is None:
            if not _BUTTONS_ACTIONS_CONFIG.exists():
                logger.error(f'buttons_actions_config.json NO encontrado en: {_BUTTONS_ACTIONS_CONFIG}')
                return _get_default_button_style()

            with open(_BUTTONS_ACTIONS_CONFIG, 'r', encoding='utf-8') as f:
                _buttons_cache = json.load(f)

        if button_key in _buttons_cache:  # type: ignore[arg-type]
            return _buttons_cache[button_key]  # type: ignore[return-value]
        else:
            logger.warning(f'Botón "{button_key}" no encontrado en buttons_actions_config.json')
            return _get_default_button_style()

    except Exception:
        logger.exception('Error cargando buttons_actions_config.json')
        return _get_default_button_style()


def create_action_button(parent, button_key: str, command, **overrides) -> ctk.CTkButton:
    """Crear botón desde config con command personalizado.

    Args:
        parent: Widget padre donde se colocará el botón
        button_key: Clave del botón en buttons_actions_config.json
        command: Función a ejecutar al hacer click
        **overrides: Parámetros para sobrescribir config (ej: state='disabled')

    Returns:
        CTkButton configurado y listo para usar.
    """
    try:
        # Cargar config base
        config = load_button_style(button_key)

        # Aplicar overrides (no mutar cache: hacer copia)
        cfg = dict(config)
        cfg.update(overrides)

        # Convertir font array a tuple
        font_tuple = tuple(cfg.get('font', ['Courier New', 16, 'bold']))

        # Crear botón con todos los parámetros
        btn_params = {
            'master': parent,
            'text': cfg.get('text', 'BOTÓN'),
            'fg_color': cfg.get('fg_color', '#CCCCCC'),
            'hover_color': cfg.get('hover_color', '#DDDDDD'),
            'text_color': cfg.get('text_color', '#000000'),
            'border_color': cfg.get('border_color', '#000000'),
            'border_width': cfg.get('border_width', 0),
            'corner_radius': cfg.get('corner_radius', 6),
            'width': cfg.get('width', 140),
            'height': cfg.get('height', 50),
            'font': font_tuple,
            'anchor': cfg.get('anchor', 'center'),
            'compound': cfg.get('compound', 'left'),
            'command': command
        }

        # State se aplica después de crear
        state = cfg.get('state', 'normal')

        # Crear botón
        btn = ctk.CTkButton(**btn_params)

        # Aplicar state
        if state == 'disabled':
            try:
                btn.configure(state='disabled')
            except Exception:
                pass

        logger.debug(f'Botón "{button_key}" creado desde config')
        return btn

    except Exception:
        logger.exception(f'Error creando botón "{button_key}" desde config')
        # Fallback: botón básico
        try:
            return ctk.CTkButton(parent, text=button_key.upper(), command=command)
        except Exception:
            # último recurso: raise
            raise


def _get_default_colors() -> Dict[str, str]:
    """Colores por defecto si falla carga de config."""
    return {
        'primary': '#00FF00',
        'secondary': '#32CD32',
        'accent': '#7FFF00',
        'border': '#00FF00',
        'text': '#00FF00'
    }


def _get_default_button_style() -> Dict[str, Any]:
    """Estilo botón por defecto si falla carga de config."""
    return {
        'text': 'BOTÓN',
        'fg_color': '#CCCCCC',
        'hover_color': '#DDDDDD',
        'text_color': '#000000',
        'border_color': '#000000',
        'border_width': 2,
        'corner_radius': 6,
        'width': 140,
        'height': 50,
        'font': ['Courier New', 16, 'bold'],
        'state': 'normal',
        'anchor': 'center',
        'compound': 'left',
        'image': None
    }


def reload_configs() -> None:
    """Forzar recarga de configs (útil para desarrollo/testing)."""
    global _colors_cache, _buttons_cache
    _colors_cache = None
    _buttons_cache = None
    logger.info('Configs recargados desde archivos')
