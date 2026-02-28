"""Gestor singleton para controlar dialogs activos (throttling)."""
import logging


class DialogManager:
    """Singleton que previene múltiples dialogs simultáneos."""

    _instance = None
    _active_dialog = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def can_show(cls) -> bool:
        """Verifica si se puede mostrar un nuevo dialog."""
        return cls._active_dialog is None

    @classmethod
    def register(cls, dialog):
        """Registra un dialog como activo."""
        if cls._active_dialog is not None:
            logging.warning(f'Intento de abrir dialog mientras hay uno activo: {cls._active_dialog}')
            return False

        cls._active_dialog = dialog
        logging.debug(f'Dialog registrado: {dialog}')
        return True

    @classmethod
    def unregister(cls):
        """Libera el dialog activo."""
        if cls._active_dialog is not None:
            logging.debug(f'Dialog liberado: {cls._active_dialog}')
            cls._active_dialog = None

    @classmethod
    def reset(cls):
        """Emergency reset (para testing o recovery)."""
        logging.warning('DialogManager reset forzado')
        cls._active_dialog = None
