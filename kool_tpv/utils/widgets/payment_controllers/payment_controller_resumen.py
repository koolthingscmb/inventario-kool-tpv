"""PaymentControllerResumen - Widget de resumen tras finalizar ticket."""
import logging
import customtkinter as ctk
from typing import Optional, Callable, Dict, Any
from . import PaymentConfigHelper

logger = logging.getLogger(__name__)


class PaymentControllerResumen(ctk.CTkFrame):
    """Controller de resumen post-venta."""

    def __init__(self, parent, ticket_data: Dict[str, Any], on_nueva_venta: Optional[Callable] = None, **kwargs):
        self.config = PaymentConfigHelper("resumen")
        super().__init__(parent, fg_color=self.config.get_bg_color(),
                         border_width=self.config.get_layout_value("border_width") or 5,
                         border_color=self.config.get_color("border"),
                         corner_radius=self.config.get_layout_value("corner_radius") or 18, **kwargs)
        self.ticket_data = ticket_data
        self.on_nueva_venta_callback = on_nueva_venta
        self._create_widgets()
        self.after_idle(lambda: self.focus_set())
        self.bind("<Return>", lambda e: self._on_nueva_venta())
        self.bind("<KP_Enter>", lambda e: self._on_nueva_venta())
        logger.info(f"PaymentControllerResumen ticket={ticket_data.get('num_ticket')}")

    def _create_widgets(self):
        title_font = self.config.get_font("titulo")
        label_font = self.config.get_font("label")
        value_font = self.config.get_font("value")
        button_font = self.config.get_font("button")

        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=20, pady=12)

        # Título
        ctk.CTkLabel(main, text="TICKET COMPLETADO", font=title_font,
                     text_color=self.config.get_color("text_titulo")).pack(pady=(0, 16))

        # Separador
        ctk.CTkFrame(main, height=2, fg_color=self.config.get_color("separator", "#555555")).pack(fill="x", padx=10, pady=(0, 16))

        # Datos
        num_ticket = self.ticket_data.get("num_ticket", "---")
        total = self.ticket_data.get("total", 0.0)
        forma_pago = self.ticket_data.get("forma_pago", "---")
        efectivo = self.ticket_data.get("efectivo_entregado", 0.0)
        cambio = self.ticket_data.get("cambio", 0.0)
        cliente = self.ticket_data.get("cliente_nombre", "")

        self._row(main, "TICKET:", f"#{num_ticket}", label_font, value_font)
        if cliente:
            self._row(main, "CLIENTE:", cliente, label_font, value_font)
        self._row(main, "FORMA DE PAGO:", forma_pago, label_font, value_font)
        self._row(main, "TOTAL:", f"{total:.2f} €", label_font, value_font, True)
        if efectivo > 0:
            self._row(main, "ENTREGADO:", f"{efectivo:.2f} €", label_font, value_font)
        if cambio > 0:
            self._row(main, "CAMBIO:", f"{cambio:.2f} €", label_font, value_font, True, True)

        # Espacio
        ctk.CTkFrame(main, fg_color="transparent", height=20).pack()

        # Botón
        color_normal = self.config.get_color("border", context="button")
        color_foco = self.config.get_color("border_hover") or self.config.get_color("hover", context="button")

        self.btn = ctk.CTkButton(main, text="ENTER → NUEVA VENTA", command=self._on_nueva_venta,
                                 fg_color=self.config.get_color("bg", context="button"),
                                 hover_color=self.config.get_color("hover", context="button"),
                                 text_color=self.config.get_color("text", context="button"),
                                 font=button_font, width=220, height=50, corner_radius=22,
                                 border_width=2, border_color=color_normal)
        self.btn.pack(pady=(10, 0))
        self.btn.bind("<Return>", lambda e: self._on_nueva_venta())
        self.btn.bind("<FocusIn>", lambda e: self.btn.configure(border_color=color_foco))
        self.btn.bind("<FocusOut>", lambda e: self.btn.configure(border_color=color_normal))
        self.after(100, lambda: self.btn.focus_set())

    def _row(self, parent, label, value, label_font, value_font, highlight=False, cambio=False):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=4)
        color = self.config.get_color("text_cambio" if cambio else ("text_titulo" if highlight else "text"))
        ctk.CTkLabel(row, text=label, font=label_font, text_color=self.config.get_color("text_label")).pack(side="left")
        ctk.CTkLabel(row, text=value, font=value_font, text_color=color).pack(side="right")

    def _on_nueva_venta(self):
        if self.on_nueva_venta_callback:
            self.on_nueva_venta_callback()
