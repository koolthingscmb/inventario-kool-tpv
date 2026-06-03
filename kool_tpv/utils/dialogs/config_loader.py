"""
Carga configuración de diálogos desde JSON con fallbacks centralizados.

Implementa patrón singleton/cache: los JSON se leen una sola vez en memoria.
"""
from pathlib import Path
import logging
import json

# Cache global de configuración (se carga una sola vez)
_CONFIG_CACHE = None


# Fallbacks centralizados (solo se usan si falla la carga del JSON)
FALLBACKS = {
    'colors': {
        'bg': '#000000',
        'border': '#3498db',
        'title_text': '#00FF00',
        'message_text': '#FFFFFF',
        'button_bg': '#3498db',
        'button_hover': '#2980b9',
        'button_text': '#000000',
        'cancel_bg': '#666666',
        'cancel_hover': '#555555',
        'button_focus_border': '#FFFFFF'
    },
    'geometry': {
        'width': 580,
        'height': 400,
        'border_width': 4,
        'icon_size': 96,
        'button_width': 160,
        'button_height': 55,
        'corner_radius': 0,
        'wraplength': 'auto',
        'focus_border_width': 3,
        'entry_width': 300,
        'entry_height': 35,
        'padding_x': 20,
        'padding_y': 20
    },
    'fonts': {
        'dialog_title': ('Courier New', 28, 'bold'),
        'dialog_message': ('Courier New', 20),
        'dialog_button': ('Courier New', 18, 'bold'),
        'dialog_input': ('Roboto-Regular', 16)
    }
}


def load_dialog_config():
    """Carga configuración de diálogos desde JSON con fallbacks centralizados.

    Implementa cache: los archivos JSON se leen una sola vez.
    Las siguientes llamadas devuelven el cache en memoria.

    Returns:
        tuple: (colors_dict, fonts_dict, geometry_dict, fallbacks_dict)
    """
    global _CONFIG_CACHE

    # Si ya tenemos cache, devolverlo directamente (no leer disco)
    if _CONFIG_CACHE is not None:
        return _CONFIG_CACHE

    try:
        config_dir = Path(__file__).resolve().parents[2] / "config"

        # Cargar colores
        with open(config_dir / "colors_config.json", 'r', encoding='utf-8') as f:
            colors_data = json.load(f)
            dialogs_colors = colors_data.get('global', {}).get('dialogs', {})

        # Cargar fuentes
        with open(config_dir / "font_config.json", 'r', encoding='utf-8') as f:
            fonts_data = json.load(f)

        # Cargar geometría desde layout_config.json
        with open(config_dir / "layout_config.json", 'r', encoding='utf-8') as f:
            layout_data = json.load(f)
            geometry = layout_data.get('components', {}).get('dialog', {})

        # Guardar en cache para futuras llamadas
        _CONFIG_CACHE = (dialogs_colors, fonts_data, geometry, FALLBACKS)
        return _CONFIG_CACHE

    except Exception as e:
        logging.exception("Error cargando configuración de diálogos, usando fallbacks")
        # En caso de error, cachear fallbacks para no reintentar
        _CONFIG_CACHE = ({}, {}, {}, FALLBACKS)
        return _CONFIG_CACHE
