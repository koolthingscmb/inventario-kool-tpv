"""Widget de búsqueda de diseños.

Contiene la clase `DisenoSearchWidget` que muestra un campo de búsqueda
y una lista de diseños filtrada en tiempo real.
"""
import tkinter as tk
from typing import Optional, Callable, List, Dict

from kool_tpv.modulos.produccion.services.produccion_disenos_service import ProduccionDisenosService
from kool_tpv.modulos.produccion.models.produccion_diseno_model import ProduccionDiseno


class DisenoSearchWidget:
	"""Widget para buscar y seleccionar diseños.

	Args:
		parent: Widget padre donde se mostrará el widget.
		db: instancia de `Database` ya conectada.
		on_seleccion: Callback cuando se selecciona un diseño (recibe el código).
		titulo: Título opcional del widget.
	"""

	def __init__(self, parent, db, on_seleccion: Callable[[str], None], titulo: str = "BUSCAR DISEÑO"):
		self.parent = parent
		self.db = db
		self.on_seleccion = on_seleccion
		self.titulo = titulo
		self.diseno_seleccionado: Optional[str] = None
		self.disenos_service = ProduccionDisenosService(db)
		self.resultados: List[ProduccionDiseno] = []

		# Frame principal
		self.frame = tk.Frame(parent, bg="#2c3e50")
		self.frame.pack(fill=tk.BOTH, expand=True)

		# Título
		self._crear_titulo()

		# Campo de búsqueda
		self._crear_busqueda()

		# Lista de resultados
		self._crear_lista_resultados()

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

	def _crear_busqueda(self):
		"""Crear el campo de búsqueda."""
		frame_busqueda = tk.Frame(self.frame, bg="#2c3e50")
		frame_busqueda.pack(fill=tk.X, padx=40, pady=10)

		self.entry_busqueda = tk.Entry(
			frame_busqueda,
			font=("Arial", 14),
			takefocus=True
		)
		self.entry_busqueda.pack(fill=tk.X, ipady=10)

		# Eventos de búsqueda
		self.entry_busqueda.bind("<KeyRelease>", self._on_buscar)
		self.entry_busqueda.bind("<Return>", self._on_enter_seleccion)

	def _crear_lista_resultados(self):
		"""Crear la lista de resultados."""
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
			takefocus=True,
			height=10
		)
		self.listbox.pack(fill=tk.BOTH, expand=True)
		scrollbar.config(command=self.listbox.yview)

		# Eventos de selección
		self.listbox.bind("<Double-Button-1>", self._on_doble_clic)
		self.listbox.bind("<Return>", self._on_enter_seleccion)

		# Cargar todos los diseños al inicio
		self._cargar_todos()

	def _on_buscar(self, event):
		"""Manejador de búsqueda en tiempo real."""
		termino = self.entry_busqueda.get().strip()
		if termino:
			self.resultados = self.disenos_service.buscar(termino)
		else:
			self.resultados = self.disenos_service.obtener_activos()
		self._actualizar_lista()

	def _actualizar_lista(self):
		"""Actualizar la lista de resultados."""
		self.listbox.delete(0, tk.END)
		for diseno in self.resultados:
			texto = f"{diseno.codigo} - {diseno.nombre}"
			if diseno.coleccion:
				texto += f" ({diseno.coleccion})"
			self.listbox.insert(tk.END, texto)

	def _on_doble_clic(self, event):
		"""Manejador de doble clic en un diseño."""
		indice = self.listbox.curselection()
		if indice:
			self._seleccionar_diseno(indice[0])

	def _on_enter_seleccion(self, event):
		"""Manejador de Enter para seleccionar el diseño actual."""
		indice = self.listbox.curselection()
		if indice:
			self._seleccionar_diseno(indice[0])

	def _seleccionar_diseno(self, indice: int):
		"""Seleccionar un diseño de la lista."""
		if 0 <= indice < len(self.resultados):
			diseno = self.resultados[indice]
			self.diseno_seleccionado = diseno.codigo
			if self.on_seleccion:
				self.on_seleccion(diseno.codigo)

	def _cargar_todos(self):
		"""Cargar todos los diseños activos."""
		self.resultados = self.disenos_service.obtener_activos()
		self._actualizar_lista()

	def obtener_seleccion(self) -> Optional[str]:
		"""Obtener el diseño seleccionado.

		Returns:
			Código del diseño seleccionado o None.
		"""
		return self.diseno_seleccionado

	def destruir(self):
		"""Destruir el widget y limpiar recursos."""
		self.frame.destroy()
