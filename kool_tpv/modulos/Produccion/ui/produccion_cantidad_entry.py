"""Widget de entrada de cantidad.

Contiene la clase `CantidadEntryWidget` que muestra un campo de entrada
para la cantidad, con lógica especial: Enter vacío = +1 automático.
"""
import tkinter as tk
from typing import Optional, Callable


class CantidadEntryWidget:
	"""Widget para entrada de cantidad.

	Args:
		parent: Widget padre donde se mostrará el widget.
		on_confirmar: Callback cuando se confirma la cantidad (recibe el valor).
		titulo: Título opcional del widget.
		valor_defecto: Valor por defecto del campo (por defecto 1).
		permitir_cero: Si permite cero como valor válido (por defecto False).
	"""

	def __init__(self, parent, on_confirmar: Callable[[int], None], titulo: str = "CANTIDAD",
	             valor_defecto: int = 1, permitir_cero: bool = False):
		self.parent = parent
		self.on_confirmar = on_confirmar
		self.titulo = titulo
		self.cantidad: Optional[int] = None
		self.valor_defecto = valor_defecto
		self.permitir_cero = permitir_cero

		# Frame principal
		self.frame = tk.Frame(parent, bg="#2c3e50")
		self.frame.pack(fill=tk.BOTH, expand=True)

		# Título
		self._crear_titulo()

		# Campo de cantidad
		self._crear_cantidad()

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

	def _crear_cantidad(self):
		"""Crear el campo de entrada de cantidad."""
		frame_cantidad = tk.Frame(self.frame, bg="#2c3e50")
		frame_cantidad.pack(expand=True, fill=tk.BOTH, padx=40)

		# Label de ayuda
		ayuda = tk.Label(
			frame_cantidad,
			text="Enter vacío = +1 automático",
			font=("Arial", 12),
			bg="#2c3e50",
			fg="#95a5a6"
		)
		ayuda.pack(pady=(0, 10))

		# Entry de cantidad
		self.entry_cantidad = tk.Entry(
			frame_cantidad,
			font=("Arial", 24, "bold"),
			justify=tk.CENTER,
			takefocus=True
		)
		self.entry_cantidad.pack(fill=tk.X, ipady=10)
		self.entry_cantidad.insert(0, str(self.valor_defecto))
		self.entry_cantidad.select_range(0, tk.END)

		# Eventos
		self.entry_cantidad.bind("<Return>", self._on_enter)
		self.entry_cantidad.bind("<FocusIn>", self._on_focus_in)

		# Botones de ajuste rápido
		frame_botones = tk.Frame(frame_cantidad, bg="#2c3e50")
		frame_botones.pack(pady=20)

		btn_menos = tk.Button(
			frame_botones,
			text="-",
			font=("Arial", 18, "bold"),
			width=3,
			bg="#e74c3c",
			fg="white",
			activebackground="#c0392b",
			activeforeground="white",
			takefocus=True,
			command=self._reducir,
			bd=0
		)
		btn_menos.pack(side=tk.LEFT, padx=10)

		btn_mas = tk.Button(
			frame_botones,
			text="+",
			font=("Arial", 18, "bold"),
			width=3,
			bg="#27ae60",
			fg="white",
			activebackground="#2ecc71",
			activeforeground="white",
			takefocus=True,
			command=self._aumentar,
			bd=0
		)
		btn_mas.pack(side=tk.LEFT, padx=10)

	def _on_focus_in(self, event):
		"""Seleccionar todo el texto al recibir el foco."""
		self.entry_cantidad.select_range(0, tk.END)

	def _on_enter(self, event):
		"""Manejador de Enter: si está vacío, añade +1."""
		valor = self.entry_cantidad.get().strip()

		if not valor:
			# Enter vacío = +1 automático
			self.cantidad = self.valor_defecto
		else:
			try:
				self.cantidad = int(valor)
				if self.cantidad <= 0 and not self.permitir_cero:
					self.cantidad = self.valor_defecto
			except ValueError:
				self.cantidad = self.valor_defecto

		self.entry_cantidad.delete(0, tk.END)
		self.entry_cantidad.insert(0, str(self.cantidad))

		if self.on_confirmar:
			self.on_confirmar(self.cantidad)

	def _aumentar(self):
		"""Aumentar la cantidad en 1."""
		try:
			actual = int(self.entry_cantidad.get())
			self.entry_cantidad.delete(0, tk.END)
			self.entry_cantidad.insert(0, str(actual + 1))
			self.entry_cantidad.select_range(0, tk.END)
		except ValueError:
			self.entry_cantidad.delete(0, tk.END)
			self.entry_cantidad.insert(0, str(self.valor_defecto))

	def _reducir(self):
		"""Reducir la cantidad en 1 (mínimo 1 o 0 según configuración)."""
		try:
			actual = int(self.entry_cantidad.get())
			minimo = 0 if self.permitir_cero else 1
			nuevo = max(minimo, actual - 1)
			self.entry_cantidad.delete(0, tk.END)
			self.entry_cantidad.insert(0, str(nuevo))
			self.entry_cantidad.select_range(0, tk.END)
		except ValueError:
			self.entry_cantidad.delete(0, tk.END)
			self.entry_cantidad.insert(0, str(self.valor_defecto))

	def obtener_valor(self) -> Optional[int]:
		"""Obtener el valor actual de la cantidad.

		Returns:
			Valor de la cantidad o None.
		"""
		try:
			return int(self.entry_cantidad.get())
		except ValueError:
			return None

	def establecer_valor(self, valor: int):
		"""Establecer el valor de la cantidad."""
		self.entry_cantidad.delete(0, tk.END)
		self.entry_cantidad.insert(0, str(valor))
		self.entry_cantidad.select_range(0, tk.END)

	def destruir(self):
		"""Destruir el widget y limpiar recursos."""
		self.frame.destroy()
