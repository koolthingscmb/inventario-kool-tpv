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


def _norm_color(val: str) -> str:
    try:
        if not val:
            return ''
        if not isinstance(val, str):
            return val
        s = val.strip()
        if not s:
            return ''
        s_low = s.lower()
        if s_low in ("transparent", "none"):
            return s_low
        s = s.lstrip('#')
        return '#' + s
    except Exception:
        return val


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

        # Leer configuración específica de multi
        pc_colors = self.colors.get("tpv", {}).get("payment_controllers", {}).get("multi", {})
        pc_layout = self.layout.get("modules", {}).get("tpv", {}).get("ticket_carrito", {}).get("payment_controllers", {})

        # Aplicar desde config (si bg es 'transparent' usar footer.bg como fallback)
        footer_bg = self.colors.get("tpv", {}).get("ticket_carrito", {}).get("footer", {}).get("bg", "#1a1a1a")
        raw_bg = (pc_colors.get("bg", "transparent") or "").strip()
        if raw_bg.lower() in ("transparent", "none", ""):
            final_bg = _norm_color(footer_bg)
        else:
            final_bg = _norm_color(raw_bg)

        # Debug: log raw and normalized colors to trace invalid values
        try:
            logger.debug(f"PaymentControllerMulti raw_bg={raw_bg!r}, footer_bg={footer_bg!r}, final_bg={final_bg!r}, border={pc_colors.get('border')!r}")
        except Exception:
            pass

        super().__init__(
            parent,
            fg_color=final_bg,
            border_width=pc_layout.get("border_width", 3),
            border_color=_norm_color(pc_colors.get("border", "#9b59b6")),
            corner_radius=pc_layout.get("corner_radius", 18),
            **kwargs
        )

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
        pcfg = self.colors.get("tpv", {}).get("payment_controllers", {}).get("multi", {})
        fonts_cfg = self.fonts.get("modules", {}).get("tpv", {}).get("payment_controllers", {})
        layout_cfg = self.layout.get("modules", {}).get("tpv", {}).get("payment_controllers", {})

        # Container principal con padding
        main_container = ctk.CTkFrame(self, fg_color="transparent")
        main_container.pack(fill="both", expand=True,
            padx=layout_cfg.get("padding", 20),
            pady=layout_cfg.get("spacing", 12))

        # Fonts and layout
        title_font = (
            fonts_cfg.get("titulo", {}).get("family", "Courier New"),
            fonts_cfg.get("titulo", {}).get("size", 20),
            fonts_cfg.get("titulo", {}).get("weight", "bold")
        )

        entry_font = (
            fonts_cfg.get("entry", {}).get("family", "Courier New"),
            fonts_cfg.get("entry", {}).get("size", 14)
        )

        error_font = (
            fonts_cfg.get("error", {}).get("family", "Courier New"),
            fonts_cfg.get("error", {}).get("size", 12)
        )

        multi_layout = layout_cfg.get("multi", {})
        entry_w = multi_layout.get("entry_width", 120)
        entry_h = multi_layout.get("entry_height", 40)
        entries_spacing = multi_layout.get("entries_spacing", 16)
        btn_layout = layout_cfg.get("button", {})
        btn_cfg = pcfg.get("button", {})
        btn_cfg = {k: _norm_color(v) if isinstance(v, str) else v for k, v in btn_cfg.items()}

        # Label informativo (Multicobro)
        total_label = ctk.CTkLabel(
            main_container,
            text="Multicobro",
            font=title_font,
            text_color=_norm_color(pcfg.get("text_titulo", "#FFFFFF"))
        )
        multi_cfg = layout_cfg.get("multi", {})
        total_label.pack(pady=(0, multi_cfg.get("titulo_bottom", 8)))

        # Container para los 2 entries
        entries_container = ctk.CTkFrame(main_container, fg_color="transparent")
        entries_container.pack(pady=(0, multi_cfg.get("entries_bottom", 8)))

        # Entry efectivo
        efectivo_frame = ctk.CTkFrame(entries_container, fg_color="transparent")
        efectivo_frame.pack(side="left", padx=multi_cfg.get("entries_spacing", 16))

        ctk.CTkLabel(
            efectivo_frame,
            text="Efectivo:",
            font=entry_font,
            text_color=_norm_color(pcfg.get("text_label", "#FFFFFF"))
        ).pack()

        self.entry_efectivo = ctk.CTkEntry(
            efectivo_frame,
            width=entry_w,
            height=entry_h,
            font=entry_font,
            justify="center"
        )
        self.entry_efectivo.pack()
        self.entry_efectivo.bind('<KeyRelease>', lambda e: self._on_efectivo_change())

        # Focus automático en efectivo
        try:
            self.entry_efectivo.focus_set()
        except Exception:
            pass

        # TAB: efectivo → tarjeta
        self.entry_efectivo.bind('<Tab>', lambda e: (self.entry_tarjeta.focus_set(), 'break'))

        # Entry tarjeta
        tarjeta_frame = ctk.CTkFrame(entries_container, fg_color="transparent")
        tarjeta_frame.pack(side="left", padx=multi_cfg.get("entries_spacing", 16))

        ctk.CTkLabel(
            tarjeta_frame,
            text="Tarjeta:",
            font=entry_font,
            text_color=_norm_color(pcfg.get("text_label", "#FFFFFF"))
        ).pack()

        self.entry_tarjeta = ctk.CTkEntry(
            tarjeta_frame,
            width=entry_w,
            height=entry_h,
            font=entry_font,
            justify="center"
        )
        self.entry_tarjeta.pack()
        self.entry_tarjeta.bind('<KeyRelease>', lambda e: self._on_tarjeta_change())

        # TAB: tarjeta → botón finalizar
        self.entry_tarjeta.bind('<Tab>', lambda e: (self.btn_finalizar.focus_set(), 'break'))

        # Label error
        self.error_label = ctk.CTkLabel(
            main_container,
            text="",
            font=error_font,
            text_color=_norm_color(pcfg.get("text_error", "#e74c3c"))
        )
        self.error_label.pack(pady=(0, multi_cfg.get("error_bottom", 8)))

        # Botón Finalizar
        self.btn_finalizar = ctk.CTkButton(
            main_container,
            text="FINALIZAR VENTA",
            command=self._on_finalizar,
            fg_color=btn_cfg.get("bg", "#2ecc71"),
            hover_color=btn_cfg.get("hover", "#27ae60"),
            text_color=_norm_color(btn_cfg.get("text", "#000000")),
            font=(btn_cfg.get("family", title_font[0]), btn_cfg.get("size", title_font[1])),
            width=btn_layout.get("width", 160),
            height=btn_layout.get("height", 35),
            corner_radius=btn_layout.get("corner_radius", 22),
            border_width=btn_layout.get("border_width", 2),
            border_color=_norm_color(btn_cfg.get("border", "#000000")),
            state="disabled"
        )
        btn_spacing_top = layout_cfg.get("button_spacing_top", 12)
        btn_spacing_bottom = layout_cfg.get("button_spacing_bottom", 8)

        self.btn_finalizar.pack(pady=(btn_spacing_top, btn_spacing_bottom))

        # TAB: botón → volver a efectivo (ciclo)
        try:
            self.btn_finalizar.bind('<Tab>', lambda e: (self.entry_efectivo.focus_set(), 'break'))
        except Exception:
            pass

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
