"""Subvista de selección de producto.

Contiene la clase `NuevaProduccionView` que muestra el widget de selección
de producto y botones de navegación (SIGUIENTE / VOLVER).
"""
import tkinter as tk
from typing import Callable, Optional

import customtkinter as ctk

from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.produccion.models.produccion_tipos_model import ProduccionTipo
from kool_tpv.modulos.produccion.models.produccion_menu_model import ProduccionMenuItem
from kool_tpv.modulos.produccion.ui.produccion_producto_selector import ProductoSelectorWidget
from kool_tpv.modulos.produccion.ui.subvistas.config_helper import cargar_config_produccion, get_font, get_nav_button_config, get_nav_button_style
from kool_tpv.utils.keyboard_nav_mixin import KeyboardNavigableMixin


class NuevaProduccionView(ctk.CTkFrame, KeyboardNavigableMixin):
	"""Subvista para seleccionar el tipo de producto.

	Args:
		parent: Widget padre donde se mostrará la subvista.
		on_siguiente: Callback cuando se pulsa SIGUIENTE (recibe el código de producto).
		on_volver: Callback cuando se pulsa VOLVER.
	"""

	def __init__(self, parent, db: Database,
	             on_siguiente: Optional[Callable[[ProduccionMenuItem], None]] = None,
	             on_volver: Optional[Callable] = None,
	             keyboard_mgr=None):
		# Cargar configuración
		self.config = cargar_config_produccion()
		self._colors = self.config.get("colors", {})
		self._bg = self._colors.get("background", "#2c3e50")

		# Inicializar como CTkFrame
		ctk.CTkFrame.__init__(self, parent, fg_color=self._bg)
		KeyboardNavigableMixin.__init_keyboard_mixin__(self)

		self.db = db
		self.on_siguiente = on_siguiente
		self.on_volver = on_volver
		self.keyboard_mgr = keyboard_mgr
		self.menu_seleccionado: Optional[ProduccionMenuItem] = None

		self._text = self._colors.get("text", "#ecf0f1")

		# Frame principal ya es self
		self.pack(fill=tk.BOTH, expand=True)

		# Widget selector de producto
		self._crear_selector()

		# Botones de navegación
		self._crear_botones_navegacion()

		# Configurar navegación con KeyboardNavigableMixin
		# Primero los chips del selector, luego los botones
		self._navigable_buttons = []
		if hasattr(self.selector, 'get_navigable_widgets'):
			for btn, callback in self.selector.get_navigable_widgets():
				self._navigable_buttons.append((btn, callback))
		
		self._navigable_buttons.append((self.btn_volver, self._on_volver_handler))
		self._navigable_buttons.append((self.btn_siguiente, self._on_siguiente_handler))

		if self._navigable_buttons:
			self._setup_keyboard_navigation()

		if self._navigable_buttons:
			self.after(100, lambda: self._focus_nav_widget(0))

	def _get_font(self, key: str) -> tuple:
		"""Obtener una fuente desde la configuración."""
		return get_font(self.config, key)

	def _crear_selector(self):
		"""Crear el widget selector de producto."""
		self.selector = ProductoSelectorWidget(
			self,
			db=self.db,
			on_seleccion=self._on_producto_seleccionado,
			on_advance=self._on_siguiente_handler,
			keyboard_mgr=self.keyboard_mgr,
			titulo="SELECCIONA PRODUCTO"
		)
		self.selector.frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(20, 10))

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
			font=self._get_font(nav_volver.get("font_key", "button")),
			fg_color=style_volver.get("bg", "#e74c3c"),
			text_color=style_volver.get("text", "#FFFFFF"),
			hover_color=style_volver.get("hover", "#c0392b"),
			border_color=style_volver.get("border", "#e74c3c"),
			border_width=style_volver.get("focus_thickness", 0),
			width=nav_volver.get("width", 15) * 10,
			height=nav_volver.get("height", 2) * 20,
			cursor="hand2",
			command=self._on_volver_handler
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
			command=self._on_siguiente_handler
		)
		self.btn_siguiente.pack(side=tk.RIGHT, padx=10)

	def _on_producto_seleccionado(self, menu_item: ProduccionMenuItem):
		"""Manejador cuando se selecciona un menú de producto."""
		self.menu_seleccionado = menu_item

	def _on_siguiente_handler(self):
		"""Manejador del botón SIGUIENTE."""
		if self.menu_seleccionado and self.on_siguiente:
			self.on_siguiente(self.menu_seleccionado)

	def _on_volver_handler(self):
		"""Manejador del botón VOLVER."""
		if self.on_volver:
			self.on_volver()

	def obtener_seleccion(self) -> Optional[ProduccionMenuItem]:
		"""Obtener el menú de producto seleccionado.

		Returns:
			Objeto ProduccionMenuItem o None.
		"""
		return self.menu_seleccionado

	def destruir(self):
		"""Destruir la subvista y limpiar recursos."""
		self.clear_keyboard_navigation()
		if hasattr(self.selector, 'destruir'):
			self.selector.destruir()
		self.destroy()
