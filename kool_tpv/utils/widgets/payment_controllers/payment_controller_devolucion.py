"""
PaymentControllerDevolucion - Widget visual para modo devolución activo.
Muestra el indicador MODO DEVOLUCIÓN en el payment_area del TicketCarrito.
"""
import logging
from pathlib import Path
import json
import customtkinter as ctk
from typing import Optional, Callable

logger = logging.getLogger(__name__)


def load_config(config_name: str) -> dict:
    try:
        base = Path(__file__).resolve().parents[3]
        config_path = base / "config" / config_name
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        logger.exception(f"Error cargando {config_name}")
        return {}


def _norm_color(val: str) -> str:
    try:
        if not val:
            return ''
        if not isinstance(val, str):
            return val
        s = val.strip()
        if not s:
            return ''
        if s.lower() in ("transparent", "none"):
            return s.lower()
        return '#' + s.lstrip('#')
    except Exception:
        return val


def _resolve_token(tokens: dict, token: str, fallback: str) -> str:
    """Busca un token de color en el dict anidado de design_tokens."""
    for section in tokens.values():
        if isinstance(section, dict) and token in section:
            return _norm_color(section[token])
    return fallback


class PaymentControllerDevolucion(ctk.CTkFrame):
    """Indicador visual de modo devolución activo + botones de finalización."""

    def __init__(
        self,
        parent,
        total: float = 0.0,
        on_finalizar: Optional[Callable] = None,
        **kwargs
    ):
        self.colors     = load_config("colors_config.json")
        self.fonts      = load_config("font_config.json")
        self.layout     = load_config("layout_config.json")
        self.tokens     = load_config("design_tokens.json")
        self.btn_styles = load_config("button_styles.json")

        # --- Colores banner "MODO DEVOLUCIÓN" ---
        style = self.btn_styles.get("tpv_danger", {})
        self._color_danger = _resolve_token(self.tokens, style.get("bg_token",   "red_danger"), "#FF0000")
        self._color_text   = _resolve_token(self.tokens, style.get("text_token", "white_base"), "#FFFFFF")

        # --- Colores botones de acción ---
        pc_colors = self.colors.get("tpv", {}).get("payment_controllers", {})
        _ef  = pc_colors.get("efectivo", {}).get("button", {})
        _tar = pc_colors.get("tarjeta",  {}).get("button", {})

        self._btn_efectivo = {
            "bg":     _norm_color(_ef.get("bg",     "#000000")),
            "hover":  _norm_color(_ef.get("hover",  "#197307")),
            "text":   _norm_color(_ef.get("text",   "#2cff00")),
            "border": _norm_color(_ef.get("border", "#2cff00")),
        }
        self._btn_tarjeta = {
            "bg":     _norm_color(_tar.get("bg",     "#000000")),
            "hover":  _norm_color(_tar.get("hover",  "#2A7D58")),
            "text":   _norm_color(_tar.get("text",   "#53ffb1")),
            "border": _norm_color(_tar.get("border", "#53ffb1")),
        }
        self._btn_cambio = {
            "bg":     "#000000",
            "hover":  _resolve_token(self.tokens, "orange_hover",  "#e67e22"),
            "text":   _resolve_token(self.tokens, "orange_config", "#FF9800"),
            "border": _resolve_token(self.tokens, "orange_config", "#FF9800"),
        }

        # --- Frame ---
        pc_layout = self.layout.get("modules", {}).get("tpv", {}).get("ticket_carrito", {}).get("payment_controllers", {})
        footer_bg = self.colors.get("tpv", {}).get("ticket_carrito", {}).get("footer", {}).get("bg", "#1a1a1a")

        super().__init__(
            parent,
            fg_color=_norm_color(footer_bg),
            border_width=pc_layout.get("border_width", 5),
            border_color=self._color_danger,
            corner_radius=pc_layout.get("corner_radius", 18),
            **kwargs
        )

        self.total = total
        self.on_finalizar_callback = on_finalizar

        self._create_widgets()
        logger.info("PaymentControllerDevolucion inicializado")

    def _create_widgets(self):
        fonts_cfg  = self.fonts.get("modules", {}).get("tpv", {}).get("payment_controllers", {})
        layout_cfg = self.layout.get("modules", {}).get("tpv", {}).get("ticket_carrito", {}).get("payment_controllers", {})
        style      = self.btn_styles.get("tpv_danger", {})

        title_font_cfg = fonts_cfg.get("titulo", {})
        btn_font_cfg   = fonts_cfg.get("button",  {})
        btn_layout     = layout_cfg.get("button", {})

        main_container = ctk.CTkFrame(self, fg_color="transparent")
        main_container.pack(
            fill="both", expand=True,
            padx=layout_cfg.get("padding", 20),
            pady=layout_cfg.get("spacing", 12),
        )

        # --- Banner decorativo: MODO DEVOLUCIÓN (no clicable) ---
        self.btn_modo = ctk.CTkButton(
            main_container,
            text="⚠ MODO DEVOLUCIÓN",
            command=lambda: None,
            fg_color=self._color_danger,
            hover_color=self._color_danger,
            text_color=self._color_text,
            font=(
                title_font_cfg.get("family", "Courier New"),
                style.get("font_size", 36),
                "bold",
            ),
            width=style.get("width", 185),
            height=btn_layout.get("height", 45),
            corner_radius=style.get("corner_radius", 18),
            border_width=style.get("border_width", 0),
        )
        self.btn_modo.pack(pady=(0, layout_cfg.get("button_spacing_bottom", 8)))

        # --- Botones de acción ---
        btn_w  = btn_layout.get("width",         200)
        btn_h  = btn_layout.get("height",         45)
        btn_cr = btn_layout.get("corner_radius",  22)
        btn_bw = btn_layout.get("border_width",    2)
        btn_font = (
            btn_font_cfg.get("family", "Courier New"),
            btn_font_cfg.get("size",   20),
            "bold",
        )

        def _make_btn(text, colors, command):
            return ctk.CTkButton(
                main_container,
                text=text,
                command=command,
                fg_color=colors["bg"],
                hover_color=colors["hover"],
                text_color=colors["text"],
                border_color=colors["border"],
                font=btn_font,
                width=btn_w,
                height=btn_h,
                corner_radius=btn_cr,
                border_width=btn_bw,
            )

        # Solo mostrar el botón de CAMBIO para finalizar devoluciones
        self.btn_cambio = _make_btn(
            "FINALIZAR", self._btn_cambio, lambda: self._on_btn("cambio")
        )
        self.btn_cambio.pack(pady=(0, 0))

    def _on_btn(self, forma_pago: str):
        if self.on_finalizar_callback:
            self.on_finalizar_callback({"forma_pago": forma_pago, "total": self.total})

    def set_total(self, total: float):
        self.total = total
