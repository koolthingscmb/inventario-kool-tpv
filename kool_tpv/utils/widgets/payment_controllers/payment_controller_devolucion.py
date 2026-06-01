"""
PaymentControllerDevolucion - Widget visual para modo devolución activo.
Muestra el indicador MODO DEVOLUCIÓN en el payment_area del TicketCarrito.
"""
import logging
import customtkinter as ctk
from typing import Optional, Callable
from . import PaymentConfigHelper, load_config, norm_color

logger = logging.getLogger(__name__)


def _resolve_token(tokens: dict, token: str, fallback: str) -> str:
    """Busca un token de color en el dict anidado de design_tokens."""
    for section in tokens.values():
        if isinstance(section, dict) and token in section:
            return norm_color(section[token])
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
        # Cargar tokens y styles (devolución no tiene config propio)
        self.tokens = load_config("design_tokens.json")
        self.btn_styles = load_config("button_styles.json")
        
        # ConfigHelpers para los botones de efectivo y tarjeta
        self.config_efectivo = PaymentConfigHelper("efectivo")
        self.config_tarjeta = PaymentConfigHelper("tarjeta")
        self.config_layout = PaymentConfigHelper("efectivo")  # Cualquiera para layout general

        # Colores del banner "MODO DEVOLUCIÓN"
        style = self.btn_styles.get("tpv_danger", {})
        self._color_danger = _resolve_token(self.tokens, style.get("bg_token", "red_danger"), "#FF0000")
        self._color_text = _resolve_token(self.tokens, style.get("text_token", "white_base"), "#FFFFFF")

        # Colores de botones de acción (usan configs de otros payment controllers)
        self._btn_efectivo = {
            "bg": self.config_efectivo.get_color("bg", context="button"),
            "hover": self.config_efectivo.get_color("hover", context="button"),
            "text": self.config_efectivo.get_color("text", context="button"),
            "border": self.config_efectivo.get_color("border", context="button"),
        }
        self._btn_tarjeta = {
            "bg": self.config_tarjeta.get_color("bg", context="button"),
            "hover": self.config_tarjeta.get_color("hover", context="button"),
            "text": self.config_tarjeta.get_color("text", context="button"),
            "border": self.config_tarjeta.get_color("border", context="button"),
        }
        self._btn_cambio = {
            "bg": "#000000",
            "hover": _resolve_token(self.tokens, "orange_hover", "#e67e22"),
            "text": _resolve_token(self.tokens, "orange_config", "#FF9800"),
            "border": _resolve_token(self.tokens, "orange_config", "#FF9800"),
        }

        # Frame principal
        super().__init__(
            parent,
            fg_color=self.config_layout.get_bg_color(),
            border_width=self.config_layout.get_layout_value("border_width"),
            border_color=self._color_danger,
            corner_radius=self.config_layout.get_layout_value("corner_radius"),
            **kwargs
        )

        self.total = total
        self.on_finalizar_callback = on_finalizar

        self._create_widgets()
        logger.info("PaymentControllerDevolucion inicializado")

    def _create_widgets(self):
        # Obtener configuraciones
        title_font = self.config_layout.get_font("titulo")
        button_font = self.config_layout.get_font("button")
        style = self.btn_styles.get("tpv_danger", {})

        main_container = ctk.CTkFrame(self, fg_color="transparent")
        main_container.pack(
            fill="both", 
            expand=True,
            padx=self.config_layout.get_layout_value("padding"),
            pady=self.config_layout.get_layout_value("spacing"),
        )

        # Banner decorativo: MODO DEVOLUCIÓN (no clicable)
        self.btn_modo = ctk.CTkButton(
            main_container,
            text="⚠ MODO DEVOLUCIÓN",
            command=lambda: None,
            fg_color=self._color_danger,
            hover_color=self._color_danger,
            text_color=self._color_text,
            font=(
                title_font[0] if title_font else "Courier New",
                style.get("font_size", 36),
                "bold",
            ),
            width=style.get("width", 185),
            height=self.config_layout.get_layout_value("button", "height"),
            corner_radius=style.get("corner_radius", 18),
            border_width=style.get("border_width", 0),
        )
        self.btn_modo.pack(pady=(0, self.config_layout.get_layout_value("button_spacing_bottom")))

        # Botones de acción
        btn_w = self.config_layout.get_layout_value("button", "width")
        btn_h = self.config_layout.get_layout_value("button", "height")
        btn_cr = self.config_layout.get_layout_value("button", "corner_radius")
        btn_bw = self.config_layout.get_layout_value("button", "border_width")

        def _make_btn(text, colors, command):
            return ctk.CTkButton(
                main_container,
                text=text,
                command=command,
                fg_color=colors["bg"],
                hover_color=colors["hover"],
                text_color=colors["text"],
                border_color=colors["border"],
                font=button_font,
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
