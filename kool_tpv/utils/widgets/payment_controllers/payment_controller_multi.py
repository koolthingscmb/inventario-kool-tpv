"""
PaymentControllerMulti - Widget para pago mixto (efectivo + tarjeta)
Dos entries con auto-balance
"""
import logging
import customtkinter as ctk
from typing import Optional, Callable
from decimal import Decimal, InvalidOperation
from . import PaymentConfigHelper

logger = logging.getLogger(__name__)


class PaymentControllerMulti(ctk.CTkFrame):
    """Controller multi: 2 entries con auto-balance."""

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
        self.config = PaymentConfigHelper("multi")

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
        self.efectivo = 0.0
        self.tarjeta = 0.0
        self._updating = False  # Flag para evitar loops

        # Crear UI
        self._create_widgets()

        # Focus automático en entry efectivo
        self.after_idle(lambda: self.entry_efectivo.focus_set())

        logger.info("PaymentControllerMulti inicializado")

    def _create_widgets(self):
        """Crear widgets del controller."""
        # Obtener configuraciones usando ConfigHelper
        title_font = self.config.get_font("titulo")
        entry_font = self.config.get_font("entry")
        error_font = self.config.get_font("error")
        button_font = self.config.get_font("button")

        # Container principal con padding
        main_container = ctk.CTkFrame(self, fg_color="transparent")
        main_container.pack(
            fill="both", 
            expand=True,
            padx=self.config.get_layout_value("padding"),
            pady=self.config.get_layout_value("spacing")
        )

        # Label informativo (Multicobro)
        total_label = ctk.CTkLabel(
            main_container,
            text="Multicobro",
            font=title_font,
            text_color=self.config.get_color("text_titulo")
        )
        total_label.pack(pady=(0, self.config.get_layout_value("titulo_bottom")))

        # Container para los 2 entries
        entries_container = ctk.CTkFrame(main_container, fg_color="transparent")
        entries_container.pack(pady=(0, self.config.get_layout_value("entries_bottom")))

        # Entry efectivo
        efectivo_frame = ctk.CTkFrame(entries_container, fg_color="transparent")
        efectivo_frame.pack(side="left", padx=self.config.get_layout_value("entries_spacing"))

        ctk.CTkLabel(
            efectivo_frame,
            text="Efectivo:",
            font=entry_font,
            text_color=self.config.get_color("text_label")
        ).pack()

        self.entry_efectivo = ctk.CTkEntry(
            efectivo_frame,
            width=self.config.get_layout_value("entry_width"),
            height=self.config.get_layout_value("entry_height"),
            font=entry_font,
            justify="center"
        )
        self.entry_efectivo.pack()
        self.entry_efectivo.bind('<KeyRelease>', lambda e: self._on_efectivo_change())
        self.entry_efectivo.bind('<Return>', lambda e: self._on_finalizar())
        self.entry_efectivo.bind('<Tab>', lambda e: (self.entry_tarjeta.focus_set(), 'break'))

        # Entry tarjeta
        tarjeta_frame = ctk.CTkFrame(entries_container, fg_color="transparent")
        tarjeta_frame.pack(side="left", padx=self.config.get_layout_value("entries_spacing"))

        ctk.CTkLabel(
            tarjeta_frame,
            text="Tarjeta:",
            font=entry_font,
            text_color=self.config.get_color("text_label")
        ).pack()

        self.entry_tarjeta = ctk.CTkEntry(
            tarjeta_frame,
            width=self.config.get_layout_value("entry_width"),
            height=self.config.get_layout_value("entry_height"),
            font=entry_font,
            justify="center"
        )
        self.entry_tarjeta.pack()
        self.entry_tarjeta.bind('<KeyRelease>', lambda e: self._on_tarjeta_change())
        self.entry_tarjeta.bind('<Return>', lambda e: self._on_finalizar())
        self.entry_tarjeta.bind('<Tab>', lambda e: (self.btn_finalizar.focus_set(), 'break'))

        # Label error
        self.error_label = ctk.CTkLabel(
            main_container,
            text="",
            font=error_font,
            text_color=self.config.get_color("text_error")
        )
        self.error_label.pack(pady=(0, self.config.get_layout_value("error_bottom")))

        # Colores de borde para feedback visual de focus
        color_borde_normal = self.config.get_color("border", context="button")
        color_borde_foco = self.config.get_color("border_hover")
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
        # 1. TAB para navegar (ciclo completo)
        self.btn_finalizar.bind('<Tab>', lambda e: (self.entry_efectivo.focus_set(), 'break'))
        
        # 2. ENTER para finalizar
        self.btn_finalizar.bind('<Return>', lambda e: self._on_finalizar())
        
        # 3. Feedback visual de focus
        self.btn_finalizar.bind('<FocusIn>', lambda e: self.btn_finalizar.configure(border_color=color_borde_foco))
        self.btn_finalizar.bind('<FocusOut>', lambda e: self.btn_finalizar.configure(border_color=color_borde_normal))

    def _on_efectivo_change(self):
        """Handler cuando cambia efectivo → calcular tarjeta."""
        if self._updating:
            return

        try:
            texto = self.entry_efectivo.get().strip()

            if not texto:
                self.efectivo = 0.0
                return

            try:
                self.efectivo = Decimal(texto.replace(',', '.'))
            except (ValueError, InvalidOperation):
                return

            # Auto-balance: calcular tarjeta
            self._updating = True
            self.tarjeta = max(0, self.total - self.efectivo)
            self.entry_tarjeta.delete(0, 'end')
            self.entry_tarjeta.insert(0, f"{self.tarjeta:.2f}")
            self._updating = False

            self._validate()

        except Exception:
            logger.exception("Error en _on_efectivo_change")
            self._updating = False

    def _on_tarjeta_change(self):
        """Handler cuando cambia tarjeta → calcular efectivo."""
        if self._updating:
            return

        try:
            texto = self.entry_tarjeta.get().strip()

            if not texto:
                self.tarjeta = 0.0
                return

            try:
                self.tarjeta = Decimal(texto.replace(',', '.'))
            except (ValueError, InvalidOperation):
                return

            # Auto-balance: calcular efectivo
            self._updating = True
            self.efectivo = max(0, self.total - self.tarjeta)
            self.entry_efectivo.delete(0, 'end')
            self.entry_efectivo.insert(0, f"{self.efectivo:.2f}")
            self._updating = False

            self._validate()

        except Exception:
            logger.exception("Error en _on_tarjeta_change")
            self._updating = False

    def _validate(self):
        """Validar que ambos importes sean > 0 y sumen el total."""
        try:
            suma = self.efectivo + self.tarjeta

            # Si total es 0 (vale cubre todo), permitir ambos en 0
            if self.total <= 0:
                if suma <= Decimal("0.01"):
                    self.error_label.configure(text="")
                    self.btn_finalizar.configure(state="normal")
                else:
                    self.error_label.configure(text=f"Suma incorrecta: {suma:.2f}€")
                    self.btn_finalizar.configure(state="disabled")
                return

            if self.efectivo <= 0 or self.tarjeta <= 0:
                self.error_label.configure(text="Ambos importes deben ser > 0")
                self.btn_finalizar.configure(state="disabled")
            elif abs(suma - self.total) > Decimal("0.01"):  # Tolerancia para decimales
                self.error_label.configure(text=f"Suma incorrecta: {suma:.2f}€")
                self.btn_finalizar.configure(state="disabled")
            else:
                self.error_label.configure(text="")
                self.btn_finalizar.configure(state="normal")

        except Exception:
            logger.exception("Error en validación")

    def _on_finalizar(self):
        """Handler botón Finalizar."""
        try:
            # Si total es 0 (vale cubre todo), permitir ambos en 0
            if self.total <= 0:
                if self.on_finalizar_callback:
                    self.on_finalizar_callback({
                        "tipo_pago": "Multi",
                        "total": self.total,
                        "efectivo": self.efectivo,
                        "tarjeta": self.tarjeta
                    })
                return

            if self.efectivo <= 0 or self.tarjeta <= 0:
                return

            if abs((self.efectivo + self.tarjeta) - self.total) > Decimal("0.01"):
                return

            if self.on_finalizar_callback:
                self.on_finalizar_callback({
                    "tipo_pago": "Multi",
                    "total": self.total,
                    "efectivo": self.efectivo,
                    "tarjeta": self.tarjeta
                })
        except Exception:
            logger.exception("Error en _on_finalizar")

    def set_total(self, total: float):
        """Actualizar total a cobrar."""
        self.total = Decimal(str(total))
        # Reset entries
        try:
            self.entry_efectivo.delete(0, 'end')
            self.entry_tarjeta.delete(0, 'end')
        except Exception:
            pass
        self.efectivo = Decimal("0.0")
        self.tarjeta = Decimal("0.0")
        # Si total es 0 (vale cubre todo), pre-llenar 0 y activar
        if self.total <= 0:
            try:
                self.entry_efectivo.insert(0, '0')
                self.entry_tarjeta.insert(0, '0')
            except Exception:
                pass
            self.error_label.configure(text="")
            try:
                self.btn_finalizar.configure(state="normal")
            except Exception:
                pass
            return
        self._validate()
