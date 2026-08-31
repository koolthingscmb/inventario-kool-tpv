"""Subvista de selección de origen (KOOL / CUSTOM).

Contiene la clase `NuevaProduccionOrigenView` que muestra dos chips
y botones de navegación (SIGUIENTE / VOLVER).
"""
import tkinter as tk
from typing import Callable, Optional

import customtkinter as ctk

from kool_tpv.modulos.produccion.ui.subvistas.config_helper import cargar_config_produccion, get_font, get_chip_config, get_chip_style, get_nav_button_config, get_nav_button_style
from kool_tpv.utils.keyboard_nav_mixin import KeyboardNavigableMixin
from kool_tpv.utils.factories.button_factory import ButtonFactory

OPCIONES = [
	{"codigo": "KOOL", "nombre": "KOOL"},
	{"codigo": "CUSTOM", "nombre": "CUSTOM"},
]


class NuevaProduccionOrigenView(KeyboardNavigableMixin):
	"""Subvista para seleccionar el origen de la producción.

	Args:
		parent: Widget padre donde se mostrará la subvista.
		on_siguiente: Callback cuando se pulsa SIGUIENTE (recibe el código de origen).
		on_volver: Callback cuando se pulsa VOLVER.
	"""

	def __init__(self, parent,
	             on_siguiente: Optional[Callable[[str], None]] = None,
	             on_volver: Optional[Callable] = None):
		KeyboardNavigableMixin.__init_keyboard_mixin__(self)
		self.parent = parent
		self.on_siguiente = on_siguiente
		self.on_volver = on_volver
		self.origen_seleccionado: Optional[str] = None
		self._chip_buttons = []
		self._selected_chip: Optional[ctk.CTkButton] = None

		# Cargar configuración
		self.config = cargar_config_produccion()
		self._colors = self.config.get("colors", {})
		self._bg = self._colors.get("background", "#2c3e50")
		self._text = self._colors.get("text", "#ecf0f1")
		self._chip_cfg = get_chip_config(self.config, "producto")

		# Frame principal
		self.frame = ctk.CTkFrame(parent, fg_color=self._bg)
		self.frame.pack(fill="both", expand=True)

		# Título + chips
		self._crear_titulo()
		self._crear_chips()

		# Botones de navegación
		self._crear_botones_navegacion()

		# Configurar navegación con KeyboardNavigableMixin
		self._navigable_buttons = [
			(btn, lambda b=btn, c=getattr(btn, '_origen_codigo', None): self._on_nav_enter_callback(b, c))
			for btn in self._chip_buttons
		]
		self._navigable_buttons.append((self.btn_volver, self._on_volver))
		self._navigable_buttons.append((self.btn_siguiente, self._on_siguiente))
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

		if self._chip_buttons:
			self.frame.after(100, lambda: self._focus_nav_widget(0))

	def _get_font(self, key: str) -> tuple:
		return get_font(self.config, key)

	def _crear_titulo(self):
		titulo = ctk.CTkLabel(
			self.frame,
			text="SELECCIONA ORIGEN",
			font=self._get_font("title"),
			text_color=self._text,
			fg_color=self._bg
		)
		titulo.pack(pady=20)

	def _crear_chips(self):
		self.chips_frame = ctk.CTkFrame(self.frame, fg_color=self._bg)
		self.chips_frame.pack(expand=True, fill="both", padx=40, pady=20)

		cols = 2
		padx = self._chip_cfg.get("padx", 12)
		pady = self._chip_cfg.get("pady", 12)
		chip_height = self._chip_cfg.get("height", 48)
		corner_radius = self._chip_cfg.get("corner_radius", 8)
		font_key = self._chip_cfg.get("font_key", "label")
		default_style = get_chip_style(self._chip_cfg, "default")
		font_family = get_font(self.config, font_key)
		chip_font = (font_family[0], default_style.get("font_size", 14), font_family[2])

		for idx, opcion in enumerate(OPCIONES):
			btn = ctk.CTkButton(
				master=self.chips_frame,
				text=opcion["nombre"],
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
			btn.bind("<Button-1>", lambda e, b=btn, c=opcion["codigo"]: self._on_chip_click(b, c))
			setattr(btn, "_origen_codigo", opcion["codigo"])
			self._chip_buttons.append(btn)

		for i in range(cols):
			self.chips_frame.columnconfigure(i, weight=1)

	def _on_chip_click(self, btn: ctk.CTkButton, codigo: str):
		self._select_chip(btn, codigo)

	def _select_chip(self, btn: ctk.CTkButton, codigo: str):
		if self._selected_chip is not None:
			try:
				self._apply_chip_style(self._selected_chip, "default")
			except Exception:
				pass
		self._selected_chip = btn
		self.origen_seleccionado = codigo
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
		frame_nav = ctk.CTkFrame(self.frame, fg_color=self._bg)
		frame_nav.pack(fill="x", padx=40, pady=20)

				# Botón VOLVER
		nav_volver = get_nav_button_config(self.config, "volver")
		self.btn_volver = ButtonFactory.create_button(
			parent=frame_nav,
			text=nav_volver.get("text", "VOLVER"),
			command=self._on_volver,
			width=nav_volver.get("width", 15) * 10,
			height=nav_volver.get("height", 2) * 20,
			font=self._get_font(nav_volver.get("font_key", "button")),
			style_key="action_confirm",
			module="produccion",
			palette_key="primary",
			cursor="hand2"
		)
		self.btn_volver.pack(side=tk.LEFT, padx=10)

				# Botón SIGUIENTE
		nav_sig = get_nav_button_config(self.config, "siguiente")
		self.btn_siguiente = ButtonFactory.create_button(
			parent=frame_nav,
			text=nav_sig.get("text", "SIGUIENTE"),
			command=self._on_siguiente,
			width=nav_sig.get("width", 15) * 10,
			height=nav_sig.get("height", 2) * 20,
			font=self._get_font(nav_sig.get("font_key", "button")),
			style_key="action_confirm",
			module="produccion",
			palette_key="primary",
			cursor="hand2"
		)
		self.btn_siguiente.pack(side=tk.RIGHT, padx=10)

	def _on_nav_enter_callback(self, btn: ctk.CTkButton, codigo: Optional[str]):
		if self._selected_chip is not None and self._selected_chip == btn:
			if self.origen_seleccionado and self.on_siguiente:
				self.on_siguiente(self.origen_seleccionado)
		elif codigo is not None:
			self._select_chip(btn, codigo)

	def _on_siguiente(self):
		if self.origen_seleccionado and self.on_siguiente:
			self.on_siguiente(self.origen_seleccionado)

	def _on_volver(self):
		if self.on_volver:
			self.on_volver()

	def destruir(self):
		self.clear_keyboard_navigation()
		self.frame.destroy()
