"""KeyboardManager - Gestor global de navegación con teclado.

Responsabilidades:

    Capturar flechas Up/Down globalmente
    Delegar a la lista navegable activa
    Ignorar cuando usuario escribe en Entry/Text
    Evitar conflictos entre múltiples listas

Uso:
    # En main.py o App.init
    keyboard_mgr = KeyboardManager(root_window)

    # En cada NavList (se registra automáticamente al hacer click)
    nav_list = NavList(parent, keyboard_manager=keyboard_mgr)

"""
import logging
from typing import Optional, Protocol
import tkinter as tk

logger = logging.getLogger(__name__)


class Navigable(Protocol):
    """Protocolo que deben implementar widgets navegables."""

    def select_next(self) -> bool:
        """Seleccionar siguiente item. Returns True si hubo movimiento."""
        ...

    def select_previous(self) -> bool:
        """Seleccionar item anterior. Returns True si hubo movimiento."""
        ...


class KeyboardManager:
    """Gestor global de navegación con teclado.

    Nota: este componente no tiene UI; solo registra handlers globales en
    el `root_widget` provisto y delega a la lista navegable activa.
    """

    def __init__(self, root_widget: tk.Misc):
        """Inicializar gestor.

        Args:
            root_widget: Widget raíz (Tk o Toplevel) donde hacer bind_all
        """
        self.root = root_widget
        self.active_list: Optional[Navigable] = None

        # Bind global de flechas
        try:
            self.root.bind_all('<Up>', self._on_arrow_up, add='+')
            self.root.bind_all('<Down>', self._on_arrow_down, add='+')
            logger.info('KeyboardManager inicializado - flechas capturadas globalmente')
        except Exception:
            logger.exception('Error inicializando KeyboardManager')

    def set_active_list(self, navigable: Optional[Navigable]):
        """Establecer lista navegable activa.

        Args:
            navigable: Widget que implementa Navigable o None para desactivar
        """
        try:
            if navigable != self.active_list:
                self.active_list = navigable
                logger.debug(f'Lista activa cambiada: {type(navigable).__name__ if navigable else "None"}')
        except Exception:
            logger.exception('Error cambiando lista activa')

    def clear_active_list(self):
        """Desactivar lista activa."""
        self.active_list = None

    def _should_ignore_key(self) -> bool:
        """Determinar si el evento debe ignorarse.

        Returns:
            True si usuario está escribiendo en Entry/Text/ComboBox
        """
        try:
            focused = self.root.focus_get()

            if focused is None:
                return False

            # Ignorar si foco en widgets de entrada de texto
            widget_class = focused.__class__.__name__.lower()

            ignore_widgets = [
                'entry', 'text', 'textbox',
                'ctkentry', 'ctktextbox',
                'spinbox', 'combobox'
            ]

            for ignore in ignore_widgets:
                if ignore in widget_class:
                    return True

            return False

        except Exception:
            logger.exception('Error verificando foco')
            return False

    def _on_arrow_down(self, event: tk.Event):
        """Manejar flecha abajo global."""
        try:
            # Ignorar si usuario está escribiendo
            if self._should_ignore_key():
                return

            # Delegar a lista activa si existe
            if self.active_list and hasattr(self.active_list, 'select_next'):
                try:
                    moved = self.active_list.select_next()
                    if moved:
                        return 'break'  # Evitar propagación
                except Exception:
                    logger.exception('Error delegando Down a lista activa')

        except Exception:
            logger.exception('Error manejando flecha abajo')

    def _on_arrow_up(self, event: tk.Event):
        """Manejar flecha arriba global."""
        try:
            # Ignorar si usuario está escribiendo
            if self._should_ignore_key():
                return

            # Delegar a lista activa si existe
            if self.active_list and hasattr(self.active_list, 'select_previous'):
                try:
                    moved = self.active_list.select_previous()
                    if moved:
                        return 'break'  # Evitar propagación
                except Exception:
                    logger.exception('Error delegando Up a lista activa')

        except Exception:
            logger.exception('Error manejando flecha arriba')

    def destroy(self):
        """Limpiar bindings (llamar al cerrar aplicación)."""
        try:
            self.root.unbind_all('<Up>')
            self.root.unbind_all('<Down>')
            self.active_list = None
            logger.info('KeyboardManager destruido')
        except Exception:
            logger.exception('Error destruyendo KeyboardManager')
