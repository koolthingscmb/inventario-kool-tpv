"""
PaymentControllerSimple - Widget simple para pago con un solo botón
Usado para: Tarjeta, Web
"""
import logging
import customtkinter as ctk
from typing import Optional, Callable
from . import PaymentConfigHelper

logger = logging.getLogger(__name__)


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
        # Determinar key de configuración según tipo de pago
        config_key = "tarjeta" if tipo_pago.lower() == "tarjeta" else "web"
        
        # Inicializar ConfigHelper
        self.config = PaymentConfigHelper(config_key)

        super().__init__(
            parent,
            fg_color=self.config.get_bg_color(),
            border_width=self.config.get_layout_value("border_width") or 5,
            border_color=self.config.get_color("border"),
            corner_radius=self.config.get_layout_value("corner_radius") or 18,
            **kwargs
        )

        self.tipo_pago = tipo_pago
        self.total = total
        self.on_finalizar_callback = on_finalizar

        # Crear UI
        self._create_widgets()

        # Focus automático al botón
        self.after_idle(lambda: self.btn_finalizar.focus_set())

        logger.info(f"PaymentControllerSimple ({tipo_pago}) inicializado")

    def _create_widgets(self):
        """Crear widgets del controller."""
        # Obtener configuraciones usando ConfigHelper
        title_font = self.config.get_font("titulo")
        button_font = self.config.get_font("button")

        # Container
        main_container = ctk.CTkFrame(self, fg_color="transparent")
        main_container.pack(
            fill="both", 
            expand=True,
            padx=self.config.get_layout_value("padding") or 20,
            pady=self.config.get_layout_value("spacing") or 12
        )

        # Título
        texto_info = "Pago con tarjeta" if self.tipo_pago.lower() == "tarjeta" else "Pago en la Web"

        titulo_bottom_padding = self.config.get_layout_value("titulo_bottom") or 12
        
        ctk.CTkLabel(
            main_container,
            text=texto_info,
            font=title_font,
            text_color=self.config.get_color("text_titulo")
        ).pack(pady=(0, titulo_bottom_padding))

        # Colores de borde para feedback visual de focus
        color_borde_normal = self.config.get_color("border", context="button")
        color_borde_foco = self.config.get_color("border_hover")
        if not color_borde_foco:
            color_borde_foco = self.config.get_color("hover", context="button")

        # BOTÓN FINALIZAR
        self.btn_finalizar = ctk.CTkButton(
            main_container,
            text="FINALIZAR VENTA",
            command=self._on_finalizar,
            fg_color=self.config.get_color("bg", context="button"),
            hover_color=self.config.get_color("hover", context="button"),
            text_color=self.config.get_color("text", context="button"),
            font=button_font,
            width=self.config.get_layout_value("button", "width") or 200,
            height=self.config.get_layout_value("button", "height") or 45,
            corner_radius=self.config.get_layout_value("button", "corner_radius") or 22,
            border_width=self.config.get_layout_value("button", "border_width") or 2,
            border_color=color_borde_normal
        )
        
        btn_spacing_top = self.config.get_layout_value("button_spacing_top") or 8
        btn_spacing_bottom = self.config.get_layout_value("button_spacing_bottom") or 8
        self.btn_finalizar.pack(pady=(btn_spacing_top, btn_spacing_bottom))

        # BINDINGS
        # 1. ENTER para finalizar
        self.btn_finalizar.bind('<Return>', lambda e: self._on_finalizar())

        # 2. Feedback visual de focus
        self.btn_finalizar.bind('<FocusIn>', lambda e: self.btn_finalizar.configure(border_color=color_borde_foco))
        self.btn_finalizar.bind('<FocusOut>', lambda e: self.btn_finalizar.configure(border_color=color_borde_normal))


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
