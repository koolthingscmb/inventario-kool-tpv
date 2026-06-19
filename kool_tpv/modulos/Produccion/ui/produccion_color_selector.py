"""Widget de selección de color.

Contiene la clase `ColorSelectorWidget` que muestra chips de colores
para seleccionar el color del producto.
"""
import tkinter as tk
from typing import Optional, Callable, List, Dict

COLORES_PREDETERMINADOS = [
	{"codigo": "blanco", "nombre": "BLANCO", "color": "#FFFFFF", "texto": "#000000"},
	{"codigo": "negro", "nombre": "NEGRO", "color": "#000000", "texto": "#FFFFFF"},
	{"codigo": "rojo", "nombre": "ROJO", "color": "#E74C3C", "texto": "#FFFFFF"},
	{"codigo": "azul", "nombre": "AZUL", "color": "#3498DB", "texto": "#FFFFFF"},
	{"codigo": "verde", "nombre": "VERDE", "color": "#2ECC71", "texto": "#FFFFFF"},
	{"codigo": "amarillo", "nombre": "AMARILLO", "color": "#F1C40F", "texto": "#000000"},
	{"codigo": "naranja", "nombre": "NARANJA", "color": "#E67E22", "texto": "#FFFFFF"},
	{"codigo": "morado", "nombre": "MORADO", "color": "#9B59B6", "texto": "#FFFFFF"},
	{"codigo": "rosa", "nombre": "ROSA", "color": "#FF69B4", "texto": "#FFFFFF"},
	{"codigo": "gris", "nombre": "GRIS", "color": "#95A5A6", "texto": "#FFFFFF"},
]


class ColorSelectorWidget:
	"""Widget para seleccionar el color.

	Args:
		parent: Widget padre donde se mostrará el selector.
		on_seleccion: Callback cuando se selecciona un color (recibe el código).
		titulo: Título opcional del widget.
		colores_disponibles: Lista opcional de colores disponibles (por defecto todos).
	"""

	def __init__(self, parent, on_seleccion: Callable[[str], None], titulo: str = "SELECCIONA COLOR",
	             colores_disponibles: Optional[List[Dict]] = None):
		self.parent = parent
		self.on_seleccion = on_seleccion
		self.titulo = titulo
		self.color_seleccionado: Optional[str] = None
		self.colores_disponibles = colores_disponibles or COLORES_PREDETERMINADOS

		# Frame principal
		self.frame = tk.Frame(parent, bg="#2c3e50")
		self.frame.pack(fill=tk.BOTH, expand=True)

		# Título
		self._crear_titulo()

		# Grid de chips de colores
		self._crear_chips_colores()

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

	def _crear_chips_colores(self):
		"""Crear los chips de colores."""
		frame_chips = tk.Frame(self.frame, bg="#2c3e50")
		frame_chips.pack(expand=True, fill=tk.BOTH, padx=40, pady=20)

		# Configuración común para botones
		btn_config = {
			"font": ("Arial", 12, "bold"),
			"width": 12,
			"height": 3,
			"takefocus": True,
			"bd": 2,
			"cursor": "hand2",
			"relief": tk.RAISED
		}

		# Crear chips en grid
		for idx, color in enumerate(self.colores_disponibles):
			btn = tk.Button(
				frame_chips,
				text=color["nombre"],
				bg=color["color"],
				fg=color["texto"],
				activebackground=self._oscurecer_color(color["color"]),
				activeforeground=color["texto"],
				command=lambda c=color["codigo"]: self._on_click(c),
				**btn_config
			)

			# Calcular posición en grid (3 columnas)
			row = idx // 3
			col = idx % 3
			btn.grid(row=row, column=col, padx=15, pady=15, sticky="nsew")

		# Configurar pesos del grid para expansión
		for i in range(3):
			frame_chips.columnconfigure(i, weight=1)
		for i in range((len(self.colores_disponibles) + 2) // 3):
			frame_chips.rowconfigure(i, weight=1)

		# Navegación por teclado con flechas
		frame_chips.bind("<Left>", lambda e: self._navegar_flecha(-1))
		frame_chips.bind("<Right>", lambda e: self._navegar_flecha(1))
		frame_chips.bind("<Up>", lambda e: self._navegar_flecha(-3))
		frame_chips.bind("<Down>", lambda e: self._navegar_flecha(3))

	def _on_click(self, color_codigo: str):
		"""Manejador del clic en un color."""
		self.color_seleccionado = color_codigo
		if self.on_seleccion:
			self.on_seleccion(color_codigo)

	def _navegar_flecha(self, delta: int):
		"""Navegar entre botones con flechas del teclado."""
		widget_actual = self.frame.focus_get()
		if widget_actual and isinstance(widget_actual, tk.Button):
			widgetes = [w for w in self.frame.winfo_children() if isinstance(w, tk.Button)]
			if widget_actual in widgetes:
				idx_actual = widgetes.index(widget_actual)
				nuevo_idx = (idx_actual + delta) % len(widgetes)
				widgetes[nuevo_idx].focus_set()

	def _oscurecer_color(self, color: str) -> str:
		"""Oscurecer un color hexadecimal para el estado activo."""
		try:
			# Convertir hex a RGB
			hex_color = color.lstrip("#")
			r = int(hex_color[0:2], 16)
			g = int(hex_color[2:4], 16)
			b = int(hex_color[4:6], 16)

			# Oscurecer un 20%
			r = int(r * 0.8)
			g = int(g * 0.8)
			b = int(b * 0.8)

			# Convertir de vuelta a hex
			return f"#{r:02x}{g:02x}{b:02x}"
		except:
			return color

	def obtener_seleccion(self) -> Optional[str]:
		"""Obtener el color seleccionado.

		Returns:
			Código del color seleccionado o None.
		"""
		return self.color_seleccionado

	def destruir(self):
		"""Destruir el widget y limpiar recursos."""
		self.frame.destroy()
