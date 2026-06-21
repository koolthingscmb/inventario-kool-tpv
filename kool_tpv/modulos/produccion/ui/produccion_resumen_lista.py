"""Widget de lista de resumen.

Contiene la clase `ResumenListaWidget` que muestra una lista temporal
de diseños añadidos con opción de eliminar.
"""
import tkinter as tk
from typing import Optional, Callable, List, Dict, Any


class ResumenListaWidget:
	"""Widget para mostrar y gestionar la lista de resumen.

	Args:
		parent: Widget padre donde se mostrará el widget.
		on_eliminar: Callback cuando se elimina un ítem (recibe el índice).
		on_confirmar: Callback cuando se confirma la lista (recibe la lista completa).
		titulo: Título opcional del widget.
	"""

	def __init__(self, parent, on_eliminar: Optional[Callable[[int], None]] = None,
	             on_confirmar: Optional[Callable[[List[Dict]], None]] = None,
	             titulo: str = "RESUMEN"):
		self.parent = parent
		self.on_eliminar = on_eliminar
		self.on_confirmar = on_confirmar
		self.titulo = titulo
		self.items: List[Dict] = []

		# Frame principal
		self.frame = tk.Frame(parent, bg="#2c3e50")
		self.frame.pack(fill=tk.BOTH, expand=True)

		# Título
		self._crear_titulo()

		# Lista de resumen
		self._crear_lista()

		# Botones de acción
		self._crear_botones()

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

	def _crear_lista(self):
		"""Crear la lista de resumen con scrollbar."""
		frame_lista = tk.Frame(self.frame, bg="#2c3e50")
		frame_lista.pack(fill=tk.BOTH, expand=True, padx=40, pady=10)

		# Scrollbar
		scrollbar = tk.Scrollbar(frame_lista)
		scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

		# Listbox
		self.listbox = tk.Listbox(
			frame_lista,
			font=("Arial", 12),
			bg="#34495e",
			fg="#ecf0f1",
			selectbackground="#3498db",
			selectforeground="white",
			yscrollcommand=scrollbar.set,
			takefocus=True
		)
		self.listbox.pack(fill=tk.BOTH, expand=True)
		scrollbar.config(command=self.listbox.yview)

		# Frame para botones de eliminar
		frame_eliminar = tk.Frame(frame_lista, bg="#2c3e50")
		frame_eliminar.pack(pady=10)

		btn_eliminar = tk.Button(
			frame_eliminar,
			text="ELIMINAR SELECCIONADO",
			font=("Arial", 12, "bold"),
			bg="#e74c3c",
			fg="white",
			activebackground="#c0392b",
			activeforeground="white",
			takefocus=True,
			command=self._on_eliminar_seleccionado,
			bd=0,
			padx=20,
			pady=5
		)
		btn_eliminar.pack()

	def _crear_botones(self):
		"""Crear los botones de acción."""
		frame_botones = tk.Frame(self.frame, bg="#2c3e50")
		frame_botones.pack(fill=tk.X, padx=40, pady=20)

		btn_confirmar = tk.Button(
			frame_botones,
			text="CONFIRMAR",
			font=("Arial", 14, "bold"),
			bg="#27ae60",
			fg="white",
			activebackground="#2ecc71",
			activeforeground="white",
			takefocus=True,
			command=self._on_confirmar,
			bd=0,
			padx=30,
			pady=10
		)
		btn_confirmar.pack(side=tk.RIGHT, padx=10)

		btn_cancelar = tk.Button(
			frame_botones,
			text="CANCELAR",
			font=("Arial", 14, "bold"),
			bg="#e74c3c",
			fg="white",
			activebackground="#c0392b",
			activeforeground="white",
			takefocus=True,
			command=self._on_cancelar,
			bd=0,
			padx=30,
			pady=10
		)
		btn_cancelar.pack(side=tk.RIGHT, padx=10)

	def _on_eliminar_seleccionado(self):
		"""Eliminar el ítem seleccionado de la lista."""
		indice = self.listbox.curselection()
		if indice:
			idx = indice[0]
			if 0 <= idx < len(self.items):
				self.items.pop(idx)
				self._actualizar_lista()
				if self.on_eliminar:
					self.on_eliminar(idx)

	def _on_confirmar(self):
		"""Confirmar la lista actual."""
		if self.on_confirmar:
			self.on_confirmar(self.items)

	def _on_cancelar(self):
		"""Cancelar y limpiar la lista."""
		self.items.clear()
		self._actualizar_lista()

	def _actualizar_lista(self):
		"""Actualizar la visualización de la lista."""
		self.listbox.delete(0, tk.END)
		for item in self.items:
			texto = self._formatear_item(item)
			self.listbox.insert(tk.END, texto)

	def _formatear_item(self, item: Dict) -> str:
		"""Formatear un ítem para mostrar en la lista."""
		partes = []
		if 'producto' in item:
			partes.append(item['producto'])
		if 'talla' in item:
			partes.append(f"T: {item['talla']}")
		if 'color' in item:
			partes.append(f"C: {item['color']}")
		if 'diseno' in item:
			partes.append(f"D: {item['diseno']}")
		if 'cantidad' in item:
			partes.append(f"x{item['cantidad']}")
		if 'mixta' in item and item['mixta']:
			partes.append("(Mixta)")
		return " | ".join(partes)

	def agregar_item(self, item: Dict[str, Any]):
		"""Agregar un ítem a la lista.

		Args:
			item: Diccionario con los datos del ítem.
		"""
		self.items.append(item)
		self._actualizar_lista()

	def limpiar(self):
		"""Limpiar todos los ítems de la lista."""
		self.items.clear()
		self._actualizar_lista()

	def obtener_items(self) -> List[Dict]:
		"""Obtener la lista completa de ítems.

		Returns:
			Lista de ítems.
		"""
		return self.items.copy()

	def esta_vacia(self) -> bool:
		"""Verificar si la lista está vacía.

		Returns:
			True si está vacía, False en caso contrario.
		"""
		return len(self.items) == 0

	def destruir(self):
		"""Destruir el widget y limpiar recursos."""
		self.frame.destroy()
