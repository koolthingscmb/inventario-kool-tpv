"""
PaymentControllerEfectivo - Widget para pago en efectivo
Entry + cálculo de cambio + validación
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
        # Cargar configs
        self.colors = load_config("colors_config.json")
        self.fonts = load_config("font_config.json")
        self.layout = load_config("layout_config.json")

        # Fondo activo para efectivo
        footer_colors = self.colors.get("tpv", {}).get("ticket_carrito", {}).get("footer", {})
        bg_active = footer_colors.get("bg_active_efectivo", "#2ecc71")

        super().__init__(parent, fg_color=bg_active, **kwargs)

        self.total = total
        self.on_finalizar_callback = on_finalizar
        self.cantidad_entregada = 0.0

        # Crear UI
        self._create_widgets()

        logger.info("PaymentControllerEfectivo inicializado")

    def _create_widgets(self):
        """Crear widgets del controller (grid 2x2 compacto)."""
        btn_font_cfg = self.fonts.get("components", {}).get("action_button", {})
        btn_font = (
            btn_font_cfg.get("family", "Courier New"),
            btn_font_cfg.get("size", 20),
            btn_font_cfg.get("weight", "bold")
        )

        entry_font_cfg = self.fonts.get("entry", {})
        entry_font = (
            entry_font_cfg.get("family", "Courier New"),
            entry_font_cfg.get("size", 16)
        )

        label_font = (
            entry_font_cfg.get("family", "Courier New"),
            entry_font_cfg.get("size", 14),
            "bold"
        )

        btn_layout = self.layout.get("components", {}).get("action_button", {})
        action_btn_cfg = self.colors.get("global", {}).get("components", {}).get("action_buttons", {}).get("primary", {})

        # Container principal con padding
        main_container = ctk.CTkFrame(self, fg_color="transparent")
        main_container.pack(fill="both", expand=True, padx=20, pady=12)

        # Grid 2×2
        grid_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        grid_frame.pack(fill="x", pady=(0, 12))

        # Configurar columnas
        grid_frame.grid_columnconfigure(0, weight=0)  # Labels (ancho fijo)
        grid_frame.grid_columnconfigure(1, weight=1)  # Entry/valores (expandible)

        # FILA 1: Cantidad entregada + Entry
        ctk.CTkLabel(
            grid_frame,
            text="Cantidad entregada:",
            font=label_font,
            text_color="#000000",
            anchor="e"
        ).grid(row=0, column=0, sticky="e", padx=(0, 12), pady=8)

        self.entry_cantidad = ctk.CTkEntry(
            grid_frame,
            width=150,
            height=40,
            font=entry_font,
            justify="center"
        )
        self.entry_cantidad.grid(row=0, column=1, sticky="w", pady=8)
        self.entry_cantidad.bind('<KeyRelease>', self._on_cantidad_change)
        self.entry_cantidad.bind('<Return>', lambda e: self._on_finalizar())

        # FILA 2: Cambio + Label dinámico
        ctk.CTkLabel(
            grid_frame,
            text="Cambio:",
            font=label_font,
            text_color="#000000",
            anchor="e"
        ).grid(row=1, column=0, sticky="e", padx=(0, 12), pady=8)

        self.cambio_label = ctk.CTkLabel(
            grid_frame,
            text="0.00€",
            font=btn_font,
            text_color="#000000",
            anchor="w"
        )
        self.cambio_label.grid(row=1, column=1, sticky="w", pady=8)

        # Label error (debajo del grid)
        self.error_label = ctk.CTkLabel(
            main_container,
            text="",
            font=entry_font,
            text_color="#e74c3c",
            anchor="center"
        )
        self.error_label.pack(pady=(0, 8))

        # Botón Finalizar
        self.btn_finalizar = ctk.CTkButton(
            main_container,
            text="FINALIZAR VENTA",
            command=self._on_finalizar,
            fg_color=action_btn_cfg.get("bg", "#2ecc71"),
            hover_color=action_btn_cfg.get("hover", "#27ae60"),
            text_color=action_btn_cfg.get("text", "#000000"),
            font=btn_font,
            width=btn_layout.get("width", 200),
            height=btn_layout.get("height", 45),
            corner_radius=btn_layout.get("corner_radius", 22),
            border_width=btn_layout.get("border_width", 2),
            border_color=action_btn_cfg.get("border", "#000000"),
            state="disabled"
        )
        self.btn_finalizar.pack(pady=(0, 8))

        # Focus automático
        try:
            self.entry_cantidad.focus_set()
        except Exception:
            pass

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
                cantidad = float(texto.replace(',', '.'))
            except ValueError:
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
        # Recalcular cambio
        try:
            self._on_cantidad_change()
        except Exception:
            pass
