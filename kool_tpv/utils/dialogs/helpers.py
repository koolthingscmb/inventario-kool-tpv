"""
Funciones helper para mostrar diálogos de forma sencilla.
"""
import logging

from .message_dialog import MessageDialog
from .input_dialog import InputDialog


def show_success(parent, titulo, mensaje, callback=None):
    """Mostrar diálogo de éxito.

    Siempre devuelve True (el usuario confirmó haber visto el mensaje).
    """
    dlg = MessageDialog(parent, tipo='success', titulo=titulo, mensaje=mensaje, callback=callback)
    try:
        dlg.wait_window()
    except Exception:
        pass
    return True


def show_error(parent, titulo, mensaje, callback=None, confirm=False):
    """Mostrar diálogo de error.

    Si confirm=True, muestra botones 'Cancelar' y 'Aceptar' y devuelve True/False.
    Útil para: "Error al guardar, ¿Reintentar?"
    """
    dlg = MessageDialog(parent, tipo='error', titulo=titulo, mensaje=mensaje,
                        callback=callback, confirm=confirm)
    try:
        dlg.wait_window()
    except Exception:
        pass
    return getattr(dlg, 'result', False)


def show_warning(parent, titulo, mensaje, callback=None, confirm=False):
    """Mostrar diálogo de advertencia.

    Si confirm=True, muestra botones 'Cancelar' y 'Aceptar' y devuelve True/False.
    """
    dlg = MessageDialog(parent, tipo='warning', titulo=titulo, mensaje=mensaje,
                        callback=callback, confirm=confirm)
    try:
        dlg.wait_window()
    except Exception:
        pass
    return getattr(dlg, 'result', False)


def show_info(parent, titulo, mensaje, callback=None, confirm=False):
    """Mostrar diálogo de información."""
    dlg = MessageDialog(parent, tipo='info', titulo=titulo, mensaje=mensaje, callback=callback, confirm=confirm)
    try:
        dlg.wait_window()
    except Exception:
        pass
    return getattr(dlg, 'result', False if confirm else True)


def show_input_dialog(parent, titulo, mensaje, tipo='success', valor_defecto='', callback=None, password=False, window_title=None):
    """Mostrar diálogo de entrada y devolver valor ingresado o None si canceló.

    Args:
        password: si True, el campo será enmascarado (show='*').
    """
    dialog = InputDialog(parent, tipo=tipo, titulo=titulo, mensaje=mensaje,
                         valor_defecto=valor_defecto, callback=callback,
                         password=password, window_title=window_title)
    return dialog.get_input()


def show_password_dialog(parent, titulo="Contraseña", mensaje="Introduce tu contraseña:"):
    """Mostrar diálogo de input enmascarado para password.

    Returns:
        str o None: Password ingresado o None si canceló
    """
    # En dialogs de password mostramos título en la barra de ventana,
    # pero no como título grande dentro del contenido.
    return show_input_dialog(parent, titulo="", mensaje=mensaje, tipo="password",
                             password=True, window_title=titulo)


def show_text_viewer(parent, titulo, texto, width=600, height=800, callback=None):
    """Helper que muestra TextViewDialog del módulo `textview_dialog`.

    Esto mantiene compatibilidad con llamadas previas a `show_text_viewer`
    importando desde `kool_tpv.utils.custom_dialog`.
    """
    try:
        from kool_tpv.utils.textview_dialog import show_text_viewer as _show
        _show(parent, titulo, texto, width=width, height=height, callback=callback)
    except Exception:
        logging.exception('Error delegando a textview_dialog.show_text_viewer')


def show_cierre_config_dialog(parent, defaults=None, callback=None):
    """Mostrar diálogo de configuración de cierre.

    Args:
        parent: Widget padre
        defaults: Dict con valores por defecto para los checkboxes
        callback: Función a llamar con el resultado

    Returns:
        Dict con las secciones seleccionadas o None si canceló
    """
    from .cierre_config_dialog import CierreConfigDialog
    dialog = CierreConfigDialog(parent, callback=callback, defaults=defaults)
    return dialog.get_config()
