"""
Carga configuración de diálogos desde JSON con fallbacks centralizados.

Implementa patrón singleton/cache: los JSON se leen una sola vez en memoria.
"""
from pathlib import Path
import logging
import json

# Importar nuevo loader de ui_dialogs.json (cuando esté disponible)
try:
    from kool_tpv.config.ui_config_loader import load_ui_dialogs
    _UI_LOADER_AVAILABLE = True
except ImportError:
    _UI_LOADER_AVAILABLE = False
    load_ui_dialogs = None

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
        'button_focus_border': '#FFFFFF',
        'title_bar_bg': '#3498db',
        'title_bar_text': '#FFFFFF'
    },
    'geometry': {
        'width': 580,
        'height': 400,
        'border_width': 4,
        'icon_size': 24,
        'button_width': 160,
        'button_height': 55,
        'title_bar_height': 50,
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


def _transform_ui_dialogs_to_legacy_format(ui_data: dict) -> tuple:
    """Transforma datos de ui_dialogs.json al formato legacy esperado por los dialogs.

    Args:
        ui_data: Dict cargado de ui_dialogs.json

    Returns:
        tuple: (colors_dict, fonts_dict, geometry_dict, fallbacks_dict)
    """
    dialogs_data = ui_data.get('dialogs', {})

    # Transformar a formato legacy (colors por tipo de dialog)
    colors_dict = {}
    for dialog_type, config in dialogs_data.items():
        colors = config.get('colors', {})
        colors_dict[dialog_type] = {
            'bg': colors.get('bg', FALLBACKS['colors']['bg']),
            'border': colors.get('border', FALLBACKS['colors']['border']),
            'title_text': colors.get('title_text', FALLBACKS['colors']['title_text']),
            'message_text': colors.get('message_text', FALLBACKS['colors']['message_text']),
            'button_bg': colors.get('button_bg', FALLBACKS['colors']['button_bg']),
            'button_hover': colors.get('button_hover', FALLBACKS['colors']['button_hover']),
            'button_text': colors.get('button_text', FALLBACKS['colors']['button_text']),
            'cancel_bg': colors.get('cancel_bg', FALLBACKS['colors']['cancel_bg']),
            'cancel_hover': colors.get('cancel_hover', FALLBACKS['colors']['cancel_hover']),
            'button_focus_border': colors.get('button_focus_border', FALLBACKS['colors']['button_focus_border']),
            'title_bar_bg': colors.get('title_bar_bg', FALLBACKS['colors']['title_bar_bg']),
            'title_bar_text': colors.get('title_bar_text', FALLBACKS['colors']['title_bar_text']),
        }

    # Construir fonts_dict en formato legacy
    fonts_dict = {
        'global': {'fallback': ['Courier New']},
        'app': {},
        'components': {'dialog': {}},
        'modules': {}
    }

    # Usar fuentes del primer dialog como base (todos tienen mismas fuentes)
    first_dialog = next(iter(dialogs_data.values()), {})
    fonts_config = first_dialog.get('fonts', {})

    fonts_dict['components']['dialog'] = {
        'title': fonts_config.get('title', {'family': 'Courier New', 'size': 20, 'weight': 'bold'}),
        'message': fonts_config.get('message', {'family': 'Courier New', 'size': 14, 'weight': 'bold'}),
        'button': fonts_config.get('button', {'family': 'Courier New', 'size': 14, 'weight': 'bold'}),
        'input': fonts_config.get('input', {'family': 'Courier New', 'size': 14, 'weight': 'normal'}),
    }

    # Construir geometry_dict
    window = first_dialog.get('window', {})
    spacing = first_dialog.get('spacing', {})
    geometry = {
        'width': window.get('width', FALLBACKS['geometry']['width']),
        'height': window.get('height', FALLBACKS['geometry']['height']),
        'border_width': window.get('border_width', FALLBACKS['geometry']['border_width']),
        'icon_size': window.get('icon_size', FALLBACKS['geometry']['icon_size']),
        'button_width': window.get('button_width', FALLBACKS['geometry']['button_width']),
        'button_height': window.get('button_height', FALLBACKS['geometry']['button_height']),
        'corner_radius': window.get('corner_radius', FALLBACKS['geometry']['corner_radius']),
        'wraplength': window.get('wraplength', FALLBACKS['geometry']['wraplength']),
        'focus_border_width': window.get('focus_border_width', FALLBACKS['geometry']['focus_border_width']),
        'entry_width': window.get('entry_width', FALLBACKS['geometry']['entry_width']),
        'entry_height': window.get('entry_height', FALLBACKS['geometry']['entry_height']),
        'button_width': window.get('button_width', FALLBACKS['geometry']['button_width']),
        'button_height': window.get('button_height', FALLBACKS['geometry']['button_height']),
        'title_bar_height': window.get('title_bar_height', FALLBACKS['geometry']['title_bar_height']),
        'padding_x': window.get('padding_x', FALLBACKS['geometry']['padding_x']),
        'padding_y': window.get('padding_y', FALLBACKS['geometry']['padding_y']),
        'spacing_icon_top': spacing.get('icon_top', 10),
        'spacing_icon_bottom': spacing.get('icon_bottom', 15),
        'spacing_title_bottom': spacing.get('title_bottom', 10),
        'spacing_message_bottom': spacing.get('message_bottom', 10),
        'spacing_entry_bottom': spacing.get('entry_bottom', 10),
    }

    return colors_dict, fonts_dict, geometry, FALLBACKS


def load_dialog_config():
    """Carga configuración de diálogos desde JSON con fallbacks centralizados.

    Prioridad:
    1. ui_dialogs.json (nuevo formato unificado)
    2. Fallback a colors_config.json + font_config.json + layout_config.json (legacy)
    3. Fallback a valores hardcodeados

    Implementa cache: los archivos JSON se leen una sola vez.
    Las siguientes llamadas devuelven el cache en memoria.

    Returns:
        tuple: (colors_dict, fonts_dict, geometry_dict, fallbacks_dict)
    """
    global _CONFIG_CACHE

    # Si ya tenemos cache, devolverlo directamente (no leer disco)
    if _CONFIG_CACHE is not None:
        return _CONFIG_CACHE

    # PASO 1: Intentar cargar desde ui_dialogs.json (nuevo formato)
    if _UI_LOADER_AVAILABLE and load_ui_dialogs is not None:
        try:
            ui_data = load_ui_dialogs()
            if ui_data and ui_data.get('dialogs'):
                _CONFIG_CACHE = _transform_ui_dialogs_to_legacy_format(ui_data)
                logging.info("Config cargada desde ui_dialogs.json")
                return _CONFIG_CACHE
        except Exception:
            logging.debug("No se pudo cargar ui_dialogs.json, usando legacy")

    # PASO 2: Fallback a los 3 JSONs separados (legacy)
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
