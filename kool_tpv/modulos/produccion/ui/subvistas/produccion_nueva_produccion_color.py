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
from kool_tpv.modulos.produccion.services.produccion_tallas_service import ProduccionTallasService
from kool_tpv.modulos.produccion.ui.subvistas.config_helper import cargar_config_produccion, get_font, get_chip_config, get_chip_style, get_nav_button_config, get_nav_button_style
from kool_tpv.utils.keyboard_nav_mixin import KeyboardNavigableMixin


class NuevaProduccionColorView(KeyboardNavigableMixin):
	"""Subvista para seleccionar el color.

	Args:
		parent: Widget padre donde se mostrará la subvista.
		db: Instancia de `Database` ya conectada.
		on_siguiente: Callback cuando se pulsa SIGUIENTE (recibe ProduccionColor).
		on_volver: Callback cuando se pulsa VOLVER.
	"""

	def __init__(self, parent, db: Database,
	             on_siguiente: Optional[Callable[[ProduccionColor], None]] = None,
	             on_volver: Optional[Callable] = None,
	             tipo_id: int = 0,
	             variante_id: Optional[int] = None):
		KeyboardNavigableMixin.__init_keyboard_mixin__(self)
		self.parent = parent
		self.db = db
		self.on_siguiente = on_siguiente
		self.on_volver = on_volver
		self._tipo_id = tipo_id
		self._variante_id = variante_id
		self.color_seleccionado: Optional[ProduccionColor] = None
		self._chip_buttons: List[ctk.CTkButton] = []
		self._selected_chip: Optional[ctk.CTkButton] = None

		# Servicio para cargar colores desde BD
		self._service = ProduccionColoresService(db)
		self._tallas_service = ProduccionTallasService(db)

		# Cargar configuración
		self.config = cargar_config_produccion()
		self._colors = self.config.get("colors", {})
		self._bg = self._colors.get("background", "#2c3e50")
		self._text = self._colors.get("text", "#ecf0f1")
		self._text_sec = self._colors.get("text_secondary", "#95a5a6")
		self._focus_border = self._colors.get("focus_border", "#FFD700")
		self._chip_cfg = get_chip_config(self.config, "color")

		# Frame principal
		self.frame = ctk.CTkFrame(parent, fg_color=self._bg)
		self.frame.pack(fill="both", expand=True)

		# Título + chips
		self._crear_titulo()
		self._crear_chips_colores()

		# Botones de navegación
		self._crear_botones_navegacion()

		# Configurar navegación con KeyboardNavigableMixin
		self._navigable_buttons = [
			(btn, lambda b=btn, c=getattr(btn, '_color_data', None): self._on_nav_enter_callback(b, c))
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

		# Cargar colores asignados al tipo/variante
		if self._tipo_id:
			colores = self._service.obtener_por_tipo_3d(self._tipo_id, self._variante_id)
		else:
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

		# Pre-calcular tallas disponibles por color para info de auto-asignación
		self._tallas_por_color = {}
		if self._tipo_id:
			for color in colores:
				try:
					tallas = self._tallas_service.obtener_por_tipo_color_3d(
						self._tipo_id, color.id, self._variante_id)
					if len(tallas) == 1:
						self._tallas_por_color[color.id] = tallas[0].nombre
				except Exception:
					pass

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
			bg_color = color.codigo_hex if color.codigo_hex else None
			text_color = self._calcular_texto_contraste(bg_color) if bg_color else None

			chip_cell = ctk.CTkFrame(self.chips_frame, fg_color=self._bg)
			row = idx // cols
			col = idx % cols
			chip_cell.grid(row=row, column=col, padx=padx, pady=pady, sticky="nsew")

			btn = ctk.CTkButton(
				master=chip_cell,
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
			btn.pack(fill="x")
			btn.bind("<Button-1>", lambda e, b=btn, c=color: self._on_chip_click(b, c))
			setattr(btn, "_color_data", color)
			self._chip_buttons.append(btn)

			if color.id in self._tallas_por_color:
				lbl = ctk.CTkLabel(
					chip_cell,
					text=f"Solo talla {self._tallas_por_color[color.id]} · auto-asignada",
					font=(self._get_font("label")[0], 10),
					text_color=self._text_sec,
					fg_color=self._bg
				)
				lbl.pack(pady=(2, 0))

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
		frame_nav = ctk.CTkFrame(self.frame, fg_color=self._bg)
		frame_nav.pack(fill="x", padx=40, pady=20)

		# Botón VOLVER
		nav_volver = get_nav_button_config(self.config, "volver")
		style_volver = get_nav_button_style(self.config, nav_volver.get("style_key", "volver"))
		self.btn_volver = ctk.CTkButton(
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
		self.btn_volver.pack(side=tk.LEFT, padx=10)

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

	def _on_nav_enter_callback(self, btn: ctk.CTkButton, color: Optional[ProduccionColor]):
		"""Manejar Enter desde el mixin: seleccionar o avanzar."""
		if self._selected_chip is not None and self._selected_chip == btn:
			if self.color_seleccionado and self.on_siguiente:
				self.on_siguiente(self.color_seleccionado)
		elif color is not None:
			self._select_chip(btn, color)

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
		self.clear_keyboard_navigation()
		self.frame.destroy()
