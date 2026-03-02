"""
TpvLayoutBase - Layout base de 3 zonas para el TPV

Estructura:
┌─────────┬──────────────┬─────────────┐
│ Sidebar │    Centro    │   Derecha   │
│  (220)  │ (expandible) │   (420)     │
└─────────┴──────────────┴─────────────┘

Métodos públicos:
- set_sidebar_content(widget)
- set_center_content(widget)
- set_right_content(widget)
"""
import logging
import customtkinter as ctk
from typing import Optional

logger = logging.getLogger(__name__)


class TpvLayoutBase(ctk.CTkFrame):
    """Layout base de 3 zonas para TPV."""

    def __init__(
        self,
        parent,
        sidebar_width: int = 220,
        right_width: int = 420,
        **kwargs
    ):
        """
        Args:
            parent: Widget padre
            sidebar_width: Ancho del sidebar izquierdo (default 220)
            right_width: Ancho de la zona derecha (default 420)
        """
        super().__init__(parent, **kwargs)

        # Guardar dimensiones
        self.sidebar_width = sidebar_width
        self.right_width = right_width

        # Crear contenedor principal
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True)

        # Zona 1: Sidebar (izquierda, ancho fijo)
        self.sidebar_frame = ctk.CTkFrame(
            self.main_container,
            width=sidebar_width,
            fg_color="transparent"
        )
        self.sidebar_frame.pack(side="left", fill="y")
        self.sidebar_frame.pack_propagate(False)

        # Zona 2: Centro (expandible)
        self.center_frame = ctk.CTkFrame(
            self.main_container,
            fg_color="transparent"
        )
        self.center_frame.pack(side="left", fill="both", expand=True)

        # Zona 3: Derecha (ancho fijo)
        self.right_frame = ctk.CTkFrame(
            self.main_container,
            width=right_width,
            fg_color="transparent"
        )
        self.right_frame.pack(side="right", fill="y")
        self.right_frame.pack_propagate(False)

        # Referencias a contenidos actuales
        self.sidebar_content: Optional[ctk.CTkBaseClass] = None
        self.center_content: Optional[ctk.CTkBaseClass] = None
        self.right_content: Optional[ctk.CTkBaseClass] = None

        logger.info("TpvLayoutBase inicializado")

    def set_sidebar_content(self, widget: Optional[ctk.CTkBaseClass]) -> None:
        """Cambiar contenido del sidebar.

        Args:
            widget: Widget a mostrar en sidebar (None para vaciar)
        """
        try:
            # Limpiar contenido anterior
            self._clear_frame(self.sidebar_frame)

            if widget is not None:
                # Validar parent
                try:
                    if getattr(widget, 'master', None) != self.sidebar_frame:
                        logger.warning(
                            f"Widget parent incorrecto. Debería ser sidebar_frame pero es {getattr(widget, 'master', None)}. "
                            f"Crear widget con layout.get_sidebar_frame() como parent."
                        )
                except Exception:
                    pass

                widget.pack(fill="both", expand=True)
                self.sidebar_content = widget
            else:
                self.sidebar_content = None

            logger.debug("Sidebar content actualizado")

        except Exception:
            logger.exception("Error actualizando sidebar content")

    def set_center_content(self, widget: Optional[ctk.CTkBaseClass]) -> None:
        """Cambiar contenido del centro.

        Args:
            widget: Widget a mostrar en centro (None para vaciar)
        """
        try:
            # Limpiar contenido anterior
            self._clear_frame(self.center_frame)

            if widget is not None:
                # Validar parent
                try:
                    if getattr(widget, 'master', None) != self.center_frame:
                        logger.warning(
                            f"Widget parent incorrecto. Debería ser center_frame pero es {getattr(widget, 'master', None)}. "
                            f"Crear widget con layout.get_center_frame() como parent."
                        )
                except Exception:
                    pass

                widget.pack(fill="both", expand=True)
                self.center_content = widget
            else:
                self.center_content = None

            logger.debug("Center content actualizado")

        except Exception:
            logger.exception("Error actualizando center content")

    def set_right_content(self, widget: Optional[ctk.CTkBaseClass]) -> None:
        """Cambiar contenido de la zona derecha.

        Args:
            widget: Widget a mostrar a la derecha (None para vaciar)
        """
        try:
            # Limpiar contenido anterior
            self._clear_frame(self.right_frame)

            if widget is not None:
                # Validar parent
                try:
                    if getattr(widget, 'master', None) != self.right_frame:
                        logger.warning(
                            f"Widget parent incorrecto. Debería ser right_frame pero es {getattr(widget, 'master', None)}. "
                            f"Crear widget con layout.get_right_frame() como parent."
                        )
                except Exception:
                    pass

                widget.pack(fill="both", expand=True)
                self.right_content = widget
            else:
                self.right_content = None

            logger.debug("Right content actualizado")

        except Exception:
            logger.exception("Error actualizando right content")

    def _clear_frame(self, frame: ctk.CTkFrame) -> None:
        """Limpiar todos los widgets de un frame.

        Args:
            frame: Frame a limpiar
        """
        try:
            for widget in frame.winfo_children():
                try:
                    widget.pack_forget()
                    widget.destroy()
                except Exception:
                    pass
        except Exception:
            logger.exception("Error limpiando frame")

    def get_sidebar_frame(self) -> ctk.CTkFrame:
        """Obtener referencia al frame del sidebar."""
        return self.sidebar_frame

    def get_center_frame(self) -> ctk.CTkFrame:
        """Obtener referencia al frame del centro."""
        return self.center_frame

    def get_right_frame(self) -> ctk.CTkFrame:
        """Obtener referencia al frame derecho."""
        return self.right_frame
