"""
PaymentControllerMulti - Widget para pago mixto (efectivo + tarjeta)
Dos entries con auto-balance
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
        # Cargar configs
        self.colors = load_config("colors_config.json")
        self.fonts = load_config("font_config.json")
        self.layout = load_config("layout_config.json")

        # Fondo (usar color primario o default)
        footer_colors = self.colors.get("tpv", {}).get("ticket_carrito", {}).get("footer", {})
        bg = footer_colors.get("bg", "#1a1a1a")

        super().__init__(parent, fg_color=bg, **kwargs)

        self.total = total
        self.on_finalizar_callback = on_finalizar
        self.efectivo = 0.0
        self.tarjeta = 0.0
        self._updating = False  # Flag para evitar loops

        # Crear UI
        self._create_widgets()

        logger.info("PaymentControllerMulti inicializado")

    def _create_widgets(self):
        """Crear widgets del controller."""
        btn_font_cfg = self.fonts.get("components", {}).get("action_button", {})
        btn_font = (
            btn_font_cfg.get("family", "Courier New"),
            btn_font_cfg.get("size", 20),
            btn_font_cfg.get("weight", "bold")
        )

        entry_font_cfg = self.fonts.get("entry", {})
        entry_font = (
            entry_font_cfg.get("family", "Courier New"),
            entry_font_cfg.get("size", 14)
        )

        btn_layout = self.layout.get("components", {}).get("action_button", {})
        action_btn_cfg = self.colors.get("global", {}).get("components", {}).get("action_buttons", {}).get("primary", {})

        # Label total
        total_label = ctk.CTkLabel(
            self,
            text=f"Total a cobrar: {self.total:.2f}€",
            font=btn_font,
            text_color="#FFFFFF"
        )
        total_label.pack(pady=(12, 8))

        # Container para los 2 entries
        entries_container = ctk.CTkFrame(self, fg_color="transparent")
        entries_container.pack(pady=(0, 8))

        # Entry efectivo
        efectivo_frame = ctk.CTkFrame(entries_container, fg_color="transparent")
        efectivo_frame.pack(side="left", padx=8)

        ctk.CTkLabel(
            efectivo_frame,
            text="Efectivo:",
            font=entry_font,
            text_color="#FFFFFF"
        ).pack()

        self.entry_efectivo = ctk.CTkEntry(
            efectivo_frame,
            width=120,
            height=40,
            font=entry_font,
            justify="center"
        )
        self.entry_efectivo.pack()
        self.entry_efectivo.bind('<KeyRelease>', lambda e: self._on_efectivo_change())

        # Entry tarjeta
        tarjeta_frame = ctk.CTkFrame(entries_container, fg_color="transparent")
        tarjeta_frame.pack(side="left", padx=8)

        ctk.CTkLabel(
            tarjeta_frame,
            text="Tarjeta:",
            font=entry_font,
            text_color="#FFFFFF"
        ).pack()

        self.entry_tarjeta = ctk.CTkEntry(
            tarjeta_frame,
            width=120,
            height=40,
            font=entry_font,
            justify="center"
        )
        self.entry_tarjeta.pack()
        self.entry_tarjeta.bind('<KeyRelease>', lambda e: self._on_tarjeta_change())

        # Label error
        self.error_label = ctk.CTkLabel(
            self,
            text="",
            font=entry_font,
            text_color="#e74c3c"
        )
        self.error_label.pack(pady=(0, 8))

        # Botón Finalizar
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
            border_color=action_btn_cfg.get("border", "#000000"),
            state="disabled"
        )
        self.btn_finalizar.pack(pady=(0, 12))

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
                self.efectivo = float(texto.replace(',', '.'))
            except ValueError:
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
                self.tarjeta = float(texto.replace(',', '.'))
            except ValueError:
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

            if self.efectivo <= 0 or self.tarjeta <= 0:
                self.error_label.configure(text="Ambos importes deben ser > 0")
                self.btn_finalizar.configure(state="disabled")
            elif abs(suma - self.total) > 0.01:  # Tolerancia para decimales
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
            if self.efectivo <= 0 or self.tarjeta <= 0:
                return

            if abs((self.efectivo + self.tarjeta) - self.total) > 0.01:
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
        self.total = total
        # Reset entries
        try:
            self.entry_efectivo.delete(0, 'end')
            self.entry_tarjeta.delete(0, 'end')
        except Exception:
            pass
        self.efectivo = 0.0
        self.tarjeta = 0.0
        self._validate()
