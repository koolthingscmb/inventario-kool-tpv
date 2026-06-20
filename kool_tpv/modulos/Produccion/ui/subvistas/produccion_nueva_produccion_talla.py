"""Subvista de selección de talla.

Contiene la clase `NuevaProduccionTallaView` que muestra chips de tallas
y botones de navegación (SIGUIENTE / VOLVER).
"""
import os
import tkinter as tk
from typing import Callable, List, Optional

import customtkinter as ctk

from kool_tpv.modulos.produccion.ui.subvistas.config_helper import cargar_config_produccion, get_font, get_chip_config, get_chip_style, get_nav_button_config, get_nav_button_style

TALLAS = [
	{"codigo": "XS", "nombre": "XS"},
	{"codigo": "S", "nombre": "S"},
	{"codigo": "M", "nombre": "M"},
	{"codigo": "L", "nombre": "L"},
	{"codigo": "XL", "nombre": "XL"},
	{"codigo": "XXL", "nombre": "XXL"},
]


class NuevaProduccionTallaView:
	"""Subvista para seleccionar la talla.

	Args:
		parent: Widget padre donde se mostrará la subvista.
		on_siguiente: Callback cuando se pulsa SIGUIENTE (recibe el código de talla).
		on_volver: Callback cuando se pulsa VOLVER.
		tallas_disponibles: Lista opcional de tallas disponibles.
	"""

	def __init__(self, parent,
	             on_siguiente: Optional[Callable[[str], None]] = None,
	             on_volver: Optional[Callable] = None,
	             tallas_disponibles: Optional[List[dict]] = None):
		self.parent = parent
		self.on_siguiente = on_siguiente
		self.on_volver = on_volver
		self.talla_seleccionada: Optional[str] = None
		self.tallas = tallas_disponibles or TALLAS
		self._chip_buttons: List[ctk.CTkButton] = []
		self._selected_chip: Optional[ctk.CTkButton] = None
		self._focused_index: int = -1

		# Cargar configuración
		self.config = cargar_config_produccion()
		self._colors = self.config.get("colors", {})
		self._bg = self._colors.get("background", "#2c3e50")
		self._text = self._colors.get("text", "#ecf0f1")
		self._chip_cfg = get_chip_config(self.config, "talla")

		# Frame principal
		self.frame = tk.Frame(parent, bg=self._bg)
		self.frame.pack(fill=tk.BOTH, expand=True)

		# Título + chips
		self._crear_titulo()
		self._crear_chips_tallas()

		# Botones de navegación
		self._crear_botones_navegacion()

		# Navegación por teclado
		self._setup_keyboard_nav()

	def _get_font(self, key: str) -> tuple:
		"""Obtener una fuente desde la configuración."""
		return get_font(self.config, key)

	def _crear_titulo(self):
		"""Crear el título de la subvista."""
		titulo = ctk.CTkLabel(
			self.frame,
			text="SELECCIONA TALLA",
			font=self._get_font("title"),
			text_color=self._text,
			fg_color=self._bg
		)
		titulo.pack(pady=20)

	def _crear_chips_tallas(self):
		"""Crear los chips de tallas."""
		self.chips_frame = ctk.CTkFrame(self.frame, fg_color=self._bg)
		self.chips_frame.pack(expand=True, fill="both", padx=40, pady=20)

		cols = self._chip_cfg.get("columns", 3)
		padx = self._chip_cfg.get("padx", 12)
		pady = self._chip_cfg.get("pady", 12)
		chip_height = self._chip_cfg.get("height", 48)
		corner_radius = self._chip_cfg.get("corner_radius", 8)
		font_key = self._chip_cfg.get("font_key", "label")
		default_style = get_chip_style(self._chip_cfg, "default")
		font_family = get_font(self.config, font_key)
		chip_font = (font_family[0], default_style.get("font_size", 14), font_family[2])
		for idx, talla in enumerate(self.tallas):
			btn = ctk.CTkButton(
				master=self.chips_frame,
				text=talla["nombre"],
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
			btn.bind("<Button-1>", lambda e, b=btn, t=talla["codigo"]: self._on_chip_click(b, t))
			setattr(btn, "_talla_codigo", talla["codigo"])
			self._chip_buttons.append(btn)

		# Pesos del grid
		for i in range(cols):
			self.chips_frame.columnconfigure(i, weight=1)
		n_rows = (len(self.tallas) + cols - 1) // cols
		for i in range(n_rows):
			self.chips_frame.rowconfigure(i, weight=1)

	def _on_chip_click(self, btn: ctk.CTkButton, talla_codigo: str):
		"""Manejador del clic en un chip de talla."""
		self._select_chip(btn, talla_codigo)

	def _select_chip(self, btn: ctk.CTkButton, talla_codigo: str):
		"""Seleccionar un chip visualmente y guardar la selección."""
		if self._selected_chip is not None:
			try:
				self._apply_chip_style(self._selected_chip, "default")
			except Exception:
				pass

		self._selected_chip = btn
		self.talla_seleccionada = talla_codigo
		try:
			self._apply_chip_style(btn, "selected")
		except Exception:
			pass

	def _apply_chip_style(self, btn: ctk.CTkButton, state: str):
		"""Aplicar estilo de color directo desde config al chip."""
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
		frame_nav = tk.Frame(self.frame, bg=self._bg)
		frame_nav.pack(fill=tk.X, padx=40, pady=20)

		# Botón VOLVER
		nav_volver = get_nav_button_config(self.config, "volver")
		style_volver = get_nav_button_style(self.config, nav_volver.get("style_key", "volver"))
		btn_volver = tk.Button(
			frame_nav,
			text=nav_volver.get("text", "VOLVER"),
			font=self._get_font(nav_volver.get("font_key", "button")),
			bg=style_volver.get("bg", "#e74c3c"),
			fg=style_volver.get("text", "#FFFFFF"),
			activebackground=style_volver.get("hover", "#c0392b"),
			activeforeground=style_volver.get("text", "#FFFFFF"),
			takefocus=True,
			bd=nav_volver.get("bd", 0),
			width=nav_volver.get("width", 15),
			height=nav_volver.get("height", 2),
			command=self._on_volver
		)
		btn_volver.pack(side=tk.LEFT, padx=10)

		# Botón SIGUIENTE
		nav_sig = get_nav_button_config(self.config, "siguiente")
		style_siguiente = get_nav_button_style(self.config, nav_sig.get("style_key", "siguiente"))
		self.btn_siguiente = tk.Button(
			frame_nav,
			text=nav_sig.get("text", "SIGUIENTE"),
			font=self._get_font(nav_sig.get("font_key", "button")),
			bg=style_siguiente.get("bg", "#27ae60"),
			fg=style_siguiente.get("text", "#FFFFFF"),
			activebackground=style_siguiente.get("hover", "#2ecc71"),
			activeforeground=style_siguiente.get("text", "#FFFFFF"),
			takefocus=True,
			bd=nav_sig.get("bd", 0),
			width=nav_sig.get("width", 15),
			height=nav_sig.get("height", 2),
			command=self._on_siguiente
		)
		self.btn_siguiente.pack(side=tk.RIGHT, padx=10)

	# --- Navegación por teclado ---

	def _setup_keyboard_nav(self):
		"""Configurar bindings de navegación por teclado."""
		toplevel = self.frame.winfo_toplevel()
		toplevel.bind("<Tab>", self._on_tab_next)
		toplevel.bind("<Shift-Tab>", self._on_tab_prev)
		toplevel.bind("<Return>", self._on_enter)
		toplevel.bind("<KP_Enter>", self._on_enter)
		toplevel.bind("<Left>", self._on_arrow_left)
		toplevel.bind("<Right>", self._on_arrow_right)
		toplevel.bind("<Up>", self._on_arrow_up)
		toplevel.bind("<Down>", self._on_arrow_down)

		self.frame.bind("<Destroy>", self._on_destroy)

	def _on_destroy(self, event=None):
		"""Limpiar bindings al destruir."""
		try:
			toplevel = self.frame.winfo_toplevel()
			for key in ("<Tab>", "<Shift-Tab>", "<Return>", "<KP_Enter>",
			            "<Left>", "<Right>", "<Up>", "<Down>"):
				toplevel.unbind(key)
		except Exception:
			pass

	def _focus_chip(self, index: int):
		"""Aplicar foco visual a un chip por índice."""
		if not self._chip_buttons:
			return
		if index < 0:
			index = len(self._chip_buttons) - 1
		elif index >= len(self._chip_buttons):
			index = 0

		self._focused_index = index
		self._chip_buttons[index].focus_set()

	def _on_tab_next(self, event):
		if not self._chip_buttons:
			return "break"
		next_idx = self._focused_index + 1 if self._focused_index >= 0 else 0
		self._focus_chip(next_idx)
		return "break"

	def _on_tab_prev(self, event):
		if not self._chip_buttons:
			return "break"
		prev_idx = self._focused_index - 1 if self._focused_index >= 0 else len(self._chip_buttons) - 1
		self._focus_chip(prev_idx)
		return "break"

	def _on_enter(self, event):
		if 0 <= self._focused_index < len(self._chip_buttons):
			btn = self._chip_buttons[self._focused_index]
			talla = getattr(btn, "_talla_codigo", None)
			if talla is not None:
				self._select_chip(btn, talla)
		return "break"

	def _on_arrow_left(self, event):
		if self._chip_buttons:
			self._focus_chip(self._focused_index - 1 if self._focused_index >= 0 else 0)
		return "break"

	def _on_arrow_right(self, event):
		if self._chip_buttons:
			self._focus_chip(self._focused_index + 1 if self._focused_index >= 0 else 0)
		return "break"

	def _on_arrow_up(self, event):
		if self._chip_buttons:
			cols = self._chip_cfg.get("columns", 3)
			self._focus_chip(self._focused_index - cols if self._focused_index >= 0 else 0)
		return "break"

	def _on_arrow_down(self, event):
		if self._chip_buttons:
			cols = self._chip_cfg.get("columns", 3)
			self._focus_chip(self._focused_index + cols if self._focused_index >= 0 else 0)
		return "break"

	# --- Callbacks de navegación ---

	def _on_siguiente(self):
		"""Manejador del botón SIGUIENTE."""
		if self.talla_seleccionada and self.on_siguiente:
			self.on_siguiente(self.talla_seleccionada)

	def _on_volver(self):
		"""Manejador del botón VOLVER."""
		if self.on_volver:
			self.on_volver()

	def obtener_seleccion(self) -> Optional[str]:
		"""Obtener la talla seleccionada.

		Returns:
			Código de la talla seleccionada o None.
		"""
		return self.talla_seleccionada

	def destruir(self):
		"""Destruir la subvista y limpiar recursos."""
		self._on_destroy()
		self.frame.destroy()
