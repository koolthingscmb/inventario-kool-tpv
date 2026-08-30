"""Configuración global para widgets de notificación (Toast, Banner, etc.)."""
import json
import logging
from kool_tpv.paths import get_resource_path

_CONFIG_PATH = get_resource_path("kool_tpv", "config", "notificaciones_config.json")

_DEFAULTS = {
    'toast_posicion': 'bottom-right',
    'toast_duracion_ms': 3000,
    'toast_ancho': 320,
    'toast_padding_x': 16,
    'toast_padding_y': 12,
    'toast_corner_radius': 8,
    'toast_offset_x': 16,
    'toast_offset_y': 16,
    'toast_success_bg': '#2D7D46',
    'toast_info_bg': '#1F6AA5',
    'toast_warning_bg': '#B8870B',
    'toast_error_bg': '#C0392B',
    'toast_text_color': '#FFFFFF',
    'toast_animar_aparicion': True,
    'toast_animar_desaparicion': True,
    'toast_fade_step_ms': 20,
    'toast_max_opacity': 0.95,
    'toast_icono_size': 40,
    'toast_icono_padding': 8,
    'toast_icono_success': 'dialog_success.png',
    'toast_icono_info': 'dialog_info.png',
    'toast_icono_warning': 'dialog_warning.png',
    'toast_icono_error': 'dialog_error.png',
}


def load_notificaciones_config() -> dict:
    """Lee notificaciones_config.json y aplica fallback a valores por defecto."""
    cfg = dict(_DEFAULTS)
    try:
        data = json.loads(_CONFIG_PATH.read_text(encoding='utf-8'))
        cfg.update(data)
    except Exception:
        logging.warning('notificaciones_config.json no encontrado o inválido, usando defaults')
    return cfg
