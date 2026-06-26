"""Paso 6: Entrada de SKU y cantidad + botones GUARDAR / OTRA VARIANTE.

Muestra un resumen de la selección acumulada (tipo, género, color, talla)
y dos entries para introducir el SKU de Shopify y la cantidad en almacén.
"""
from typing import Callable, Optional

import customtkinter as ctk
import tkinter as tk

from kool_tpv.modulos.produccion.ui.subvistas.config_helper import (
    cargar_config_produccion, get_font, get_nav_button_config, get_nav_button_style
)
from kool_tpv.utils.keyboard_nav_mixin import KeyboardNavigableMixin


class StockBaseStepFinal(KeyboardNavigableMixin):
    """Paso final: SKU + Cantidad + botones de acción.

    Args:
        parent: Widget padre.
        resumen: Texto con la selección acumulada (ej. "Camiseta Hombre Negro XL").
        on_guardar: Callback cuando se pulsa GUARDAR (recibe sku: str, cantidad: int).
        on_volver: Callback para volver al paso anterior (talla).
        on_otro: Callback para empezar otra variante (volver al paso 1).
    """

    def __init__(self, parent, resumen: str = "",
                 on_guardar: Optional[Callable[[str, int], None]] = None,
                 on_volver: Optional[Callable] = None,
                 on_otro: Optional[Callable] = None,
                 sku_inicial: Optional[str] = None,
                 cantidad_inicial: Optional[int] = None):
        KeyboardNavigableMixin.__init_keyboard_mixin__(self)
        self.parent = parent
        self.resumen = resumen
        self.on_guardar = on_guardar
        self.on_volver = on_volver
        self.on_otro = on_otro
        self._sku_inicial = sku_inicial
        self._cantidad_inicial = cantidad_inicial

        self.config = cargar_config_produccion()
        self._colors = self.config.get("colors", {})
        self._bg = self._colors.get("background", "#2c3e50")
        self._text = self._colors.get("text", "#ecf0f1")
        self._text_sec = self._colors.get("text_secondary", "#95a5a6")
        self._focus_border = self._colors.get("focus_border", "#C77BFF")

        self.frame = ctk.CTkFrame(parent, fg_color=self._bg)
        self.frame.pack(fill="both", expand=True)

        self._crear_titulo()
        self._crear_resumen()
        self._crear_formulario()
        self._crear_botones_navegacion()

        self._setup_keyboard_nav()

    def _crear_titulo(self):
        titulo = ctk.CTkLabel(
            self.frame,
            text="ENTRADA DE STOCK",
            font=get_font(self.config, "title"),
            text_color=self._text,
            fg_color=self._bg
        )
        titulo.pack(pady=20)

    def _crear_resumen(self):
        if self.resumen:
            lbl_resumen = ctk.CTkLabel(
                self.frame,
                text=self.resumen,
                font=get_font(self.config, "label"),
                text_color=self._focus_border,
                fg_color=self._bg
            )
            lbl_resumen.pack(pady=(0, 20))

    def _crear_formulario(self):
        form_frame = ctk.CTkFrame(self.frame, fg_color=self._bg)
        form_frame.pack(expand=True, pady=20)

        label_font = get_font(self.config, "label")
        entry_font = get_font(self.config, "entry")

        # SKU
        ctk.CTkLabel(
            form_frame,
            text="SKU SHOPIFY:",
            font=label_font,
            text_color=self._text,
            fg_color=self._bg
        ).grid(row=0, column=0, sticky="w", pady=(10, 0), padx=20)
        self.entry_sku = ctk.CTkEntry(
            form_frame,
            font=entry_font,
            height=40,
            width=400,
            placeholder_text="Introduce el SKU de Shopify..."
        )
        self.entry_sku.grid(row=1, column=0, sticky="we", pady=(0, 20), padx=20)
        if self._sku_inicial:
            self.entry_sku.insert(0, self._sku_inicial)
        self.entry_sku.focus_set()

        # Cantidad
        ctk.CTkLabel(
            form_frame,
            text="CANTIDAD EN ALMACÉN:",
            font=label_font,
            text_color=self._text,
            fg_color=self._bg
        ).grid(row=2, column=0, sticky="w", pady=(10, 0), padx=20)
        self.entry_cantidad = ctk.CTkEntry(
            form_frame,
            font=entry_font,
            height=40,
            width=400,
            placeholder_text="0"
        )
        self.entry_cantidad.grid(row=3, column=0, sticky="we", pady=(0, 30), padx=20)
        if self._cantidad_inicial is not None:
            self.entry_cantidad.insert(0, str(self._cantidad_inicial))

        # Enter en SKU → pasar a cantidad
        self.entry_sku.bind("<Return>", lambda e: self.entry_cantidad.focus_set())
        # Enter en cantidad → guardar
        self.entry_cantidad.bind("<Return>", lambda e: self._on_guardar())

    def _crear_botones_navegacion(self):
        frame_nav = ctk.CTkFrame(self.frame, fg_color=self._bg)
        frame_nav.pack(fill="x", padx=40, pady=20)

        # VOLVER
        nav_volver = get_nav_button_config(self.config, "volver")
        style_volver = get_nav_button_style(self.config, nav_volver.get("style_key", "volver"))
        btn_volver = ctk.CTkButton(
            frame_nav,
            text=nav_volver.get("text", "VOLVER"),
            font=get_font(self.config, nav_volver.get("font_key", "button")),
            fg_color=style_volver.get("bg", "#e74c3c"),
            text_color=style_volver.get("text", "#FFFFFF"),
            hover_color=style_volver.get("hover", "#c0392b"),
            border_color=style_volver.get("border", "#e74c3c"),
            border_width=style_volver.get("focus_thickness", 0),
            width=nav_volver.get("width", 15) * 10,
            height=nav_volver.get("height", 2) * 20,
            cursor="hand2",
            command=self._on_volver_click
        )
        btn_volver.pack(side=tk.LEFT, padx=10)

        # OTRA VARIANTE
        btn_otro = ctk.CTkButton(
            frame_nav,
            text="OTRA VARIANTE",
            font=get_font(self.config, "button"),
            fg_color="#552583",
            text_color="#FFFFFF",
            hover_color="#8e44ad",
            border_color="#C77BFF",
            border_width=0,
            width=150,
            height=40,
            cursor="hand2",
            command=self._on_otro_click
        )
        btn_otro.pack(side=tk.LEFT, padx=10)

        # GUARDAR
        nav_sig = get_nav_button_config(self.config, "confirmar")
        style_guardar = get_nav_button_style(self.config, nav_sig.get("style_key", "siguiente"))
        btn_guardar = ctk.CTkButton(
            frame_nav,
            text="GUARDAR",
            font=get_font(self.config, nav_sig.get("font_key", "button")),
            fg_color=style_guardar.get("bg", "#27ae60"),
            text_color=style_guardar.get("text", "#FFFFFF"),
            hover_color=style_guardar.get("hover", "#2ecc71"),
            border_color=style_guardar.get("border", "#1C0629"),
            border_width=style_guardar.get("focus_thickness", 0),
            width=nav_sig.get("width", 15) * 10,
            height=nav_sig.get("height", 2) * 20,
            cursor="hand2",
            command=self._on_guardar
        )
        btn_guardar.pack(side=tk.RIGHT, padx=10)

    def _setup_keyboard_nav(self):
        self._navigable_buttons = [
            (self.entry_sku, lambda b=self.entry_sku: self.entry_cantidad.focus_set()),
            (self.entry_cantidad, lambda b=self.entry_cantidad: self._on_guardar()),
        ]
        if self._navigable_buttons:
            try:
                self._nav_toplevel = self.frame.winfo_toplevel()
            except Exception:
                self._nav_toplevel = self.frame
            self._nav_toplevel.bind("<Tab>", self._on_nav_tab_next)
            self._nav_toplevel.bind("<Shift-Tab>", self._on_nav_tab_prev)
            self._nav_toplevel.bind("<Return>", self._on_nav_enter)
            self._nav_toplevel.bind("<KP_Enter>", self._on_nav_enter)
            self.frame.bind("<Destroy>", self._on_nav_destroy)

        self.frame.after(100, lambda: self._focus_nav_widget(0))

    def _on_guardar(self):
        sku = self.entry_sku.get().strip()
        try:
            cantidad = int(self.entry_cantidad.get())
        except ValueError:
            cantidad = 0

        if not sku:
            from kool_tpv.utils.widgets.notificaciones import ToastWidget
            ToastWidget.show(self.frame, 'DEBES INTRODUCIR UN SKU DE SHOPIFY', tipo='error')
            return

        if self.on_guardar:
            self.on_guardar(sku, cantidad)

    def _on_volver_click(self):
        if self.on_volver:
            self.on_volver()

    def _on_otro_click(self):
        if self.on_otro:
            self.on_otro()

    def destruir(self):
        self.clear_keyboard_navigation()
        self.frame.destroy()
