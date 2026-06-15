"""
Paquete de diálogos modales para Kool TPV.

Exporta todas las clases y funciones helper para uso externo.
"""

# Clases
from .base_dialog import BaseDialog
from .message_dialog import MessageDialog
from .input_dialog import InputDialog

# Funciones helper
from .helpers import (
    show_error,
    show_warning,
    show_info,
    show_input_dialog,
    show_password_dialog,
    show_text_viewer,
)

# Configuración
from .config_loader import load_dialog_config, FALLBACKS

# Utilidades
from .content_container import create_dialog_content_container

__all__ = [
    # Clases
    'BaseDialog',
    'MessageDialog',
    'InputDialog',
    # Helpers
    'show_error',
    'show_warning',
    'show_info',
    'show_input_dialog',
    'show_password_dialog',
    'show_text_viewer',
    # Config
    'load_dialog_config',
    'FALLBACKS',
    # Utilidades
    'create_dialog_content_container',
]
