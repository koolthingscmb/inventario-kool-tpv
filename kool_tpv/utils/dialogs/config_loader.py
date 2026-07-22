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
    """Transforma el nuevo formato ui_dialogs.json al formato que espera BaseDialog.
    
    Implementa herencia: common -> dialogs[type]
    """
    dialogs_data = ui_data.get('dialogs', {})
    common = ui_data.get('common', {})
    
    # 1. Colores (normalmente específicos por tipo)
    colors_dict = {}
    for dialog_type, config in dialogs_data.items():
        colors_dict[dialog_type] = config.get('colors', {})

    # 2. Fuentes (heredan de common.fonts)
    fonts_by_type = {}
    common_fonts = common.get('fonts', {})
    for dialog_type, config in dialogs_data.items():
        type_fonts = config.get('fonts', {})
        fonts_by_type[dialog_type] = {
            'title': type_fonts.get('title') or common_fonts.get('title', {'family': 'Courier New', 'size': 18, 'weight': 'bold'}),
            'message': type_fonts.get('message') or common_fonts.get('message', {'family': 'Courier New', 'size': 14, 'weight': 'bold'}),
            'button': type_fonts.get('button') or common_fonts.get('button', {'family': 'Courier New', 'size': 14, 'weight': 'bold'}),
            'input': type_fonts.get('input') or common_fonts.get('input', {'family': 'Courier New', 'size': 14, 'weight': 'normal'}),
        }

    # 3. Geometría, Spacing y Buttons por tipo (heredan de common)
    geometry_by_type = {}
    spacing_by_type = {}
    buttons_by_type = {}
    
    common_win = common.get('window', {})
    common_spacing = common.get('spacing', {})
    common_buttons = common.get('buttons', {})

    for dialog_type, config in dialogs_data.items():
        w = config.get('window', {})
        s = config.get('spacing', {})
        b = config.get('buttons', {})
        
        geometry_by_type[dialog_type] = {
            'width': w.get('width') or common_win.get('width', FALLBACKS['geometry']['width']),
            'height': w.get('height') or common_win.get('height', FALLBACKS['geometry']['height']),
            'border_width': w.get('border_width') or common_win.get('border_width', FALLBACKS['geometry']['border_width']),
            'corner_radius': w.get('corner_radius') or common_win.get('corner_radius', FALLBACKS['geometry']['corner_radius']),
            'icon_size': w.get('icon_size') or common_win.get('icon_size', FALLBACKS['geometry']['icon_size']),
            'title_bar_height': w.get('title_bar_height') or common_win.get('title_bar_height', FALLBACKS['geometry']['title_bar_height']),
            'padding_x': w.get('padding_x') or common_win.get('padding_x', FALLBACKS['geometry']['padding_x']),
            'padding_y': w.get('padding_y') or common_win.get('padding_y', FALLBACKS['geometry']['padding_y']),
            'entry_width': w.get('entry_width') or common_win.get('entry_width', FALLBACKS['geometry']['entry_width']),
            'entry_height': w.get('entry_height') or common_win.get('entry_height', FALLBACKS['geometry']['entry_height']),
            'wraplength': w.get('wraplength') or common_win.get('wraplength', FALLBACKS['geometry']['wraplength']),
            'focus_border_width': w.get('focus_border_width') or common_win.get('focus_border_width', FALLBACKS['geometry']['focus_border_width']),
        }
        
        spacing_by_type[dialog_type] = {
            'icon_top': s.get('icon_top') or common_spacing.get('icon_top', 10),
            'icon_bottom': s.get('icon_bottom') or common_spacing.get('icon_bottom', 15),
            'title_bottom': s.get('title_bottom') or common_spacing.get('title_bottom', 10),
            'message_bottom': s.get('message_bottom') or common_spacing.get('message_bottom', 10),
            'entry_bottom': s.get('entry_bottom') or common_spacing.get('entry_bottom', 10),
        }

        buttons_by_type[dialog_type] = {
            'accept': {**common_buttons.get('accept', {}), **b.get('accept', {})},
            'cancel': {**common_buttons.get('cancel', {}), **b.get('cancel', {})},
        }

    # Mantener geometry legacy (primer tipo) para compatibilidad
    geometry_legacy = geometry_by_type.get('info', geometry_by_type[next(iter(geometry_by_type))]) if geometry_by_type else FALLBACKS['geometry']

    return colors_dict, fonts_by_type, geometry_legacy, FALLBACKS, geometry_by_type, spacing_by_type, buttons_by_type


def load_dialog_config():
    """Carga configuración de diálogos desde JSON con fallbacks centralizados.

    Prioridad:
    1. ui_dialogs.json (nuevo formato unificado)
    2. Fallback a colors_config.json + font_config.json + layout_config.json (legacy)
    3. Fallback a valores hardcodeados

    Implementa cache: los archivos JSON se leen una sola vez.
    Las siguientes llamadas devuelven el cache en memoria.

    Returns:
        tuple: (colors, fonts_by_type, geometry_legacy, fallbacks, geometry_by_type, spacing_by_type, buttons_by_type)
    """
    global _CONFIG_CACHE

    # Si ya tenemos cache, devolverlo directamente (no leer disco)
    if _CONFIG_CACHE is not None:
        return _CONFIG_CACHE

    return reload_dialog_config()


def reload_dialog_config(ui_data: dict = None):
    """Fuerza la recarga de la configuración, opcionalmente usando datos proporcionados.
    
    Args:
        ui_data (dict, optional): Si se proporciona, usa estos datos en lugar de leer de disco.
    """
    global _CONFIG_CACHE
    
    if ui_data:
        _CONFIG_CACHE = _transform_ui_dialogs_to_legacy_format(ui_data)
        logging.info("Config de diálogos actualizada desde datos manuales (cache)")
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
        _CONFIG_CACHE = (dialogs_colors, fonts_data, geometry, FALLBACKS, {}, {}, {})
        return _CONFIG_CACHE

    except Exception as e:
        logging.exception("Error cargando configuración de diálogos, usando fallbacks")
        # En caso de error, cachear fallbacks para no reintentar
        _CONFIG_CACHE = ({}, {}, {}, FALLBACKS, {}, {}, {})
        return _CONFIG_CACHE
