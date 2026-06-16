from .toast_widget import ToastWidget, ToastType

__all__ = ['ToastWidget', 'ToastType', 'show_success', 'show_info', 'show_warning', 'show_error']


def show_success(parent, mensaje: str, duracion_ms: int = None):
    """Mostrar toast de éxito."""
    return ToastWidget.show(parent, mensaje, tipo='success', duracion_ms=duracion_ms)


def show_info(parent, mensaje: str, duracion_ms: int = None):
    """Mostrar toast informativo."""
    return ToastWidget.show(parent, mensaje, tipo='info', duracion_ms=duracion_ms)


def show_warning(parent, mensaje: str, duracion_ms: int = None):
    """Mostrar toast de advertencia (warning).

    Reemplaza show_warning() de custom_dialog para mensajes informativos
    que no requieren confirmación del usuario.
    """
    return ToastWidget.show(parent, mensaje, tipo='warning', duracion_ms=duracion_ms)


def show_error(parent, mensaje: str, duracion_ms: int = None):
    """Mostrar toast de error."""
    return ToastWidget.show(parent, mensaje, tipo='error', duracion_ms=duracion_ms)
