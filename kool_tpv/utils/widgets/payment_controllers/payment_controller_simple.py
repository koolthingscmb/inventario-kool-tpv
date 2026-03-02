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
        # Determinar key según tipo de pago
        tipo_key = "tarjeta" if tipo_pago.lower() == "tarjeta" else "web"

        # Leer configuración específica
        pc_colors = self.colors.get("tpv", {}).get("payment_controllers", {}).get(tipo_key, {})
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
            logger.debug(f"PaymentControllerSimple raw_bg={raw_bg!r}, footer_bg={footer_bg!r}, final_bg={final_bg!r}, border={pc_colors.get('border')!r}")
        except Exception:
            pass

        super().__init__(
            parent,
            fg_color=final_bg,
            border_width=pc_layout.get("border_width", 3),
            border_color=_norm_color(pc_colors.get("border", "#3498db")),
            corner_radius=pc_layout.get("corner_radius", 18),
            **kwargs
        )

        self.bg_active = self.cget("fg_color")

        self.tipo_pago = tipo_pago
        self.total = total
        self.on_finalizar_callback = on_finalizar

        # Crear UI
        self._create_widgets()

        logger.info(f"PaymentControllerSimple ({tipo_pago}) inicializado")

    def _create_widgets(self):
        """Crear widgets del controller."""
        # Obtener tokens según tipo de pago
        tp_key = "tarjeta" if self.tipo_pago.lower() == "tarjeta" else ("web" if self.tipo_pago.lower() == "web" else "simple")
        pcfg = self.colors.get("tpv", {}).get("payment_controllers", {}).get(tp_key, {})
        fonts_cfg = self.fonts.get("modules", {}).get("tpv", {}).get("payment_controllers", {})
        layout_cfg = self.layout.get("modules", {}).get("tpv", {}).get("payment_controllers", {})

        # Fonts and layout
        title_font = (
            fonts_cfg.get("titulo", {}).get("family", "Courier New"),
            fonts_cfg.get("titulo", {}).get("size", 20),
            fonts_cfg.get("titulo", {}).get("weight", "bold")
        )
        btn_layout = layout_cfg.get("button", {})
        btn_cfg = pcfg.get("button", {})

        # Container principal con padding
        main_container = ctk.CTkFrame(self, fg_color="transparent")
        main_container.pack(fill="both", expand=True,
            padx=layout_cfg.get("padding", 20),
            pady=layout_cfg.get("spacing", 12))

        # Label informativo según tipo de pago
        if self.tipo_pago.lower() == "tarjeta":
            texto_info = "Pago con tarjeta"
        elif self.tipo_pago.lower() == "web":
            texto_info = "Pago en la Web"
        else:
            texto_info = f"Pago: {self.tipo_pago}"

        def _choose_text_color(cfg_color: str, bg: str) -> str:
            c = _norm_color(cfg_color) if cfg_color else cfg_color
            if not c:
                return '#FFFFFF'
            if _norm_color(c) == _norm_color(bg):
                return '#FFFFFF'
            return c

        info_label = ctk.CTkLabel(
            main_container,
            text=texto_info,
            font=title_font,
            text_color=_choose_text_color(pcfg.get("text_titulo", "#FFFFFF"), self.bg_active)
        )
        simple_cfg = layout_cfg.get("simple", {})
        info_label.pack(pady=(0, simple_cfg.get("titulo_bottom", 8)))

        # normalize button cfg
        btn_cfg = pcfg.get("button", {})
        btn_cfg = {k: _norm_color(v) if isinstance(v, str) else v for k, v in btn_cfg.items()}

        # Botón Finalizar Venta
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
            border_color=_norm_color(btn_cfg.get("border", "#000000"))
        )
        btn_spacing_top = layout_cfg.get("button_spacing_top", 12)
        btn_spacing_bottom = layout_cfg.get("button_spacing_bottom", 8)

        self.btn_finalizar.pack(pady=(btn_spacing_top, btn_spacing_bottom))

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
