"""
PaymentControllerSimple - Widget simple para pago con un solo botón
Usado para: Tarjeta, Web
"""
import logging
from pathlib import Path
import json
import customtkinter as ctk
from typing import Optional, Callable

logger = logging.getLogger(__name__)


def load_config(config_name: str) -> dict:
    """Cargar archivo de configuración."""
    try:
        base = Path(__file__).resolve().parents[3]
        config_path = base / "config" / config_name
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        logger.exception(f"Error cargando {config_name}")
        return {}


class PaymentControllerSimple(ctk.CTkFrame):
    """Controller simple: solo botón Finalizar Venta."""

    def __init__(
        self,
        parent,
        tipo_pago: str = "Tarjeta",  # "Tarjeta" o "Web"
        total: float = 0.0,
        on_finalizar: Optional[Callable] = None,
        **kwargs
    ):
        """
        Args:
            parent: Widget padre
            tipo_pago: "Tarjeta" o "Web"
            total: Total a cobrar
            on_finalizar: Callback cuando se pulsa Finalizar
        """
        # Cargar configs
        self.colors = load_config("colors_config.json")
        self.fonts = load_config("font_config.json")
        self.layout = load_config("layout_config.json")

        # Extraer configuraciones
        footer_colors = self.colors.get("tpv", {}).get("ticket_carrito", {}).get("footer", {})

        # Fondo según tipo de pago
        if tipo_pago.lower() == "tarjeta":
            bg_active = footer_colors.get("bg_active_tarjeta", "#3498db")
        elif tipo_pago.lower() == "web":
            bg_active = footer_colors.get("bg_active_web", "#88B04B")
        else:
            bg_active = footer_colors.get("bg", "#1a1a1a")

        super().__init__(parent, fg_color=bg_active, **kwargs)

        self.tipo_pago = tipo_pago
        self.total = total
        self.on_finalizar_callback = on_finalizar

        # Crear UI
        self._create_widgets()

        logger.info(f"PaymentControllerSimple ({tipo_pago}) inicializado")

    def _create_widgets(self):
        """Crear widgets del controller."""
        action_btn_cfg = self.colors.get("global", {}).get("components", {}).get("action_buttons", {}).get("primary", {})

        btn_font_cfg = self.fonts.get("components", {}).get("action_button", {})
        btn_font = (
            btn_font_cfg.get("family", "Courier New"),
            btn_font_cfg.get("size", 20),
            btn_font_cfg.get("weight", "bold")
        )

        btn_layout = self.layout.get("components", {}).get("action_button", {})

        # Label informativo según tipo de pago
        if self.tipo_pago.lower() == "tarjeta":
            texto_info = "Pago con tarjeta"
        elif self.tipo_pago.lower() == "web":
            texto_info = "Pago en la Web"
        else:
            texto_info = f"Pago: {self.tipo_pago}"

        info_label = ctk.CTkLabel(
            self,
            text=texto_info,
            font=btn_font,
            text_color="#FFFFFF"
        )
        info_label.pack(pady=(12, 8))

        # Botón Finalizar Venta
        self.btn_finalizar = ctk.CTkButton(
            self,
            text="FINALIZAR VENTA",
            command=self._on_finalizar,
            fg_color=action_btn_cfg.get("bg", "#2ecc71"),
            hover_color=action_btn_cfg.get("hover", "#27ae60"),
            text_color=action_btn_cfg.get("text", "#000000"),
            font=btn_font,
            width=btn_layout.get("width", 160),
            height=btn_layout.get("height", 35),
            corner_radius=btn_layout.get("corner_radius", 22),
            border_width=btn_layout.get("border_width", 2),
            border_color=action_btn_cfg.get("border", "#000000")
        )
        self.btn_finalizar.pack(pady=(0, 12))

        # Binding Enter
        try:
            self.btn_finalizar.bind('<Return>', lambda e: self._on_finalizar())
        except Exception:
            pass

    def _on_finalizar(self):
        """Handler botón Finalizar."""
        try:
            if self.on_finalizar_callback:
                self.on_finalizar_callback({
                    "tipo_pago": self.tipo_pago,
                    "total": self.total
                })
        except Exception:
            logger.exception("Error en _on_finalizar")

    def set_total(self, total: float):
        """Actualizar total a cobrar."""
        self.total = total
        # El total no se muestra en este controller, solo actualizar internamente
        # No necesita recrear widgets
