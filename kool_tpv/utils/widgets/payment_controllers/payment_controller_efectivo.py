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


def _norm_color(val: str) -> str:
    """Normaliza valores de color: elimina hashes repetidos y espacios."""
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
        # remove leading # and return normalized hex-like string
        s = s.lstrip('#')
        return '#' + s
    except Exception:
        return val


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

        # Leer configuración específica de payment_controllers.efectivo
        pc_colors = self.colors.get("tpv", {}).get("payment_controllers", {}).get("efectivo", {})
        pc_layout = self.layout.get("modules", {}).get("tpv", {}).get("ticket_carrito", {}).get("payment_controllers", {})

        # Aplicar colores y bordes desde config (fallback a footer.bg si bg es 'transparent')
        footer_bg = self.colors.get("tpv", {}).get("ticket_carrito", {}).get("footer", {}).get("bg", "#1a1a1a")
        raw_bg = (pc_colors.get("bg", "transparent") or "").strip()
        if raw_bg.lower() in ("transparent", "none", ""):
            final_bg = _norm_color(footer_bg)
        else:
            final_bg = _norm_color(raw_bg)

        # Debug: log raw and normalized colors to trace invalid values
        try:
            logger.debug(f"PaymentControllerEfectivo raw_bg={raw_bg!r}, footer_bg={footer_bg!r}, final_bg={final_bg!r}, border={pc_colors.get('border')!r}")
        except Exception:
            pass

        super().__init__(
            parent,
            fg_color=final_bg,
            border_width=pc_layout.get("border_width", 3),
            border_color=_norm_color(pc_colors.get("border", "#2ecc71")),
            corner_radius=pc_layout.get("corner_radius", 18),
            **kwargs
        )

        self.total = total
        self.on_finalizar_callback = on_finalizar
        self.cantidad_entregada = 0.0

        # Crear UI
        self._create_widgets()

        logger.info("PaymentControllerEfectivo inicializado")

    def _create_widgets(self):
        """Crear widgets del controller."""
        # Obtener tokens de configuración para payment controllers
        pcfg = self.colors.get("tpv", {}).get("payment_controllers", {}).get("efectivo", {})
        fonts_cfg = self.fonts.get("modules", {}).get("tpv", {}).get("payment_controllers", {})
        layout_cfg = self.layout.get("modules", {}).get("tpv", {}).get("payment_controllers", {})

        # Fonts
        btn_font = (
            fonts_cfg.get("titulo", {}).get("family", "Courier New"),
            fonts_cfg.get("titulo", {}).get("size", 20),
            fonts_cfg.get("titulo", {}).get("weight", "bold")
        )

        entry_font = (
            fonts_cfg.get("entry", {}).get("family", "Courier New"),
            fonts_cfg.get("entry", {}).get("size", 16)
        )

        label_font = (
            fonts_cfg.get("label", {}).get("family", "Courier New"),
            fonts_cfg.get("label", {}).get("size", 14),
            fonts_cfg.get("label", {}).get("weight", "bold")
        )

        cambio_font = (
            fonts_cfg.get("cambio", {}).get("family", "Courier New"),
            fonts_cfg.get("cambio", {}).get("size", 18),
            fonts_cfg.get("cambio", {}).get("weight", "bold")
        )

        error_font = (
            fonts_cfg.get("error", {}).get("family", "Courier New"),
            fonts_cfg.get("error", {}).get("size", 12)
        )

        # Layout sizes
        entry_w = layout_cfg.get("efectivo", {}).get("entry_width", 112)
        entry_h = layout_cfg.get("efectivo", {}).get("entry_height", 40)
        btn_layout = layout_cfg.get("button", {})

        # Button colors
        btn_cfg = pcfg.get("button", {})
        # normalize button token colors
        btn_cfg = {k: _norm_color(v) if isinstance(v, str) else v for k, v in btn_cfg.items()}

        # Container principal
        main_container = ctk.CTkFrame(self, fg_color="transparent")
        main_container.pack(fill="both", expand=True, padx=layout_cfg.get("padding", 20), pady=layout_cfg.get("spacing", 12))

        # Leer espaciados específicos
        efectivo_cfg = layout_cfg.get("efectivo", {})

        # Título
        titulo = ctk.CTkLabel(
            main_container,
            text="PAGO EN EFECTIVO",
            font=btn_font,
            text_color=_norm_color(pcfg.get("text_titulo", "#2ecc71"))
        )
        titulo.pack(pady=(0, efectivo_cfg.get("titulo_bottom", 12)))

        # Grid 1×3
        grid_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        grid_frame.pack(fill="x", pady=(0, efectivo_cfg.get("grid_bottom", 8)))

        # Configurar columnas
        grid_frame.grid_columnconfigure(0, weight=0)
        grid_frame.grid_columnconfigure(1, weight=0)
        grid_frame.grid_columnconfigure(2, weight=1)

        # COLUMNA 1: Label "Entregado:"
        ctk.CTkLabel(
            grid_frame,
            text="Entregado:",
            font=label_font,
            text_color=_norm_color(pcfg.get("text_label", "#000000")),
            anchor="e"
        ).grid(row=0, column=0, sticky="e", padx=(0, efectivo_cfg.get("label_padx_right", 8)))

        # COLUMNA 2: Entry
        self.entry_cantidad = ctk.CTkEntry(
            grid_frame,
            width=entry_w,
            height=entry_h,
            font=entry_font,
            justify="center"
        )
        self.entry_cantidad.grid(row=0, column=1, padx=(0, efectivo_cfg.get("entry_padx_right", 12)))
        self.entry_cantidad.bind('<KeyRelease>', self._on_cantidad_change)
        self.entry_cantidad.bind('<Return>', lambda e: self._on_finalizar())
        self.entry_cantidad.bind('<Tab>', lambda e: (self.btn_finalizar.focus_set(), 'break'))

        # COLUMNA 3: Cambio
        self.cambio_label = ctk.CTkLabel(
            grid_frame,
            text=f"Cambio: 0.00€",
            font=cambio_font,
            text_color=_norm_color(pcfg.get("text_cambio", "#2ecc71")),
            anchor="e"
        )
        self.cambio_label.grid(row=0, column=2, sticky="e")

        # Label error
        self.error_label = ctk.CTkLabel(
            main_container,
            text="",
            font=error_font,
            text_color=_norm_color(pcfg.get("text_error", "#e74c3c")),
            anchor="center"
        )
        self.error_label.pack(pady=(efectivo_cfg.get("error_top", 4), efectivo_cfg.get("error_bottom", 8)))

        # Botón Finalizar
        btn_spacing_top = layout_cfg.get("button_spacing_top", 12)
        btn_spacing_bottom = layout_cfg.get("button_spacing_bottom", 8)

        self.btn_finalizar = ctk.CTkButton(
            main_container,
            text="FINALIZAR VENTA",
            command=self._on_finalizar,
            fg_color=btn_cfg.get("bg", "#2ecc71"),
            hover_color=btn_cfg.get("hover", "#27ae60"),
            text_color=_norm_color(btn_cfg.get("text", "#000000")),
            font=(btn_cfg.get("family", btn_font[0]), btn_cfg.get("size", btn_font[1])),
            width=btn_layout.get("width", 200),
            height=btn_layout.get("height", 45),
            corner_radius=btn_layout.get("corner_radius", 22),
            border_width=btn_layout.get("border_width", 2),
            border_color=_norm_color(btn_cfg.get("border", "#000000")),
            state="disabled"
        )
        self.btn_finalizar.pack(pady=(btn_spacing_top, btn_spacing_bottom))
        self.btn_finalizar.bind('<Tab>', lambda e: (self.entry_cantidad.focus_set(), 'break'))

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
