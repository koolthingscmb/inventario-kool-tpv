"""Subvista de selección de talla.

Contiene la clase `NuevaProduccionTallaView` que muestra chips de tallas
y botones de navegación (SIGUIENTE / VOLVER).
"""
import tkinter as tk
from typing import Callable, List, Optional

import customtkinter as ctk

from kool_tpv.modulos.produccion.ui.subvistas.config_helper import cargar_config_produccion, get_font, get_chip_config, get_chip_style, get_nav_button_config, get_nav_button_style
from kool_tpv.utils.keyboard_nav_mixin import KeyboardNavigableMixin

TALLAS = [
	{"codigo": "XS", "nombre": "XS"},
	{"codigo": "S", "nombre": "S"},
	{"codigo": "M", "nombre": "M"},
	{"codigo": "L", "nombre": "L"},
	{"codigo": "XL", "nombre": "XL"},
	{"codigo": "XXL", "nombre": "XXL"},
]


class NuevaProduccionTallaView(KeyboardNavigableMixin):
	"""Subvista para seleccionar la talla.

	Args:
		parent: Widget padre donde se mostrará la subvista.
		on_siguiente: Callback cuando se pulsa SIGUIENTE (recibe el código de talla).
		on_volver: Callback cuando se pulsa VOLVER.
		tallas_disponibles: Lista opcional de tallas disponibles.
		genero_nombre: Nombre del género para mostrar en el título.
	"""

	def __init__(self, parent,
	             on_siguiente: Optional[Callable[[str], None]] = None,
	             on_volver: Optional[Callable] = None,
	             tallas_disponibles: Optional[List[dict]] = None,
	             genero_nombre: Optional[str] = None):
		KeyboardNavigableMixin.__init_keyboard_mixin__(self)
		self.parent = parent
		self.on_siguiente = on_siguiente
		self.on_volver = on_volver
		self.talla_seleccionada: Optional[str] = None
		self.tallas = tallas_disponibles or TALLAS
		self._chip_buttons: List[ctk.CTkButton] = []
		self._selected_chip: Optional[ctk.CTkButton] = None
		self._genero_nombre = genero_nombre

		# Cargar configuración
		self.config = cargar_config_produccion()
		self._colors = self.config.get("colors", {})
		self._bg = self._colors.get("background", "#2c3e50")
		self._text = self._colors.get("text", "#ecf0f1")
		self._chip_cfg = get_chip_config(self.config, "talla")

		# Frame principal
		self.frame = ctk.CTkFrame(parent, fg_color=self._bg)
		self.frame.pack(fill="both", expand=True)

		# Título + chips
		self._crear_titulo()
		self._crear_chips_tallas()

		# Botones de navegación
		self._crear_botones_navegacion()

		# Configurar navegación con KeyboardNavigableMixin
		self._navigable_buttons = [
			(btn, lambda b=btn, t=getattr(btn, '_talla_codigo', None): self._on_nav_enter_callback(b, t))
			for btn in self._chip_buttons
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

		if self._chip_buttons:
			self.frame.after(100, lambda: self._focus_nav_widget(0))

	def _get_font(self, key: str) -> tuple:
		"""Obtener una fuente desde la configuración."""
		return get_font(self.config, key)

	def _crear_titulo(self):
		"""Crear el título de la subvista."""
		texto = "SELECCIONA TALLA"
		if self._genero_nombre:
			texto = f"SELECCIONA TALLA ({self._genero_nombre})"
		titulo = ctk.CTkLabel(
			self.frame,
			text=texto,
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
		frame_nav = ctk.CTkFrame(self.frame, fg_color=self._bg)
		frame_nav.pack(fill="x", padx=40, pady=20)

		# Botón VOLVER
		nav_volver = get_nav_button_config(self.config, "volver")
		style_volver = get_nav_button_style(self.config, nav_volver.get("style_key", "volver"))
		btn_volver = ctk.CTkButton(
			frame_nav,
			text=nav_volver.get("text", "VOLVER"),
			font=self._get_font(nav_volver.get("font_key", "button")),
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
		btn_volver.pack(side=tk.LEFT, padx=10)

		# Botón SIGUIENTE
		nav_sig = get_nav_button_config(self.config, "siguiente")
		style_siguiente = get_nav_button_style(self.config, nav_sig.get("style_key", "siguiente"))
		self.btn_siguiente = ctk.CTkButton(
			frame_nav,
			text=nav_sig.get("text", "SIGUIENTE"),
			font=self._get_font(nav_sig.get("font_key", "button")),
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

	# --- Callback para Enter desde KeyboardNavigableMixin ---

	def _on_nav_enter_callback(self, btn: ctk.CTkButton, talla_codigo: Optional[str]):
		"""Manejar Enter desde el mixin: seleccionar o avanzar."""
		if self._selected_chip is not None and self._selected_chip == btn:
			if self.talla_seleccionada and self.on_siguiente:
				self.on_siguiente(self.talla_seleccionada)
		elif talla_codigo is not None:
			self._select_chip(btn, talla_codigo)

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
		self.clear_keyboard_navigation()
		self.frame.destroy()
