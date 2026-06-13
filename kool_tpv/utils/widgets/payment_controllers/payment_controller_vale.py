"""PaymentControllerVale - Widget para vales de devolucion."""
import logging
import customtkinter as ctk
from typing import Optional, Callable, Dict
from . import PaymentConfigHelper, load_config, norm_color
from kool_tpv.modulos.tpv.vale_devolucion_service import ValeDevolucionService
from kool_tpv.base_datos.money_adapter import read_from_db

logger = logging.getLogger(__name__)


def _resolve_token(tokens, token, fallback):
    for section in tokens.values():
        if isinstance(section, dict) and token in section:
            return norm_color(section[token])
    return fallback


class PaymentControllerVale(ctk.CTkFrame):
    """Muestra vales activos y permite aplicarlos al carrito."""

    def __init__(self, parent, total=0.0, on_usar_vale=None, on_omitir=None, **kwargs):
        self.tokens = load_config("design_tokens.json")
        self.btn_styles = load_config("button_styles.json")
        self.config_helper = PaymentConfigHelper("efectivo")

        super().__init__(
            parent,
            fg_color=self.config_helper.get_bg_color(),
            border_width=self.config_helper.get_layout_value("border_width") or 5,
            border_color=_resolve_token(self.tokens, "green_success", "#2ecc71"),
            corner_radius=self.config_helper.get_layout_value("corner_radius") or 18,
            **kwargs
        )

        self.total = total
        self.on_usar_vale_callback = on_usar_vale
        self.on_omitir_callback = on_omitir
        self.vale_service = ValeDevolucionService()
        self._vale_seleccionado = None

        self._create_widgets()
        logger.info("PaymentControllerVale inicializado")

    def _create_widgets(self):
        tf = self.config_helper.get_font("titulo")
        bf = self.config_helper.get_font("button")
        lf = self.config_helper.get_font("label")
        p = self.config_helper.get_layout_value("padding") or 20
        s = self.config_helper.get_layout_value("spacing") or 12
        tb = self.config_helper.get_layout_value("titulo_bottom") or 12
        bw = self.config_helper.get_layout_value("button", "width") or 200
        bh = self.config_helper.get_layout_value("button", "height") or 45
        br = self.config_helper.get_layout_value("button", "corner_radius") or 22
        bb = self.config_helper.get_layout_value("button", "border_width") or 2

        mc = ctk.CTkFrame(self, fg_color="transparent")
        mc.pack(fill="both", expand=True, padx=p, pady=s)

        ctk.CTkLabel(mc, text="VALE DE DEVOLUCION", font=tf,
                     text_color=self.config_helper.get_color("text_titulo")).pack(pady=(0, tb))

        self._info_label = ctk.CTkLabel(mc, text="", font=lf,
                                        text_color=self.config_helper.get_color("text_label"))
        self._info_label.pack(pady=(0, 10))

        bf_ = ctk.CTkFrame(mc, fg_color="transparent")
        bf_.pack(fill="x", pady=(10, 0))

        self._btn_usar = ctk.CTkButton(
            bf_, text="USAR VALE", command=self._on_usar_vale,
            fg_color=_resolve_token(self.tokens, "green_success", "#2ecc71"),
            hover_color=_resolve_token(self.tokens, "green_hover", "#27ae60"),
            text_color="#FFFFFF", font=bf, width=bw, height=bh,
            corner_radius=br, border_width=bb)
        self._btn_usar.pack(side="left", expand=True, padx=(0, 5))

        self._btn_omitir = ctk.CTkButton(
            bf_, text="OMITIR", command=self._on_omitir,
            fg_color="#95a5a6", hover_color="#7f8c8d",
            text_color="#FFFFFF", font=bf, width=bw, height=bh,
            corner_radius=br, border_width=bb)
        self._btn_omitir.pack(side="right", expand=True, padx=(5, 0))

        self._cargar_vales()

    def _cargar_vales(self):
        try:
            vales = self.vale_service.listar_activos()
            if not vales:
                self._info_label.configure(text="No hay vales disponibles")
                self._btn_usar.configure(state="disabled")
                self._vale_seleccionado = None
                return
            vale = vales[0]
            self._vale_seleccionado = vale
            imp = read_from_db(vale.get("importe_cents", 0))
            fecha = vale.get("fecha", "").split("T")[0]
            # Mostrar nombre de archivo legible si existe, sino fallback a ticket
            path_str = vale.get("path", "")
            nombre_vale = path_str.split("/")[-1].replace(".json", "") if path_str else None
            if not nombre_vale:
                nombre_vale = vale.get("num_ticket_devolucion", "?")
            txt = f"{nombre_vale} - {imp:.2f} E ({fecha})"
            if len(vales) > 1:
                txt += f"\n(+{len(vales)-1} mas)"
            self._info_label.configure(text=txt)
            self._btn_usar.configure(state="normal")
        except Exception:
            logger.exception("Error cargando vales")
            self._info_label.configure(text="Error cargando vales")
            self._btn_usar.configure(state="disabled")

    def _on_usar_vale(self):
        try:
            if not self._vale_seleccionado:
                return
            if self.on_usar_vale_callback:
                self.on_usar_vale_callback(self._vale_seleccionado)
            logger.info(f"Vale aplicado: {self._vale_seleccionado.get('id')}")
        except Exception:
            logger.exception("Error en _on_usar_vale")

    def _on_omitir(self):
        try:
            if self.on_omitir_callback:
                self.on_omitir_callback()
            logger.info("Vale omitido")
        except Exception:
            logger.exception("Error en _on_omitir")

    def set_total(self, total: float):
        self.total = total

    def recargar_vales(self):
        """Recarga la lista de vales (para llamar desde fuera)."""
        self._cargar_vales()
