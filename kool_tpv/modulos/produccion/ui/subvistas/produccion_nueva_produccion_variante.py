"""Subvista de selección de variante de tipo de producto.

Muestra chips de variantes cargados desde la base de datos para el tipo seleccionado.
"""
from typing import Callable, List, Optional

import tkinter as tk
import customtkinter as ctk

from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.produccion.models.produccion_tipo_variante_model import ProduccionTipoVariante
from kool_tpv.modulos.produccion.services.produccion_tipos_variantes_service import ProduccionTiposVariantesService
from kool_tpv.modulos.produccion.ui.subvistas.config_helper import cargar_config_produccion, get_font, get_chip_config, get_chip_style, get_nav_button_config, get_nav_button_style
from kool_tpv.utils.keyboard_nav_mixin import KeyboardNavigableMixin


class NuevaProduccionVarianteView(ctk.CTkFrame, KeyboardNavigableMixin):
    """Subvista para seleccionar la variante del tipo de producto.

    Args:
        parent: Widget padre.
        db: Instancia de Database.
        tipo_id: ID del tipo seleccionado para cargar sus variantes.
        on_siguiente: Callback cuando se selecciona variante (recibe ProduccionTipoVariante).
        on_volver: Callback para volver al paso anterior.
    """

    def __init__(self, parent, db: Database, tipo_id: int,
                 on_siguiente: Optional[Callable[[ProduccionTipoVariante], None]] = None,
                 on_volver: Optional[Callable] = None):
        KeyboardNavigableMixin.__init_keyboard_mixin__(self)
        self.parent = parent
        self.db = db
        self.tipo_id = tipo_id
        self.on_siguiente = on_siguiente
        self.on_volver = on_volver
        self.variante_seleccionada: Optional[ProduccionTipoVariante] = None
        self._chip_buttons: List[ctk.CTkButton] = []
        self._selected_chip: Optional[ctk.CTkButton] = None

        self._service = ProduccionTiposVariantesService(db)
        self.config = cargar_config_produccion()
        self._colors = self.config.get("colors", {})
        self._bg = self._colors.get("background", "#2c3e50")
        self._text = self._colors.get("text", "#ecf0f1")
        self._text_sec = self._colors.get("text_secondary", "#95a5a6")
        self._chip_cfg = get_chip_config(self.config, "producto")

        # Inicializar como CTkFrame
        ctk.CTkFrame.__init__(self, parent, fg_color=self._bg)
        self.pack(fill="both", expand=True)

        self._crear_titulo()
        self._crear_chips_variantes()
        self._crear_botones_navegacion()

        self._navigable_buttons = [
            (btn, lambda b=btn, v=getattr(btn, '_variante_data', None): self._on_nav_enter_callback(b, v))
            for btn in self._chip_buttons
        ]
        self._navigable_buttons.append((self.btn_volver, self._on_volver))
        self._navigable_buttons.append((self.btn_siguiente, self._on_siguiente))
        
        if self._navigable_buttons:
            self._setup_keyboard_navigation()

        if self._chip_buttons:
            self.after(100, lambda: self._focus_nav_widget(0))

    def _crear_titulo(self):
        titulo = ctk.CTkLabel(
            self,
            text="SELECCIONA VARIANTE",
            font=get_font(self.config, "title"),
            text_color=self._text,
            fg_color=self._bg
        )
        titulo.pack(pady=20)

    def _crear_chips_variantes(self):
        self.chips_frame = ctk.CTkScrollableFrame(self, fg_color=self._bg, label_text="")
        self.chips_frame.pack(expand=True, fill="both", padx=40, pady=20)

        variantes = self._service.obtener_por_tipo(self.tipo_id, solo_activos=True)

        if not variantes:
            lbl_vacio = ctk.CTkLabel(
                self.chips_frame,
                text="No hay variantes configuradas para este tipo",
                font=get_font(self.config, "label"),
                text_color=self._text_sec
            )
            lbl_vacio.pack(pady=40)
            return

        cols = self._chip_cfg.get("columns", 3)
        padx = self._chip_cfg.get("padx", 8)
        pady = self._chip_cfg.get("pady", 8)
        chip_height = self._chip_cfg.get("height", 48)
        corner_radius = self._chip_cfg.get("corner_radius", 8)
        font_key = self._chip_cfg.get("font_key", "label")
        default_style = get_chip_style(self._chip_cfg, "default")
        font_family = get_font(self.config, font_key)
        chip_font = (font_family[0], default_style.get("font_size", 14), font_family[2])

        for idx, var in enumerate(variantes):
            btn = ctk.CTkButton(
                master=self.chips_frame,
                text=var.nombre,
                fg_color=default_style.get("bg", "#1a1a2e"),
                text_color=default_style.get("text", "#e0e0e0"),
                border_color=default_style.get("border", "#552583"),
                hover_color=default_style.get("hover", "#C77BFF"),
                border_width=default_style.get("border_width", 1),
                corner_radius=corner_radius,
                height=chip_height,
                font=chip_font,
                cursor="hand2"
            )
            row = idx // cols
            col = idx % cols
            btn.grid(row=row, column=col, padx=padx, pady=pady, sticky="nsew")
            btn.bind("<Button-1>", lambda e, b=btn, v=var: self._on_chip_click(b, v))
            setattr(btn, "_variante_data", var)
            self._chip_buttons.append(btn)

        for i in range(cols):
            self.chips_frame.columnconfigure(i, weight=1)
        n_rows = (len(variantes) + cols - 1) // cols
        for i in range(n_rows):
            self.chips_frame.rowconfigure(i, weight=1)

    def _on_chip_click(self, btn: ctk.CTkButton, var: ProduccionTipoVariante):
        self._select_chip(btn, var)

    def _select_chip(self, btn: ctk.CTkButton, var: ProduccionTipoVariante):
        if self._selected_chip is not None:
            try:
                self._apply_chip_style(self._selected_chip, "default")
            except Exception:
                pass
        self._selected_chip = btn
        self.variante_seleccionada = var
        try:
            self._apply_chip_style(btn, "selected")
        except Exception:
            pass

    def _apply_chip_style(self, btn: ctk.CTkButton, state: str):
        style = get_chip_style(self._chip_cfg, state)
        font_key = self._chip_cfg.get("font_key", "label")
        font_family = get_font(self.config, font_key)
        btn.configure(
            fg_color=style.get("bg", "#1a1a2e"),
            text_color=style.get("text", "#e0e0e0"),
            border_color=style.get("border", "#552583"),
            hover_color=style.get("hover", "#C77BFF"),
            border_width=style.get("border_width", 1),
            font=(font_family[0], style.get("font_size", 14), font_family[2])
        )

    def _crear_botones_navegacion(self):
        """Crear los botones de navegación inferior."""
        frame_nav = ctk.CTkFrame(self, fg_color=self._bg)
        frame_nav.pack(fill="x", padx=40, pady=20)

        # Botón VOLVER
        nav_volver = get_nav_button_config(self.config, "volver")
        style_volver = get_nav_button_style(self.config, nav_volver.get("style_key", "volver"))
        self.btn_volver = ctk.CTkButton(
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
            command=self._on_volver
        )
        self.btn_volver.pack(side=tk.LEFT, padx=10)

        # Botón SIGUIENTE
        nav_sig = get_nav_button_config(self.config, "siguiente")
        style_siguiente = get_nav_button_style(self.config, nav_sig.get("style_key", "siguiente"))
        self.btn_siguiente = ctk.CTkButton(
            frame_nav,
            text=nav_sig.get("text", "SIGUIENTE"),
            font=get_font(self.config, nav_sig.get("font_key", "button")),
            fg_color=style_siguiente.get("bg", "#27ae60"),
            text_color=style_siguiente.get("text", "#FFFFFF"),
            hover_color=style_siguiente.get("hover", "#2ecc71"),
            border_color=style_siguiente.get("border", "#1C0629"),
            border_width=style_siguiente.get("focus_thickness", 0),
            width=nav_sig.get("width", 15) * 10,
            height=nav_sig.get("height", 2) * 20,
            cursor="hand2",
            command=self._on_siguiente
        )
        self.btn_siguiente.pack(side=tk.RIGHT, padx=10)

    def _on_volver(self):
        if self.on_volver:
            self.on_volver()

    def _on_siguiente(self):
        if self.variante_seleccionada and self.on_siguiente:
            self.on_siguiente(self.variante_seleccionada)

    def _on_nav_enter_callback(self, btn: ctk.CTkButton, var: Optional[ProduccionTipoVariante]):
        if self._selected_chip is not None and self._selected_chip == btn:
            if self.on_siguiente and self.variante_seleccionada:
                self.on_siguiente(self.variante_seleccionada)
        elif var is not None:
            self._select_chip(btn, var)

    def obtener_seleccion(self) -> Optional[ProduccionTipoVariante]:
        return self.variante_seleccionada

    def destruir(self):
        self.clear_keyboard_navigation()
        self.destroy()
