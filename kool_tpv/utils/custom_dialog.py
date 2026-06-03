"""
Custom Dialog helper - Wrapper de compatibilidad.

Este archivo mantiene compatibilidad con código existente.
La implementación real está en el paquete `dialogs/`.
"""

# Importar todo desde el nuevo paquete para mantener compatibilidad
from kool_tpv.utils.dialogs import (
    # Clases
    BaseDialog,
    MessageDialog as CustomDialog,
    InputDialog as CustomInputDialog,
    # Funciones helper
    show_success,
    show_error,
    show_warning,
    show_info,
    show_input_dialog,
    show_password_dialog,
    show_text_viewer,
    # Configuración
    load_dialog_config,
    FALLBACKS,
    # Utilidades
    create_dialog_content_container,
)

__all__ = [
    "BaseDialog",
    "CustomDialog",
    "CustomInputDialog",
    "show_success",
    "show_error",
    "show_warning",
    "show_info",
    "show_input_dialog",
    "show_password_dialog",
    "show_text_viewer",
    "load_dialog_config",
    "FALLBACKS",
    "create_dialog_content_container",
]
