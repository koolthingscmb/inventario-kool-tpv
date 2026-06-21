"""Subvista de selección de producto.

Contiene la clase `NuevaProduccionView` que muestra el widget de selección
de producto y botones de navegación (SIGUIENTE / VOLVER).
"""
import tkinter as tk
from typing import Callable, Optional

from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.produccion.models.produccion_tipos_model import ProduccionTipo
from kool_tpv.modulos.produccion.ui.produccion_producto_selector import ProductoSelectorWidget
from kool_tpv.modulos.produccion.ui.subvistas.config_helper import cargar_config_produccion, get_font, get_nav_button_config, get_nav_button_style


class NuevaProduccionView:
	"""Subvista para seleccionar el tipo de producto.

	Args:
		parent: Widget padre donde se mostrará la subvista.
		on_siguiente: Callback cuando se pulsa SIGUIENTE (recibe el código de producto).
		on_volver: Callback cuando se pulsa VOLVER.
	"""

	def __init__(self, parent, db: Database,
	             on_siguiente: Optional[Callable[[ProduccionTipo], None]] = None,
	             on_volver: Optional[Callable] = None):
		self.parent = parent
		self.db = db
		self.on_siguiente = on_siguiente
		self.on_volver = on_volver
		self.tipo_seleccionado: Optional[ProduccionTipo] = None

		# Cargar configuración
		self.config = cargar_config_produccion()
		self._colors = self.config.get("colors", {})
		self._bg = self._colors.get("background", "#2c3e50")
		self._text = self._colors.get("text", "#ecf0f1")

		# Frame principal
		self.frame = tk.Frame(parent, bg=self._bg)
		self.frame.pack(fill=tk.BOTH, expand=True)

		# Widget selector de producto
		self._crear_selector()

		# Botones de navegación
		self._crear_botones_navegacion()

	def _get_font(self, key: str) -> tuple:
		"""Obtener una fuente desde la configuración."""
		return get_font(self.config, key)

	def _crear_selector(self):
		"""Crear el widget selector de producto."""
		frame_selector = tk.Frame(self.frame, bg=self._bg)
		frame_selector.pack(fill=tk.BOTH, expand=True, padx=20, pady=(20, 10))

		self.selector = ProductoSelectorWidget(
			frame_selector,
			db=self.db,
			on_seleccion=self._on_producto_seleccionado,
			titulo="SELECCIONA PRODUCTO"
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

	def _on_producto_seleccionado(self, tipo: ProduccionTipo):
		"""Manejador cuando se selecciona un tipo de producto."""
		self.tipo_seleccionado = tipo

	def _on_siguiente(self):
		"""Manejador del botón SIGUIENTE."""
		if self.tipo_seleccionado and self.on_siguiente:
			self.on_siguiente(self.tipo_seleccionado)

	def _on_volver(self):
		"""Manejador del botón VOLVER."""
		if self.on_volver:
			self.on_volver()

	def obtener_seleccion(self) -> Optional[ProduccionTipo]:
		"""Obtener el tipo de producto seleccionado.

		Returns:
			Objeto ProduccionTipo o None.
		"""
		return self.tipo_seleccionado

	def destruir(self):
		"""Destruir la subvista y limpiar recursos."""
		self.frame.destroy()
