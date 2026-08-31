"""Subvista de selección de tipo de producto (tras elegir menú).

Contiene la clase `NuevaProduccionTiposView` que muestra chips de tipos
cargados desde la base de datos según el menú seleccionado.
"""
from typing import Callable, List, Optional, Dict

import customtkinter as ctk

from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.produccion.models.produccion_tipos_model import ProduccionTipo
from kool_tpv.modulos.produccion.services.produccion_menu_service import ProduccionMenuService
from kool_tpv.modulos.produccion.ui.subvistas.config_helper import cargar_config_produccion, get_font, get_chip_config, get_chip_style, get_nav_button_config
from kool_tpv.utils.keyboard_nav_mixin import KeyboardNavigableMixin
from kool_tpv.utils.factories.button_factory import ButtonFactory


class NuevaProduccionTiposView(ctk.CTkFrame, KeyboardNavigableMixin):
	"""Subvista para seleccionar el tipo de producto tras elegir un menú.

	Args:
		parent: Widget padre.
		db: Instancia de Database.
		menu_id: ID del menú seleccionado para cargar sus tipos.
		on_siguiente: Callback cuando se selecciona tipo (recibe ProduccionTipo).
		on_volver: Callback para volver al paso anterior.
	"""

	def __init__(self, parent, db: Database, menu_id: int,
	             on_siguiente: Optional[Callable[[ProduccionTipo], None]] = None,
	             on_volver: Optional[Callable] = None):
		KeyboardNavigableMixin.__init_keyboard_mixin__(self)
		self.parent = parent
		self.db = db
		self.menu_id = menu_id
		self.on_siguiente = on_siguiente
		self.on_volver = on_volver
		self.tipo_seleccionado: Optional[ProduccionTipo] = None
		self._chip_buttons: List[ctk.CTkButton] = []
		self._selected_chip: Optional[ctk.CTkButton] = None

		self._service = ProduccionMenuService(db)
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
		self._crear_chips_tipos()
		self._crear_botones_navegacion()

		self._navigable_buttons = [
			(btn, lambda b=btn, t=getattr(btn, '_tipo_data', None): self._on_nav_enter_callback(b, t))
			for btn in self._chip_buttons
		]
		self._navigable_buttons.append((self.btn_volver, self._on_volver_handler))
		self._navigable_buttons.append((self.btn_siguiente, self._on_siguiente_handler))
		
		if self._navigable_buttons:
			self._setup_keyboard_navigation()

		if self._chip_buttons:
			self.after(100, lambda: self._focus_nav_widget(0))

	def _crear_titulo(self):
		titulo = ctk.CTkLabel(
			self,
			text="SELECCIONA TIPO",
			font=get_font(self.config, "title"),
			text_color=self._text,
			fg_color=self._bg
		)
		titulo.pack(pady=20)

	def _crear_chips_tipos(self):
		self.chips_frame = ctk.CTkScrollableFrame(self, fg_color=self._bg, label_text="")
		self.chips_frame.pack(expand=True, fill="both", padx=40, pady=20)

		tipos = self._service.obtener_tipos_por_menu(self.menu_id)

		if not tipos:
			lbl_vacio = ctk.CTkLabel(
				self.chips_frame,
				text="No hay tipos configurados para este menú",
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

		for i in range(cols):
			self.chips_frame.columnconfigure(i, weight=1)
		n_rows = (len(tipos) + cols - 1) // cols
		for i in range(n_rows):
			self.chips_frame.rowconfigure(i, weight=1)

	def _on_chip_click(self, btn: ctk.CTkButton, tipo: ProduccionTipo):
		self._select_chip(btn, tipo)

	def _select_chip(self, btn: ctk.CTkButton, tipo: ProduccionTipo):
		if self._selected_chip is not None:
			try:
				self._apply_chip_style(self._selected_chip, "default")
			except Exception:
				pass
		self._selected_chip = btn
		self.tipo_seleccionado = tipo
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
		frame_nav = ctk.CTkFrame(self, fg_color=self._bg)
		frame_nav.pack(fill="x", padx=40, pady=20)

		# Botón VOLVER
		nav_volver = get_nav_button_config(self.config, "volver")
		self.btn_volver = ButtonFactory.create_button(
			parent=frame_nav,
			text=nav_volver.get("text", "VOLVER"),
			command=self._on_volver_handler,
			width=nav_volver.get("width", 15) * 10,
			height=nav_volver.get("height", 2) * 20,
			font=get_font(self.config, nav_volver.get("font_key", "button")),
			style_key="action_confirm",
			module="produccion",
			palette_key="primary",
			cursor="hand2"
		)
		self.btn_volver.pack(side="left", padx=10)

		# Botón SIGUIENTE
		nav_sig = get_nav_button_config(self.config, "siguiente")
		self.btn_siguiente = ButtonFactory.create_button(
			parent=frame_nav,
			text=nav_sig.get("text", "SIGUIENTE"),
			command=self._on_siguiente_handler,
			width=nav_sig.get("width", 15) * 10,
			height=nav_sig.get("height", 2) * 20,
			font=get_font(self.config, nav_sig.get("font_key", "button")),
			style_key="action_confirm",
			module="produccion",
			palette_key="primary",
			cursor="hand2"
		)
		self.btn_siguiente.pack(side="right", padx=10)

	def _on_nav_enter_callback(self, btn: ctk.CTkButton, tipo: Optional[ProduccionTipo]):
		if self._selected_chip is not None and self._selected_chip == btn:
			if self.on_siguiente and self.tipo_seleccionado:
				self.on_siguiente(self.tipo_seleccionado)
		elif tipo is not None:
			self._select_chip(btn, tipo)

	def _on_siguiente_handler(self):
		if self.tipo_seleccionado and self.on_siguiente:
			self.on_siguiente(self.tipo_seleccionado)

	def _on_volver_handler(self):
		if self.on_volver:
			self.on_volver()

	def obtener_seleccion(self) -> Optional[ProduccionTipo]:
		return self.tipo_seleccionado

	def destruir(self):
		self.clear_keyboard_navigation()
		self.destroy()
