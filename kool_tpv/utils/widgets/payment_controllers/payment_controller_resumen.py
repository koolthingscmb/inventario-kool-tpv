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
        logger.info(f"PaymentControllerResumen ticket={ticket_data.get('num_ticket')}")

    def _create_widgets(self):
        title_font = self.config.get_font("titulo")
        label_font = self.config.get_font("label")
        value_font = self.config.get_font("value")
        
        # Fuentes personalizadas para el nuevo layout
        font_family = label_font[0] if isinstance(label_font, tuple) else "Helvetica"
        large_font = (font_family, 18, "bold")
        xlarge_font = (font_family, 48, "bold")

        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=20, pady=12)

        # 1- Título
        ctk.CTkLabel(main, text="TICKET COMPLETADO", font=title_font,
                     text_color=self.config.get_color("text_titulo")).pack(pady=(0, 20))

        # Datos
        num_ticket = self.ticket_data.get("num_ticket", "---")
        total = self.ticket_data.get("total", 0.0)
        forma_pago = self.ticket_data.get("forma_pago", "---")
        efectivo = self.ticket_data.get("efectivo_entregado", 0.0)
        cambio = self.ticket_data.get("cambio", 0.0)
        cliente = self.ticket_data.get("cliente_nombre", "")

        # 3- GRID 4X1 (Ticket e ID, Forma Pago y Tipo)
        row1 = ctk.CTkFrame(main, fg_color="transparent")
        row1.pack(fill="x", pady=5)
        row1.grid_columnconfigure((1, 3), weight=1)
        
        ctk.CTkLabel(row1, text="Ticket:", font=label_font, text_color=self.config.get_color("text_label")).grid(row=0, column=0, sticky="w", padx=(0, 5))
        ctk.CTkLabel(row1, text=f"#{num_ticket}", font=value_font, text_color=self.config.get_color("text")).grid(row=0, column=1, sticky="w")
        
        ctk.CTkLabel(row1, text="Forma Pago:", font=label_font, text_color=self.config.get_color("text_label")).grid(row=0, column=2, sticky="w", padx=(10, 5))
        ctk.CTkLabel(row1, text=forma_pago, font=value_font, text_color=self.config.get_color("text")).grid(row=0, column=3, sticky="w")

        # 4- GRID 4X1 (Total y Entregado) - Fuente más grande
        row2 = ctk.CTkFrame(main, fg_color="transparent")
        row2.pack(fill="x", pady=15)
        row2.grid_columnconfigure((1, 3), weight=1)
        
        ctk.CTkLabel(row2, text="Total:", font=large_font, text_color=self.config.get_color("text_label")).grid(row=0, column=0, sticky="w", padx=(0, 5))
        ctk.CTkLabel(row2, text=f"{total:.2f} €", font=large_font, text_color=self.config.get_color("text_titulo")).grid(row=0, column=1, sticky="w")
        
        if efectivo > 0:
            ctk.CTkLabel(row2, text="Entregado:", font=large_font, text_color=self.config.get_color("text_label")).grid(row=0, column=2, sticky="w", padx=(10, 5))
            ctk.CTkLabel(row2, text=f"{efectivo:.2f} €", font=large_font, text_color=self.config.get_color("text")).grid(row=0, column=3, sticky="w")

        # 5- Grid 2x1 (Cambio) - Fuente MUCHO más grande
        if cambio > 0:
            row3 = ctk.CTkFrame(main, fg_color="transparent")
            row3.pack(fill="x", pady=10)
            row3.grid_columnconfigure(1, weight=1)
            
            ctk.CTkLabel(row3, text="Cambio:", font=xlarge_font, text_color=self.config.get_color("text_label")).grid(row=0, column=0, sticky="w", padx=(0, 10))
            ctk.CTkLabel(row3, text=f"{cambio:.2f} €", font=xlarge_font, text_color=self.config.get_color("text_cambio")).grid(row=0, column=1, sticky="w")

    def _on_nueva_venta(self):
        if self.on_nueva_venta_callback:
            self.on_nueva_venta_callback()
