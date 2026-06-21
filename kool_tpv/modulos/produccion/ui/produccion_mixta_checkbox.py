"""Widget de checkbox para producción mixta.

Contiene la clase `ProduccionMixtaCheckbox` que muestra un checkbox
para seleccionar producción mixta (delante y detrás), aplicable solo para camisetas.
"""
import tkinter as tk
from typing import Optional, Callable


class ProduccionMixtaCheckbox:
	"""Widget para checkbox de producción mixta.

	Args:
		parent: Widget padre donde se mostrará el widget.
		on_cambio: Callback cuando cambia el estado del checkbox (recibe el valor bool).
		titulo: Título opcional del widget.
		valor_defecto: Valor por defecto del checkbox (por defecto False).
	"""

	def __init__(self, parent, on_cambio: Callable[[bool], None], titulo: str = "PRODUCCIÓN MIXTA",
	             valor_defecto: bool = False):
		self.parent = parent
		self.on_cambio = on_cambio
		self.titulo = titulo
		self.produccion_mixta = valor_defecto

		# Frame principal
		self.frame = tk.Frame(parent, bg="#2c3e50")
		self.frame.pack(fill=tk.BOTH, expand=True)

		# Título
		self._crear_titulo()

		# Checkbox
		self._crear_checkbox()

	def _crear_titulo(self):
		"""Crear el título del widget."""
		titulo = tk.Label(
			self.frame,
			text=self.titulo,
			font=("Arial", 20, "bold"),
			bg="#2c3e50",
			fg="#ecf0f1"
		)
		titulo.pack(pady=20)

	def _crear_checkbox(self):
		"""Crear el checkbox de producción mixta."""
		frame_checkbox = tk.Frame(self.frame, bg="#2c3e50")
		frame_checkbox.pack(expand=True, fill=tk.BOTH, padx=40)

		# Variable del checkbox
		self.var_mixta = tk.BooleanVar(value=self.produccion_mixta)

		# Checkbox
		self.checkbox = tk.Checkbutton(
			frame_checkbox,
			text="Delante y detrás (+15 min)",
			variable=self.var_mixta,
			font=("Arial", 16),
			bg="#2c3e50",
			fg="#ecf0f1",
			selectcolor="#34495e",
			activebackground="#2c3e50",
			activeforeground="#ecf0f1",
			takefocus=True,
			command=self._on_cambio,
			bd=2,
			relief=tk.RAISED
		)
		self.checkbox.pack(pady=20)

		# Label de ayuda
		ayuda = tk.Label(
			frame_checkbox,
			text="Solo aplicable para camisetas",
			font=("Arial", 12),
			bg="#2c3e50",
			fg="#95a5a6"
		)
		ayuda.pack(pady=(0, 10))

	def _on_cambio(self):
		"""Manejador de cambio del checkbox."""
		self.produccion_mixta = self.var_mixta.get()
		if self.on_cambio:
			self.on_cambio(self.produccion_mixta)

	def obtener_valor(self) -> bool:
		"""Obtener el valor actual del checkbox.

		Returns:
			True si está activado, False en caso contrario.
		"""
		return self.var_mixta.get()

	def establecer_valor(self, valor: bool):
		"""Establecer el valor del checkbox."""
		self.var_mixta.set(valor)
		self.produccion_mixta = valor

	def destruir(self):
		"""Destruir el widget y limpiar recursos."""
		self.frame.destroy()
