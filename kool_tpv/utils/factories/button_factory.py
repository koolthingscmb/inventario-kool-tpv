from __future__ import annotations

import json
import logging
from pathlib import Path

import customtkinter as ctk
from typing import Optional, Any

from kool_tpv.paths import get_resource_path

logger = logging.getLogger(__name__)


class ButtonFactory:
    """Factory para crear botones `CTkButton` con parámetros limpios y predecibles.
    
    Los JSONs de configuración (button_styles, design_tokens, colors_config)
    se cargan una sola vez en memoria (caché de clase) y se reutilizan en
    todas las llamadas. Usar `reload_configs()` para invalidar el caché.
    """

    _config_dir: Path = get_resource_path("kool_tpv", "config")
    _button_styles: dict | None = None
    _design_tokens: dict | None = None
    _colors_config: dict | None = None

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
        module: Optional[str] = None,
        palette_key: str = "primary",
        **kwargs,
    ) -> ctk.CTkButton:
        """Crear y devolver un `ctk.CTkButton`.

        - No añade `width`/`height` al diccionario si son `None` (dejar que CTk use su comportamiento por defecto).
        - Convierte `text` a mayúsculas.
        - Acepta `**kwargs` para pasar parámetros adicionales si se desea.
        - Si se pasa ``module``, los colores base se resuelven desde
          ``colors_config.json[module]["buttons"][palette_key]`` en lugar de
          los tokens globales.  ``palette_key`` por defecto es ``"primary"``.
        """

        params = {
            "master": parent,
            "text": (text or "").upper(),
            "command": command,
        }

        # Si se proporciona style_key, obtener los parámetros resueltos
        # desde la lógica común; en caso contrario mantener comportamiento legacy.
        if style_key is not None:
            style_params = ButtonFactory._resolve_style(style_key, module=module, palette_key=palette_key)
            params.update(style_params)

        # Parámetros manuales (actúan como overrides si hay style_key, 
        # o como configuración base si no lo hay).
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

    # ──────────────────────────────────────────────────────────────
    #  Caché de configuración
    # ──────────────────────────────────────────────────────────────

    @classmethod
    def _ensure_configs_loaded(cls) -> None:
        """Cargar los 3 JSONs desde disco si aún no están en caché."""
        if cls._button_styles is None:
            cls._button_styles = cls._load_json("button_styles.json")
            logger.debug("button_styles.json cargado en caché (%d estilos)", len(cls._button_styles))
        if cls._design_tokens is None:
            cls._design_tokens = cls._load_json("design_tokens.json")
            logger.debug("design_tokens.json cargado en caché")
        if cls._colors_config is None:
            cls._colors_config = cls._load_json("colors_config.json")
            logger.debug("colors_config.json cargado en caché")

    @classmethod
    def _load_json(cls, filename: str) -> dict:
        """Cargar un JSON desde el directorio de configuración."""
        path = cls._config_dir / filename
        try:
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            raise ValueError(f"No se encontró {path}")
        except json.JSONDecodeError as exc:
            raise ValueError(f"Error decodificando {path}: {exc}")

    @classmethod
    def reload_configs(cls) -> None:
        """Invalidar el caché y forzar la próxima lectura desde disco.

        Llamar tras editar cualquier JSON de configuración en caliente.
        """
        cls._button_styles = None
        cls._design_tokens = None
        cls._colors_config = None
        logger.debug("Caché de ButtonFactory invalidado")

    @classmethod
    def get_module_colors(cls, module: str) -> dict:
        """Devolver el bloque completo de colores de un módulo desde colors_config.json."""
        cls._ensure_configs_loaded()
        module_cfg = cls._colors_config.get(module, {})
        if not module_cfg:
            logger.warning("Módulo '%s' no encontrado en colors_config.json", module)
        return module_cfg

    # ──────────────────────────────────────────────────────────────
    #  Resolución de estilos
    # ──────────────────────────────────────────────────────────────

    @classmethod
    def _get_module_palette(cls, module: str, palette_key: str) -> dict:
        """Obtener la paleta de botones de un módulo desde ``colors_config.json``.

        Args:
            module: Nombre del módulo (ej. ``"produccion"``, ``"almacen"``).
            palette_key: Clave dentro de ``buttons`` (ej. ``"primary"``, ``"secondary"``).

        Returns:
            Dict con claves ``bg``, ``hover``, ``text``, ``border`` (hex strings),
            o dict vacío si no se encuentra.
        """
        cls._ensure_configs_loaded()
        module_cfg = cls._colors_config.get(module, {})
        palette = module_cfg.get("buttons", {}).get(palette_key, {})
        if not palette:
            logger.warning(
                "No se encontró paleta '%s' para módulo '%s' en colors_config.json",
                palette_key, module,
            )
        return palette

    @classmethod
    def _resolve_style(
        cls,
        style_key: str,
        *,
        module: Optional[str] = None,
        palette_key: str = "primary",
    ) -> dict:
        """Resolver un ``style_key`` a parámetros concretos para ``CTkButton``.

        Pipeline unificado:
        1. Lee ``button_styles[style_key]`` desde el caché.
        2. Resuelve los tokens de color contra ``design_tokens.json``.
        3. Si ``module`` es distinto de None, sobrescribe los colores con
           la paleta del módulo desde ``colors_config.json``.
        4. Extrae parámetros geométricos (width, height, corner_radius,
           border_width, font_size).

        Devuelve claves compatibles con ``ctk.CTkButton.configure``:
        ``fg_color``, ``hover_color``, ``text_color``, ``border_color``,
        ``border_width``, ``corner_radius``, ``width``, ``height``, ``font``.
        """
        cls._ensure_configs_loaded()

        button_styles = cls._button_styles
        design_tokens = cls._design_tokens
        styles_path = cls._config_dir / "button_styles.json"
        tokens_path = cls._config_dir / "design_tokens.json"

        if style_key not in button_styles:
            raise ValueError(f"style_key '{style_key}' no existe en {styles_path}")

        style = button_styles[style_key]
        style_type = style.get("type", "outline")

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

        # ── Override con paleta del módulo ──────────────────────────
        if module is not None:
            palette = cls._get_module_palette(module, palette_key)
            if palette:
                if style_type == "outline":
                    # outline: text/border/hover del módulo.
                    # También permitimos bg si el módulo lo define explícitamente.
                    bg_val = palette.get("bg", bg_val)
                    text_val = palette.get("text", text_val)
                    border_val = palette.get("border", border_val)
                    hover_val = palette.get("hover", hover_val)
                else:
                    # solid: todos los colores del módulo
                    bg_val = palette.get("bg", bg_val)
                    text_val = palette.get("text", text_val)
                    hover_val = palette.get("hover", hover_val)
                    border_val = palette.get("border", border_val)

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

        # Respect both explicit "width" and legacy "min_width" from JSON styles.
        # Prefer explicit "width" when present; fall back to "min_width".
        width_val = None
        if "width" in style and style.get("width") is not None:
            width_val = style.get("width")
        elif "min_width" in style and style.get("min_width") is not None:
            width_val = style.get("min_width")
        if width_val is not None:
            params["width"] = width_val

        # Height: prefer explicit "height"; fall back to "min_height" if present.
        height_val = None
        if "height" in style and style.get("height") is not None:
            height_val = style.get("height")
        elif "min_height" in style and style.get("min_height") is not None:
            height_val = style.get("min_height")
        if height_val is not None:
            params["height"] = height_val
        if "font_size" in style and style.get("font_size") is not None:
            params["font"] = ("Roboto-SemiBold", style.get("font_size"))

        return params

    @classmethod
    def apply_style(
        cls,
        widget: ctk.CTkButton,
        style_key: str,
        *,
        module: Optional[str] = None,
        palette_key: str = "primary",
    ) -> None:
        """Aplicar `style_key` a un botón existente (`widget`).

        - Resuelve los parámetros de estilo exactamente como `create_button` lo haría.
        - No modifica `text`, `master` ni `command`.
        - Lanza `ValueError` si `style_key` no existe o hay problemas de resolución.
        - Si ``module`` es distinto de None, sobrescribe colores con la paleta del módulo.
        """
        if widget is None:
            raise ValueError("widget no puede ser None")

        style_params = cls._resolve_style(style_key, module=module, palette_key=palette_key)

        # _resolve_style sólo devuelve claves válidas para configure()
        try:
            widget.configure(**style_params)
        except Exception as exc:
            raise RuntimeError(f"No se pudo aplicar style_key '{style_key}' al widget: {exc}")
