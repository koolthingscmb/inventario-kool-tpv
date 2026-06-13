"""
PaymentControllerEfectivo - Widget para pago en efectivo
Entry + cálculo de cambio + validación
"""
import logging
import customtkinter as ctk
from typing import Optional, Callable
from decimal import Decimal, InvalidOperation
from . import PaymentConfigHelper

logger = logging.getLogger(__name__)


class PaymentControllerEfectivo(ctk.CTkFrame):
    """Controller efectivo: entry + cambio + validación."""

    def __init__(
        self,
        parent,
        total: float = 0.0,
        on_finalizar: Optional[Callable] = None,
        **kwargs
    ):
        """
        Args:
            parent: Widget padre
            total: Total a cobrar
            on_finalizar: Callback cuando se pulsa Finalizar
        """
        # Inicializar ConfigHelper
        self.config = PaymentConfigHelper("efectivo")

        super().__init__(
            parent,
            fg_color=self.config.get_bg_color(),
            border_width=self.config.get_layout_value("border_width"),
            border_color=self.config.get_color("border"),
            corner_radius=self.config.get_layout_value("corner_radius"),
            **kwargs
        )

        self.total = total
        self.on_finalizar_callback = on_finalizar
        self.cantidad_entregada = 0.0

        # Crear UI
        self._create_widgets()

        # Focus automático en entry después de crear widgets
        self.after_idle(lambda: self.entry_cantidad.focus_set())

        logger.info("PaymentControllerEfectivo inicializado")

    def _create_widgets(self):
        """Crear widgets del controller."""
        # Obtener configuraciones usando ConfigHelper
        titulo_font = self.config.get_font("titulo")
        label_font = self.config.get_font("label")
        entry_font = self.config.get_font("entry")
        button_font = self.config.get_font("button")
        cambio_font = self.config.get_font("cambio")
        error_font = self.config.get_font("error")

        # Container principal
        main_container = ctk.CTkFrame(self, fg_color="transparent")
        main_container.pack(
            fill="both", 
            expand=True, 
            padx=self.config.get_layout_value("padding"), 
            pady=self.config.get_layout_value("spacing")
        )

        # Título
        titulo = ctk.CTkLabel(
            main_container,
            text="PAGO EN EFECTIVO",
            font=titulo_font,
            text_color=self.config.get_color("text_titulo")
        )
        titulo.pack(pady=(0, self.config.get_layout_value("titulo_bottom")))

        # Grid 1×3
        grid_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        grid_frame.pack(fill="x", pady=(0, self.config.get_layout_value("grid_bottom")))

        # Configurar columnas
        grid_frame.grid_columnconfigure(0, weight=0)
        grid_frame.grid_columnconfigure(1, weight=0)
        grid_frame.grid_columnconfigure(2, weight=1)

        # COLUMNA 1: Label "Entregado:"
        ctk.CTkLabel(
            grid_frame,
            text="Entregado:",
            font=label_font,
            text_color=self.config.get_color("text_label"),
            anchor="e"
        ).grid(row=0, column=0, sticky="e", padx=(0, self.config.get_layout_value("label_padx_right")))

        # COLUMNA 2: Entry
        self.entry_cantidad = ctk.CTkEntry(
            grid_frame,
            width=self.config.get_layout_value("entry_width"),
            height=self.config.get_layout_value("entry_height"),
            font=entry_font,
            justify="center"
        )
        self.entry_cantidad.grid(row=0, column=1, padx=(0, self.config.get_layout_value("entry_padx_right")))
        self.entry_cantidad.bind('<KeyRelease>', self._on_cantidad_change)
        self.entry_cantidad.bind('<Return>', lambda e: self._on_finalizar())
        self.entry_cantidad.bind('<Tab>', lambda e: (self.btn_finalizar.focus_set(), 'break'))

        # COLUMNA 3: Cambio
        self.cambio_label = ctk.CTkLabel(
            grid_frame,
            text=f"Cambio: 0.00€",
            font=cambio_font,
            text_color=self.config.get_color("text_cambio"),
            anchor="e"
        )
        self.cambio_label.grid(row=0, column=2, sticky="e")

        # Label error
        self.error_label = ctk.CTkLabel(
            main_container,
            text="",
            font=error_font,
            text_color=self.config.get_color("text_error"),
            anchor="center"
        )
        self.error_label.pack(pady=(self.config.get_layout_value("error_top"), self.config.get_layout_value("error_bottom")))

        # Colores de borde para feedback visual de focus
        color_borde_normal = self.config.get_color("border", context="button")
        color_borde_foco = self.config.get_color("border_hover")  # Del payment_controller (más brillante)
        if not color_borde_foco:
            color_borde_foco = self.config.get_color("hover", context="button")

        # Botón Finalizar
        self.btn_finalizar = ctk.CTkButton(
            main_container,
            text="FINALIZAR VENTA",
            command=self._on_finalizar,
            fg_color=self.config.get_color("bg", context="button"),
            hover_color=self.config.get_color("hover", context="button"),
            text_color=self.config.get_color("text", context="button"),
            font=button_font,
            width=self.config.get_layout_value("button", "width"),
            height=self.config.get_layout_value("button", "height"),
            corner_radius=self.config.get_layout_value("button", "corner_radius"),
            border_width=self.config.get_layout_value("button", "border_width"),
            border_color=color_borde_normal,
            state="disabled"
        )
        self.btn_finalizar.pack(pady=(self.config.get_layout_value("button_spacing_top"), self.config.get_layout_value("button_spacing_bottom")))
        
        # BINDINGS
        # 1. TAB para navegar
        self.btn_finalizar.bind('<Tab>', lambda e: (self.entry_cantidad.focus_set(), 'break'))
        
        # 2. ENTER para finalizar
        self.btn_finalizar.bind('<Return>', lambda e: self._on_finalizar())
        
        # 3. Feedback visual de focus (borde más brillante cuando tiene focus)
        self.btn_finalizar.bind('<FocusIn>', lambda e: self.btn_finalizar.configure(border_color=color_borde_foco))
        self.btn_finalizar.bind('<FocusOut>', lambda e: self.btn_finalizar.configure(border_color=color_borde_normal))

    def _on_cantidad_change(self, event=None):
        """Handler cuando cambia la cantidad en el entry."""
        try:
            texto = self.entry_cantidad.get().strip()

            if not texto:
                self.cantidad_entregada = 0.0
                self.cambio_label.configure(text="Cambio: 0.00€")
                self.error_label.configure(text="")
                try:
                    self.btn_finalizar.configure(state="disabled")
                except Exception:
                    pass
                return

            # Intentar convertir a float
            try:
                cantidad = Decimal(texto.replace(',', '.'))
            except (ValueError, InvalidOperation):
                self.error_label.configure(text="Cantidad no válida")
                try:
                    self.btn_finalizar.configure(state="disabled")
                except Exception:
                    pass
                return

            self.cantidad_entregada = cantidad

            # Calcular cambio
            cambio = cantidad - self.total

            if cambio < 0:
                # Cantidad insuficiente
                self.cambio_label.configure(text=f"Falta: {abs(cambio):.2f}€")
                self.error_label.configure(text="Cantidad insuficiente")
                try:
                    self.btn_finalizar.configure(state="disabled")
                except Exception:
                    pass
            else:
                # Cantidad correcta
                self.cambio_label.configure(text=f"Cambio: {cambio:.2f}€")
                self.error_label.configure(text="")
                try:
                    self.btn_finalizar.configure(state="normal")
                except Exception:
                    pass

        except Exception:
            logger.exception("Error calculando cambio")

    def _on_finalizar(self):
        """Handler botón Finalizar."""
        try:
            if self.cantidad_entregada < self.total:
                self.error_label.configure(text="Cantidad insuficiente")
                return

            if self.on_finalizar_callback:
                cambio = self.cantidad_entregada - self.total
                self.on_finalizar_callback({
                    "tipo_pago": "Efectivo",
                    "total": self.total,
                    "cantidad_entregada": self.cantidad_entregada,
                    "cambio": cambio
                })
        except Exception:
            logger.exception("Error en _on_finalizar")

    def set_total(self, total: float):
        """Actualizar total a cobrar."""
        self.total = total
        # Si total es 0 o negativo (vale cubre todo), pre-llenar 0 y activar botón
        if self.total <= 0:
            try:
                self.entry_cantidad.delete(0, 'end')
                self.entry_cantidad.insert(0, '0')
            except Exception:
                pass
            self.cantidad_entregada = Decimal('0')
            self.cambio_label.configure(text="Cambio: 0.00€")
            self.error_label.configure(text="")
            try:
                self.btn_finalizar.configure(state="normal")
            except Exception:
                pass
            return
        # Recalcular cambio
        try:
            self._on_cantidad_change()
        except Exception:
            pass
