"""Vista principal del módulo de Producción.

Contiene la clase `ProduccionView` que muestra el menú principal del módulo
con acceso a las diferentes funcionalidades: NUEVO, COSTES, COLORES, STOCK.
"""
import tkinter as tk
from typing import Callable, Optional

from kool_tpv.base_datos.db_wrapper import Database


class ProduccionView:
	"""Vista principal del módulo de Producción.

	Args:
		parent: Widget padre (normalmente el frame principal de la aplicación).
		db: instancia de `Database` ya conectada.
		on_cerrar: Callback opcional cuando se cierra la vista.
	"""

	def __init__(self, parent, db: Database, on_cerrar: Optional[Callable] = None):
		self.parent = parent
		self.db = db
		self.on_cerrar = on_cerrar

		# Frame principal
		self.frame = tk.Frame(parent, bg="#2c3e50")
		self.frame.pack(fill=tk.BOTH, expand=True)

		# Título
		self._crear_titulo()

		# Botones del menú
		self._crear_botones_menu()

	def _crear_titulo(self):
		"""Crear el título de la vista."""
		titulo = tk.Label(
			self.frame,
			text="PRODUCCIÓN",
			font=("Arial", 24, "bold"),
			bg="#2c3e50",
			fg="#ecf0f1"
		)
		titulo.pack(pady=20)

	def _crear_botones_menu(self):
		"""Crear los botones del menú principal."""
		frame_botones = tk.Frame(self.frame, bg="#2c3e50")
		frame_botones.pack(expand=True, fill=tk.BOTH, padx=40)

		# Configuración común para botones
		btn_config = {
			"font": ("Arial", 16),
			"width": 20,
			"height": 2,
			"takefocus": True,
			"bd": 0
		}

		# Botón NUEVO
		self.btn_nuevo = tk.Button(
			frame_botones,
			text="NUEVO",
			bg="#27ae60",
			fg="white",
			activebackground="#2ecc71",
			activeforeground="white",
			command=self._on_nuevo_click,
			**btn_config
		)
		self.btn_nuevo.pack(pady=10)

		# Botón COSTES
		self.btn_costes = tk.Button(
			frame_botones,
			text="COSTES",
			bg="#f39c12",
			fg="white",
			activebackground="#f1c40f",
			activeforeground="white",
			command=self._on_costes_click,
			**btn_config
		)
		self.btn_costes.pack(pady=10)

		# Botón COLORES
		self.btn_colores = tk.Button(
			frame_botones,
			text="COLORES",
			bg="#3498db",
			fg="white",
			activebackground="#2980b9",
			activeforeground="white",
			command=self._on_colores_click,
			**btn_config
		)
		self.btn_colores.pack(pady=10)

		# Botón STOCK
		self.btn_stock = tk.Button(
			frame_botones,
			text="STOCK",
			bg="#9b59b6",
			fg="white",
			activebackground="#8e44ad",
			activeforeground="white",
			command=self._on_stock_click,
			**btn_config
		)
		self.btn_stock.pack(pady=10)

		# Botón VOLVER
		self.btn_volver = tk.Button(
			frame_botones,
			text="VOLVER",
			bg="#e74c3c",
			fg="white",
			activebackground="#c0392b",
			activeforeground="white",
			command=self._on_volver_click,
			**btn_config
		)
		self.btn_volver.pack(pady=10)

	def _on_nuevo_click(self):
		"""Manejador del botón NUEVO."""
		# TODO: Implementar navegación al flujo de nueva producción
		print("NUEVO - Flujo de producción rápida")

	def _on_costes_click(self):
		"""Manejador del botón COSTES."""
		# TODO: Implementar navegación a vista de costes
		print("COSTES - Gestión de costes de productos")

	def _on_colores_click(self):
		"""Manejador del botón COLORES."""
		# TODO: Implementar navegación a vista de colores
		print("COLORES - Gestión de colores")

	def _on_stock_click(self):
		"""Manejador del botón STOCK."""
		# TODO: Implementar navegación a vista de stock
		print("STOCK - Gestión de stock")

	def _on_volver_click(self):
		"""Manejador del botón VOLVER."""
		self.destruir()
		if self.on_cerrar:
			self.on_cerrar()

	def destruir(self):
		"""Destruir la vista y limpiar recursos."""
		self.frame.destroy()
