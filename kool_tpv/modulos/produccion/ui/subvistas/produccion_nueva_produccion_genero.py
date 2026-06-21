"""Subvista de selección de género.

Contiene la clase `NuevaProduccionGeneroView` que muestra chips de géneros
cargados desde la base de datos según el tipo de producto seleccionado.
"""
from typing import Callable, List, Optional

import customtkinter as ctk

from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.produccion.models.produccion_genero_model import ProduccionGenero
from kool_tpv.modulos.produccion.services.produccion_generos_tallas_service import ProduccionGenerosService
from kool_tpv.modulos.produccion.ui.subvistas.config_helper import cargar_config_produccion, get_font, get_chip_config, get_chip_style
from kool_tpv.utils.keyboard_nav_mixin import KeyboardNavigableMixin


class NuevaProduccionGeneroView(KeyboardNavigableMixin):
	"""Subvista para seleccionar el género del producto.

	Args:
		parent: Widget padre.
		db: Instancia de Database.
		tipo_id: ID del tipo de producto para cargar sus géneros.
		on_siguiente: Callback cuando se selecciona género (recibe ProduccionGenero).
		on_volver: Callback para volver al paso anterior.
	"""

	def __init__(self, parent, db: Database, tipo_id: int,
	             on_siguiente: Optional[Callable[[ProduccionGenero], None]] = None,
	             on_volver: Optional[Callable] = None):
		KeyboardNavigableMixin.__init_keyboard_mixin__(self)
		self.parent = parent
		self.db = db
		self.tipo_id = tipo_id
		self.on_siguiente = on_siguiente
		self.on_volver = on_volver
		self.genero_seleccionado: Optional[ProduccionGenero] = None
		self._chip_buttons: List[ctk.CTkButton] = []
		self._selected_chip: Optional[ctk.CTkButton] = None

		self._service = ProduccionGenerosService(db)
		self.config = cargar_config_produccion()
		self._colors = self.config.get("colors", {})
		self._bg = self._colors.get("background", "#2c3e50")
		self._text = self._colors.get("text", "#ecf0f1")
		self._text_sec = self._colors.get("text_secondary", "#95a5a6")
		self._chip_cfg = get_chip_config(self.config, "producto")

		self.frame = ctk.CTkFrame(parent, fg_color=self._bg)
		self.frame.pack(fill="both", expand=True)

		self._crear_titulo()
		self._crear_chips_generos()

		self._navigable_buttons = [
			(btn, lambda b=btn, g=getattr(btn, '_genero_data', None): self._on_nav_enter_callback(b, g))
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

	def _crear_titulo(self):
		titulo = ctk.CTkLabel(
			self.frame,
			text="SELECCIONA GÉNERO",
			font=get_font(self.config, "title"),
			text_color=self._text,
			fg_color=self._bg
		)
		titulo.pack(pady=20)

	def _crear_chips_generos(self):
		self.chips_frame = ctk.CTkScrollableFrame(self.frame, fg_color=self._bg, label_text="")
		self.chips_frame.pack(expand=True, fill="both", padx=40, pady=20)

		generos = self._service.obtener_por_tipo(self.tipo_id)

		if not generos:
			lbl_vacio = ctk.CTkLabel(
				self.chips_frame,
				text="No hay géneros configurados para este tipo",
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

		for idx, genero in enumerate(generos):
			btn = ctk.CTkButton(
				master=self.chips_frame,
				text=genero.nombre,
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
			btn.bind("<Button-1>", lambda e, b=btn, g=genero: self._on_chip_click(b, g))
			setattr(btn, "_genero_data", genero)
			self._chip_buttons.append(btn)

		for i in range(cols):
			self.chips_frame.columnconfigure(i, weight=1)
		n_rows = (len(generos) + cols - 1) // cols
		for i in range(n_rows):
			self.chips_frame.rowconfigure(i, weight=1)

	def _on_chip_click(self, btn: ctk.CTkButton, genero: ProduccionGenero):
		self._select_chip(btn, genero)

	def _select_chip(self, btn: ctk.CTkButton, genero: ProduccionGenero):
		if self._selected_chip is not None:
			try:
				self._apply_chip_style(self._selected_chip, "default")
			except Exception:
				pass
		self._selected_chip = btn
		self.genero_seleccionado = genero
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

	def _on_nav_enter_callback(self, btn: ctk.CTkButton, genero: Optional[ProduccionGenero]):
		if self._selected_chip is not None and self._selected_chip == btn:
			if self.on_siguiente and self.genero_seleccionado:
				self.on_siguiente(self.genero_seleccionado)
		elif genero is not None:
			self._select_chip(btn, genero)

	def obtener_seleccion(self) -> Optional[ProduccionGenero]:
		return self.genero_seleccionado

	def destruir(self):
		self.clear_keyboard_navigation()
		self.frame.destroy()
