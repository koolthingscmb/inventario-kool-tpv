from __future__ import annotations

import json
from pathlib import Path

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
        style_key: Optional[str] = None,
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

        # Si se proporciona style_key, obtener los parámetros resueltos
        # desde la lógica común; en caso contrario mantener comportamiento legacy.
        if style_key is not None:
            style_params = ButtonFactory._build_style_params(style_key)
            params.update(style_params)
        else:
            # Comportamiento legacy: respetar parámetros manuales
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

    @staticmethod
    def _build_style_params(style_key: str) -> dict:
        """Resolver y devolver un diccionario de parámetros de estilo a partir de `style_key`.

        Devuelve claves compatibles con `ctk.CTkButton.configure`, por ejemplo:
        `fg_color`, `hover_color`, `text_color`, `border_color`, `border_width`,
        `corner_radius`, `width`, `height`, `font`.
        """
        config_dir = Path(__file__).resolve().parents[2] / "config"
        styles_path = config_dir / "button_styles.json"
        tokens_path = config_dir / "design_tokens.json"

        try:
            with styles_path.open("r", encoding="utf-8") as f:
                button_styles = json.load(f)
        except FileNotFoundError:
            raise ValueError(f"No se encontró {styles_path}")
        except json.JSONDecodeError as exc:
            raise ValueError(f"Error decodificando {styles_path}: {exc}")

        try:
            with tokens_path.open("r", encoding="utf-8") as f:
                design_tokens = json.load(f)
        except FileNotFoundError:
            raise ValueError(f"No se encontró {tokens_path}")
        except json.JSONDecodeError as exc:
            raise ValueError(f"Error decodificando {tokens_path}: {exc}")

        if style_key not in button_styles:
            raise ValueError(f"style_key '{style_key}' no existe en {styles_path}")

        style = button_styles[style_key]

        # Esperamos que el estilo declare al menos los tokens habituales,
        # pero no forzamos la presencia de todos (compatibilidad con estilos simples).
        def resolve_token(token_name: Optional[str]) -> Optional[str]:
            if token_name is None:
                return None
            for cat_val in design_tokens.values():
                if isinstance(cat_val, dict) and token_name in cat_val:
                    return cat_val[token_name]
            raise ValueError(f"Token '{token_name}' no encontrado en {tokens_path}")

        params: dict = {}

        # Tokens de color (pueden faltar en estilos livianos)
        bg_val = resolve_token(style.get("bg_token")) if style.get("bg_token") is not None else None
        text_val = resolve_token(style.get("text_token")) if style.get("text_token") is not None else None
        border_val = resolve_token(style.get("border_token")) if style.get("border_token") is not None else None
        hover_val = resolve_token(style.get("hover_token")) if style.get("hover_token") is not None else None

        if bg_val is not None:
            params["fg_color"] = bg_val
        if text_val is not None:
            params["text_color"] = text_val
        if hover_val is not None:
            params["hover_color"] = hover_val
        if border_val is not None:
            params["border_color"] = border_val

        if "border_width" in style and style.get("border_width") is not None:
            params["border_width"] = style.get("border_width")
        if "corner_radius" in style and style.get("corner_radius") is not None:
            params["corner_radius"] = style.get("corner_radius")
        if "width" in style and style.get("width") is not None:
            params["width"] = style.get("width")
        if "height" in style and style.get("height") is not None:
            params["height"] = style.get("height")
        if "font_size" in style and style.get("font_size") is not None:
            params["font"] = ("Roboto-SemiBold", style.get("font_size"))

        return params

    @staticmethod
    def apply_style(widget: ctk.CTkButton, style_key: str) -> None:
        """Aplicar `style_key` a un botón existente (`widget`).

        - Resuelve los parámetros de estilo exactamente como `create_button` lo haría.
        - No modifica `text`, `master` ni `command`.
        - Lanza `ValueError` si `style_key` no existe o hay problemas de resolución.
        """
        if widget is None:
            raise ValueError("widget no puede ser None")

        style_params = ButtonFactory._build_style_params(style_key)

        # No incluir claves que no correspondan a configure()
        # (_build_style_params sólo devuelve claves válidas para configure)
        try:
            widget.configure(**style_params)
        except Exception as exc:
            raise RuntimeError(f"No se pudo aplicar style_key '{style_key}' al widget: {exc}")
