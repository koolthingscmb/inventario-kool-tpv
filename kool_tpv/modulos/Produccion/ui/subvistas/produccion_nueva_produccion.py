"""Subvista de selección de producto.

Contiene la clase `NuevaProduccionView` que muestra el widget de selección
de producto y botones de navegación (SIGUIENTE / VOLVER).
"""
import json
import os
import tkinter as tk
from typing import Callable, Optional

from kool_tpv.modulos.produccion.ui.produccion_producto_selector import ProductoSelectorWidget

_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "config", "config_produccion.json")


def _cargar_config() -> dict:
	"""Cargar la configuración de producción desde JSON."""
	try:
		with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
			return json.load(f)
	except (FileNotFoundError, json.JSONDecodeError):
		return {}


class NuevaProduccionView:
	"""Subvista para seleccionar el tipo de producto.

	Args:
		parent: Widget padre donde se mostrará la subvista.
		on_siguiente: Callback cuando se pulsa SIGUIENTE (recibe el código de producto).
		on_volver: Callback cuando se pulsa VOLVER.
	"""

	def __init__(self, parent, on_siguiente: Optional[Callable[[str], None]] = None,
	             on_volver: Optional[Callable] = None):
		self.parent = parent
		self.on_siguiente = on_siguiente
		self.on_volver = on_volver
		self.producto_seleccionado: Optional[str] = None

		# Cargar configuración
		self.config = _cargar_config()
		self._fonts = self.config.get("fonts", {})
		self._colors = self.config.get("colors", {})
		self._bg = self._colors.get("background", "#2c3e50")
		self._text = self._colors.get("text", "#ecf0f1")
		self._btn_styles = self._colors.get("buttons", {})

		# Frame principal
		self.frame = tk.Frame(parent, bg=self._bg)
		self.frame.pack(fill=tk.BOTH, expand=True)

		# Widget selector de producto
		self._crear_selector()

		# Botones de navegación
		self._crear_botones_navegacion()

	def _get_font(self, key: str) -> tuple:
		"""Obtener una fuente desde la configuración."""
		f = self._fonts.get(key, {})
		return (f.get("family", "Courier New"), f.get("size", 16), f.get("weight", "normal"))

	def _get_btn_style(self, key: str) -> dict:
		"""Obtener el estilo de un botón desde la configuración."""
		return self._btn_styles.get(key, {})

	def _crear_selector(self):
		"""Crear el widget selector de producto."""
		frame_selector = tk.Frame(self.frame, bg=self._bg)
		frame_selector.pack(fill=tk.BOTH, expand=True, padx=20, pady=(20, 10))

		self.selector = ProductoSelectorWidget(
			frame_selector,
			on_seleccion=self._on_producto_seleccionado,
			titulo="SELECCIONA PRODUCTO"
		)

	def _crear_botones_navegacion(self):
		"""Crear los botones de navegación inferior."""
		frame_nav = tk.Frame(self.frame, bg=self._bg)
		frame_nav.pack(fill=tk.X, padx=40, pady=20)

		# Botón VOLVER
		style_volver = self._get_btn_style("volver")
		btn_volver = tk.Button(
			frame_nav,
			text="VOLVER",
			font=self._get_font("button"),
			bg=style_volver.get("bg", "#e74c3c"),
			fg=style_volver.get("text", "#FFFFFF"),
			activebackground=style_volver.get("hover", "#c0392b"),
			activeforeground=style_volver.get("text", "#FFFFFF"),
			takefocus=True,
			bd=0,
			width=15,
			height=2,
			command=self._on_volver
		)
		btn_volver.pack(side=tk.LEFT, padx=10)

		# Botón SIGUIENTE
		style_siguiente = self._get_btn_style("siguiente")
		self.btn_siguiente = tk.Button(
			frame_nav,
			text="SIGUIENTE",
			font=self._get_font("button"),
			bg=style_siguiente.get("bg", "#27ae60"),
			fg=style_siguiente.get("text", "#FFFFFF"),
			activebackground=style_siguiente.get("hover", "#2ecc71"),
			activeforeground=style_siguiente.get("text", "#FFFFFF"),
			takefocus=True,
			bd=0,
			width=15,
			height=2,
			command=self._on_siguiente
		)
		self.btn_siguiente.pack(side=tk.RIGHT, padx=10)

	def _on_producto_seleccionado(self, codigo: str):
		"""Manejador cuando se selecciona un producto."""
		self.producto_seleccionado = codigo

	def _on_siguiente(self):
		"""Manejador del botón SIGUIENTE."""
		if self.producto_seleccionado and self.on_siguiente:
			self.on_siguiente(self.producto_seleccionado)

	def _on_volver(self):
		"""Manejador del botón VOLVER."""
		if self.on_volver:
			self.on_volver()

	def obtener_seleccion(self) -> Optional[str]:
		"""Obtener el producto seleccionado.

		Returns:
			Código del producto seleccionado o None.
		"""
		return self.producto_seleccionado

	def destruir(self):
		"""Destruir la subvista y limpiar recursos."""
		self.frame.destroy()
