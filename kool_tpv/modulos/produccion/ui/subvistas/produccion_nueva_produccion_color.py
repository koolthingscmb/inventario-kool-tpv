"""Subvista de selección de color.

Contiene la clase `NuevaProduccionColorView` que muestra chips de colores
cargados desde la base de datos (tabla `produccion_colores`) y botones de
navegación (SIGUIENTE / VOLVER).
"""
import os
import tkinter as tk
from typing import Callable, List, Optional

import customtkinter as ctk

from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.produccion.models.produccion_color_model import ProduccionColor
from kool_tpv.modulos.produccion.services.produccion_colores_service import ProduccionColoresService
from kool_tpv.modulos.produccion.ui.subvistas.config_helper import cargar_config_produccion, get_font, get_chip_config, get_chip_style, get_nav_button_config, get_nav_button_style


class NuevaProduccionColorView:
	"""Subvista para seleccionar el color.

	Args:
		parent: Widget padre donde se mostrará la subvista.
		db: Instancia de `Database` ya conectada.
		on_siguiente: Callback cuando se pulsa SIGUIENTE (recibe ProduccionColor).
		on_volver: Callback cuando se pulsa VOLVER.
	"""

	def __init__(self, parent, db: Database,
	             on_siguiente: Optional[Callable[[ProduccionColor], None]] = None,
	             on_volver: Optional[Callable] = None):
		self.parent = parent
		self.db = db
		self.on_siguiente = on_siguiente
		self.on_volver = on_volver
		self.color_seleccionado: Optional[ProduccionColor] = None
		self._chip_buttons: List[ctk.CTkButton] = []
		self._selected_chip: Optional[ctk.CTkButton] = None
		self._focused_index: int = -1

		# Servicio para cargar colores desde BD
		self._service = ProduccionColoresService(db)

		# Cargar configuración
		self.config = cargar_config_produccion()
		self._colors = self.config.get("colors", {})
		self._bg = self._colors.get("background", "#2c3e50")
		self._text = self._colors.get("text", "#ecf0f1")
		self._text_sec = self._colors.get("text_secondary", "#95a5a6")
		self._focus_border = self._colors.get("focus_border", "#FFD700")
		self._chip_cfg = get_chip_config(self.config, "color")

		# Frame principal
		self.frame = tk.Frame(parent, bg=self._bg)
		self.frame.pack(fill=tk.BOTH, expand=True)

		# Título + chips
		self._crear_titulo()
		self._crear_chips_colores()

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
			text="SELECCIONA COLOR",
			font=self._get_font("title"),
			text_color=self._text,
			fg_color=self._bg
		)
		titulo.pack(pady=20)

	def _crear_chips_colores(self):
		"""Crear los chips de colores cargados desde BD."""
		self.chips_frame = ctk.CTkScrollableFrame(
			self.frame,
			fg_color=self._bg,
			label_text=""
		)
		self.chips_frame.pack(expand=True, fill="both", padx=40, pady=20)

		# Cargar colores activos desde BD
		colores = self._service.obtener_activos()

		if not colores:
			lbl_vacio = ctk.CTkLabel(
				self.chips_frame,
				text="No hay colores configurados",
				font=self._get_font("label"),
				text_color=self._text_sec
			)
			lbl_vacio.pack(pady=40)
			return

		cols = self._chip_cfg.get("columns", 4)
		padx = self._chip_cfg.get("padx", 8)
		pady = self._chip_cfg.get("pady", 8)
		chip_height = self._chip_cfg.get("height", 48)
		corner_radius = self._chip_cfg.get("corner_radius", 8)
		font_key = self._chip_cfg.get("font_key", "label")
		default_style = get_chip_style(self._chip_cfg, "default")
		font_family = get_font(self.config, font_key)
		chip_font = (font_family[0], default_style.get("font_size", 14), font_family[2])
		for idx, color in enumerate(colores):
			# Usar el hex del color como fondo del chip si está disponible
			bg_color = color.codigo_hex if color.codigo_hex else None
			text_color = self._calcular_texto_contraste(bg_color) if bg_color else None

			btn = ctk.CTkButton(
				master=self.chips_frame,
				text=color.nombre,
				fg_color=bg_color or default_style.get("bg", "#1a1a2e"),
				text_color=text_color or default_style.get("text", "#e0e0e0"),
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
			btn.bind("<Button-1>", lambda e, b=btn, c=color: self._on_chip_click(b, c))
			setattr(btn, "_color_data", color)
			self._chip_buttons.append(btn)

		# Pesos del grid
		for i in range(cols):
			self.chips_frame.columnconfigure(i, weight=1)
		n_rows = (len(colores) + cols - 1) // cols
		for i in range(n_rows):
			self.chips_frame.rowconfigure(i, weight=1)

	def _calcular_texto_contraste(self, hex_color: str) -> str:
		"""Calcular si el texto debe ser blanco o negro según el fondo."""
		try:
			h = hex_color.lstrip("#")
			r = int(h[0:2], 16)
			g = int(h[2:4], 16)
			b = int(h[4:6], 16)
			# Fórmula de luminancia relativa
			luminancia = (0.299 * r + 0.587 * g + 0.114 * b) / 255
			return "#000000" if luminancia > 0.5 else "#FFFFFF"
		except Exception:
			return "#FFFFFF"

	def _on_chip_click(self, btn: ctk.CTkButton, color: ProduccionColor):
		"""Manejador del clic en un chip de color."""
		self._select_chip(btn, color)

	def _select_chip(self, btn: ctk.CTkButton, color: ProduccionColor):
		"""Seleccionar un chip visualmente y guardar la selección."""
		# Restaurar chip anterior
		if self._selected_chip is not None:
			try:
				prev_color = getattr(self._selected_chip, "_color_data", None)
				if prev_color and prev_color.codigo_hex:
					# Restaurar con el color de fondo original
					prev_bg = prev_color.codigo_hex
					prev_text = self._calcular_texto_contraste(prev_bg)
					self._selected_chip.configure(
						fg_color=prev_bg,
						text_color=prev_text,
						border_width=2
					)
				else:
					self._apply_chip_style(self._selected_chip, "default")
			except Exception:
				pass

		# Seleccionar nuevo
		self._selected_chip = btn
		self.color_seleccionado = color
		try:
			# Resaltar con borde dorado manteniendo el color de fondo
			if color.codigo_hex:
				btn.configure(border_width=4, border_color=self._focus_border)
			else:
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
			color = getattr(btn, "_color_data", None)
			if color is not None:
				self._select_chip(btn, color)
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
			cols = self._chip_cfg.get("columns", 4)
			self._focus_chip(self._focused_index - cols if self._focused_index >= 0 else 0)
		return "break"

	def _on_arrow_down(self, event):
		if self._chip_buttons:
			cols = self._chip_cfg.get("columns", 4)
			self._focus_chip(self._focused_index + cols if self._focused_index >= 0 else 0)
		return "break"

	# --- Callbacks de navegación ---

	def _on_siguiente(self):
		"""Manejador del botón SIGUIENTE."""
		if self.color_seleccionado and self.on_siguiente:
			self.on_siguiente(self.color_seleccionado)

	def _on_volver(self):
		"""Manejador del botón VOLVER."""
		if self.on_volver:
			self.on_volver()

	def obtener_seleccion(self) -> Optional[ProduccionColor]:
		"""Obtener el color seleccionado.

		Returns:
			Objeto ProduccionColor o None.
		"""
		return self.color_seleccionado

	def destruir(self):
		"""Destruir la subvista y limpiar recursos."""
		self._on_destroy()
		self.frame.destroy()
