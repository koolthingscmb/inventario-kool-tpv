from __future__ import annotations

import customtkinter as ctk
from typing import Optional, Any


class ButtonFactory:
    """Factory para crear botones `CTkButton` con parámetros limpios y predecibles.

    El método `create_button` sólo prepara los argumentos y devuelve el widget;
    no realiza lecturas de archivos ni lógica de negocio.
    """

    @staticmethod
    def create_button(
        parent,
        text: str,
        command: Optional[Any] = None,
        *,
        width: Optional[int] = None,
        height: Optional[int] = None,
        color: Optional[str] = None,
        hover_color: Optional[str] = None,
        text_color: Optional[str] = None,
        font: Optional[Any] = None,
        corner_radius: Optional[int] = 12,
        border_color: Optional[str] = None,
        border_width: Optional[int] = None,
        **kwargs,
    ) -> ctk.CTkButton:
        """Crear y devolver un `ctk.CTkButton`.

        - No añade `width`/`height` al diccionario si son `None` (dejar que CTk use su comportamiento por defecto).
        - Convierte `text` a mayúsculas.
        - Acepta `**kwargs` para pasar parámetros adicionales si se desea.
        """

        params = {
            "master": parent,
            "text": (text or "").upper(),
            "command": command,
        }

        if color is not None:
            params["fg_color"] = color
        if hover_color is not None:
            params["hover_color"] = hover_color
        if text_color is not None:
            params["text_color"] = text_color
        if font is not None:
            params["font"] = font
        if corner_radius is not None:
            params["corner_radius"] = corner_radius
        if border_color is not None:
            params["border_color"] = border_color
        if border_width is not None:
            params["border_width"] = border_width

        # Añadir width/height sólo si se pasan explícitamente
        if width is not None:
            params["width"] = width
        if height is not None:
            params["height"] = height

        # Permitir extensibilidad a través de kwargs (por ejemplo cursor, anchor, etc.)
        params.update(kwargs)

        return ctk.CTkButton(**params)
