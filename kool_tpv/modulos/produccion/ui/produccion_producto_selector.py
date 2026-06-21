"""Widget selector de tipo de producto fabricable.

Contiene la clase `ProductoSelectorWidget` que muestra los tipos de producto
como chips cargados desde la base de datos (tabla `produccion_tipos`).

Soporta:
- Clic táctil (dedo) en cada chip.
- Navegación con Tab/Shift+Tab y Enter.
- Navegación con flechas direccionales.
"""
from typing import Callable, List, Optional

import customtkinter as ctk

from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.produccion.models.produccion_tipos_model import ProduccionTipo
from kool_tpv.modulos.produccion.services.produccion_tipos_service import ProduccionTiposService
from kool_tpv.modulos.produccion.ui.subvistas.config_helper import cargar_config_produccion, get_font, get_chip_config, get_chip_style


class ProductoSelectorWidget:
	"""Widget para seleccionar el tipo de producto fabricable.

	Args:
		parent: Widget padre donde se mostrará el selector.
		db: Instancia de `Database` ya conectada.
		on_seleccion: Callback cuando se selecciona un tipo (recibe ProduccionTipo).
		titulo: Título opcional del widget.
	"""

	def __init__(self, parent, db: Database,
	             on_seleccion: Optional[Callable[[ProduccionTipo], None]] = None,
	             titulo: str = "SELECCIONA PRODUCTO"):
		self.parent = parent
		self.db = db
		self.on_seleccion = on_seleccion
		self.titulo = titulo
		self.tipo_seleccionado: Optional[ProduccionTipo] = None
		self._chip_buttons: List[ctk.CTkButton] = []
		self._selected_chip: Optional[ctk.CTkButton] = None
		self._focused_index: int = -1

		# Servicio para cargar tipos desde BD
		self._service = ProduccionTiposService(db)

		# Cargar configuración
		self.config = cargar_config_produccion()
		self._colors = self.config.get("colors", {})
		self._bg = self._colors.get("background", "#2c3e50")
		self._text = self._colors.get("text", "#ecf0f1")
		self._text_sec = self._colors.get("text_secondary", "#95a5a6")
		self._chip_cfg = get_chip_config(self.config, "producto")

		# Frame principal
		self.frame = ctk.CTkFrame(parent, fg_color=self._bg)
		self.frame.pack(fill="both", expand=True)

		# Título
		self._crear_titulo()

		# Chips de tipos
		self._crear_chips_tipos()

		# Configurar navegación por teclado
		self._setup_keyboard_nav()

	def _crear_titulo(self):
		"""Crear el título del widget."""
		titulo = ctk.CTkLabel(
			self.frame,
			text=self.titulo,
			font=get_font(self.config, "title"),
			text_color=self._text,
			fg_color=self._bg
		)
		titulo.pack(pady=20)

	def _crear_chips_tipos(self):
		"""Crear los chips de tipos de producto cargados desde BD."""
		# Frame scrollable para los chips
		self.chips_frame = ctk.CTkScrollableFrame(
			self.frame,
			fg_color=self._bg,
			label_text=""
		)
		self.chips_frame.pack(expand=True, fill="both", padx=40, pady=20)

		# Cargar tipos activos desde BD
		tipos = self._service.obtener_activos()

		if not tipos:
			lbl_vacio = ctk.CTkLabel(
				self.chips_frame,
				text="No hay tipos de producto configurados",
				font=get_font(self.config, "label"),
				text_color=self._text_sec
			)
			lbl_vacio.pack(pady=40)
			return

		# Crear chips en grid
		cols = self._chip_cfg.get("columns", 4)
		padx = self._chip_cfg.get("padx", 8)
		pady = self._chip_cfg.get("pady", 8)
		chip_height = self._chip_cfg.get("height", 48)
		corner_radius = self._chip_cfg.get("corner_radius", 8)
		font_key = self._chip_cfg.get("font_key", "label")
		default_style = get_chip_style(self._chip_cfg, "default")
		font_family = get_font(self.config, font_key)
		chip_font = (font_family[0], default_style.get("font_size", 14), font_family[2])
		for idx, tipo in enumerate(tipos):
			btn = ctk.CTkButton(
				master=self.chips_frame,
				text=tipo.nombre,
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
			btn.bind("<Button-1>", lambda e, b=btn, t=tipo: self._on_chip_click(b, t))
			setattr(btn, "_tipo_data", tipo)
			self._chip_buttons.append(btn)

		# Configurar pesos del grid
		for i in range(cols):
			self.chips_frame.columnconfigure(i, weight=1)
		n_rows = (len(tipos) + cols - 1) // cols
		for i in range(n_rows):
			self.chips_frame.rowconfigure(i, weight=1)

	def _on_chip_click(self, btn: ctk.CTkButton, tipo: ProduccionTipo):
		"""Manejador del clic en un chip de tipo."""
		self._select_chip(btn, tipo)

	def _select_chip(self, btn: ctk.CTkButton, tipo: ProduccionTipo):
		"""Seleccionar un chip visualmente y guardar la selección."""
		# Deseleccionar el anterior
		if self._selected_chip is not None:
			try:
				self._apply_chip_style(self._selected_chip, "default")
			except Exception:
				pass

		# Seleccionar el nuevo
		self._selected_chip = btn
		self.tipo_seleccionado = tipo
		try:
			self._apply_chip_style(btn, "selected")
		except Exception:
			pass

		# Notificar selección
		if self.on_seleccion:
			self.on_seleccion(tipo)

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
		# Índice circular
		if index < 0:
			index = len(self._chip_buttons) - 1
		elif index >= len(self._chip_buttons):
			index = 0

		self._focused_index = index
		btn = self._chip_buttons[index]
		btn.focus_set()

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
			tipo = getattr(btn, "_tipo_data", None)
			if tipo is not None:
				self._select_chip(btn, tipo)
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

	def obtener_seleccion(self) -> Optional[ProduccionTipo]:
		"""Obtener el tipo seleccionado.

		Returns:
			Objeto ProduccionTipo o None si no hay selección.
		"""
		return self.tipo_seleccionado

	def destruir(self):
		"""Destruir el widget y limpiar recursos."""
		self._on_destroy()
		self.frame.destroy()