"""Widget de selección de talla.

Contiene la clase `TallaSelectorWidget` que muestra botones/chips
para seleccionar la talla (S, M, L, XL, etc.).
"""
import tkinter as tk
from typing import Optional, Callable

TALLAS = [
	{"codigo": "XS", "nombre": "XS"},
	{"codigo": "S", "nombre": "S"},
	{"codigo": "M", "nombre": "M"},
	{"codigo": "L", "nombre": "L"},
	{"codigo": "XL", "nombre": "XL"},
	{"codigo": "XXL", "nombre": "XXL"},
]


class TallaSelectorWidget:
	"""Widget para seleccionar la talla.

	Args:
		parent: Widget padre donde se mostrará el selector.
		on_seleccion: Callback cuando se selecciona una talla (recibe el código).
		titulo: Título opcional del widget.
		tallas_disponibles: Lista opcional de tallas disponibles (por defecto todas).
	"""

	def __init__(self, parent, on_seleccion: Callable[[str], None], titulo: str = "SELECCIONA TALLA",
	             tallas_disponibles: Optional[list] = None):
		self.parent = parent
		self.on_seleccion = on_seleccion
		self.titulo = titulo
		self.talla_seleccionada: Optional[str] = None
		self.tallas_disponibles = tallas_disponibles or TALLAS

		# Frame principal
		self.frame = tk.Frame(parent, bg="#2c3e50")
		self.frame.pack(fill=tk.BOTH, expand=True)

		# Título
		self._crear_titulo()

		# Grid de botones de tallas
		self._crear_botones_tallas()

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

	def _crear_botones_tallas(self):
		"""Crear los botones/chips para cada talla."""
		frame_botones = tk.Frame(self.frame, bg="#2c3e50")
		frame_botones.pack(expand=True, fill=tk.BOTH, padx=40, pady=20)

		# Configuración común para botones
		btn_config = {
			"font": ("Arial", 16, "bold"),
			"width": 10,
			"height": 2,
			"takefocus": True,
			"bd": 0,
			"cursor": "hand2"
		}

		# Crear botones en grid (2 filas)
		for idx, talla in enumerate(self.tallas_disponibles):
			btn = tk.Button(
				frame_botones,
				text=talla["nombre"],
				bg="#3498db",
				fg="white",
				activebackground="#2980b9",
				activeforeground="white",
				command=lambda t=talla["codigo"]: self._on_click(t),
				**btn_config
			)

			# Calcular posición en grid (2 filas)
			row = idx // 3
			col = idx % 3
			btn.grid(row=row, column=col, padx=15, pady=15, sticky="nsew")

		# Configurar pesos del grid para expansión
		for i in range(3):
			frame_botones.columnconfigure(i, weight=1)
		for i in range((len(self.tallas_disponibles) + 2) // 3):
			frame_botones.rowconfigure(i, weight=1)

		# Navegación por teclado con flechas
		frame_botones.bind("<Left>", lambda e: self._navegar_flecha(-1))
		frame_botones.bind("<Right>", lambda e: self._navegar_flecha(1))
		frame_botones.bind("<Up>", lambda e: self._navegar_flecha(-3))
		frame_botones.bind("<Down>", lambda e: self._navegar_flecha(3))

	def _on_click(self, talla_codigo: str):
		"""Manejador del clic en una talla."""
		self.talla_seleccionada = talla_codigo
		if self.on_seleccion:
			self.on_seleccion(talla_codigo)

	def _navegar_flecha(self, delta: int):
		"""Navegar entre botones con flechas del teclado."""
		widget_actual = self.frame.focus_get()
		if widget_actual and isinstance(widget_actual, tk.Button):
			widgetes = [w for w in self.frame.winfo_children() if isinstance(w, tk.Button)]
			if widget_actual in widgetes:
				idx_actual = widgetes.index(widget_actual)
				nuevo_idx = (idx_actual + delta) % len(widgetes)
				widgetes[nuevo_idx].focus_set()

	def obtener_seleccion(self) -> Optional[str]:
		"""Obtener la talla seleccionada.

		Returns:
			Código de la talla seleccionada o None.
		"""
		return self.talla_seleccionada

	def destruir(self):
		"""Destruir el widget y limpiar recursos."""
		self.frame.destroy()
