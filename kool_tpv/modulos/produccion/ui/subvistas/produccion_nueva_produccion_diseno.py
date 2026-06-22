"""Subvista de selección de diseño.

Contiene la clase `NuevaProduccionDisenoView` que muestra un campo de búsqueda
y una lista de diseños cargados desde la base de datos (tabla `produccion_disenos`).
Usa SearchablePaginatedNavList con VirtualNavList para navegación por teclado
consistente con el resto del proyecto.
"""
import tkinter as tk
from typing import Callable, List, Optional, Any

import customtkinter as ctk

from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.produccion.models.produccion_diseno_model import ProduccionDiseno
from kool_tpv.modulos.produccion.services.produccion_disenos_service import ProduccionDisenosService
from kool_tpv.modulos.produccion.ui.subvistas.config_helper import cargar_config_produccion, get_font, get_nav_button_config, get_nav_button_style
from kool_tpv.utils.widgets.searchable_paginated_navlist import SearchablePaginatedNavList
from kool_tpv.utils.config_loader import load_layout_config


class NuevaProduccionDisenoView:
	"""Subvista para seleccionar un diseño.

	Args:
		parent: Widget padre donde se mostrará la subvista.
		db: Instancia de `Database` ya conectada.
		keyboard_mgr: Instancia de KeyboardManager para navegación con flechas.
		on_siguiente: Callback cuando se pulsa SIGUIENTE (recibe ProduccionDiseno).
		on_volver: Callback cuando se pulsa VOLVER.
	"""

	def __init__(self, parent, db: Database,
	             keyboard_mgr=None,
	             on_siguiente: Optional[Callable[[ProduccionDiseno], None]] = None,
	             on_volver: Optional[Callable] = None):
		self.parent = parent
		self.db = db
		self.keyboard_mgr = keyboard_mgr
		self.on_siguiente = on_siguiente
		self.on_volver = on_volver
		self.diseno_seleccionado: Optional[ProduccionDiseno] = None

		# Servicio para cargar diseños desde BD
		self._service = ProduccionDisenosService(db)

		# Cargar configuración
		self.config = cargar_config_produccion()
		self._colors = self.config.get("colors", {})
		self._bg = self._colors.get("background", "#2c3e50")
		self._text = self._colors.get("text", "#ecf0f1")
		self._text_sec = self._colors.get("text_secondary", "#95a5a6")

		# Frame principal
		self.frame = ctk.CTkFrame(parent, fg_color=self._bg)
		self.frame.pack(fill="both", expand=True)

		# Título + búsqueda + lista
		self._crear_titulo()
		self._crear_busqueda()
		self._crear_lista_disenos()

		# Botones de navegación
		self._crear_botones_navegacion()

		# Foco automático en el entry
		self.frame.after(100, self.entry_busqueda.focus_set)

	def _get_font(self, key: str) -> tuple:
		"""Obtener una fuente desde la configuración."""
		return get_font(self.config, key)

	def _crear_titulo(self):
		"""Crear el título de la subvista."""
		titulo = ctk.CTkLabel(
			self.frame,
			text="SELECCIONA DISEÑO",
			font=self._get_font("title"),
			text_color=self._text,
			fg_color=self._bg
		)
		titulo.pack(pady=(20, 10))

	def _crear_busqueda(self):
		"""Crear el campo de búsqueda."""
		frame_search = ctk.CTkFrame(self.frame, fg_color=self._bg)
		frame_search.pack(fill="x", padx=40, pady=(0, 10))

		self.entry_busqueda = ctk.CTkEntry(
			frame_search,
			placeholder_text="Buscar por código, nombre o colección...",
			font=self._get_font("entry"),
			height=40
		)
		self.entry_busqueda.pack(fill="x", side="left", expand=True)
		self.entry_busqueda.bind("<Return>", self._on_buscar_enter)
		self.entry_busqueda.bind("<KP_Enter>", self._on_buscar_enter)

		btn_nuevo = ctk.CTkButton(
			master=frame_search,
			text="NUEVO",
			command=self._on_nuevo_diseno,
			width=80,
			height=40,
			fg_color="#552583",
			hover_color="#8e44ad",
			cursor="hand2"
		)
		btn_nuevo.pack(side="right", padx=(10, 0))

	def _crear_lista_disenos(self):
		"""Crear la lista de diseños usando SearchablePaginatedNavList."""
		columns = [
			("nombre", 300, "Diseño"),
			("coleccion", 150, "Colección"),
			("variante", 100, "Variante"),
		]

		self.search_list = SearchablePaginatedNavList(
			parent=self.frame,
			columns=columns,
			search_function=self._buscar_disenos,
			map_function=self._map_diseno,
			module_name="tpv",
			page_limit=50,
			on_double_click=self._on_diseno_doble_clic,
			keyboard_manager=self.keyboard_mgr,
			layout_config=load_layout_config(),
		)
		self.search_list.pack(expand=True, fill="both", padx=40, pady=(0, 10))

		nav = getattr(self.search_list, 'nav_list', None)
		if nav and hasattr(nav, 'bind_return'):
			nav.bind_return(self._on_diseno_return)

	def _buscar_disenos(self, texto: str) -> List[ProduccionDiseno]:
		"""Función de búsqueda para SearchablePaginatedNavList."""
		try:
			if texto.strip():
				return self._service.buscar(texto.strip())
			else:
				return self._service.obtener_activos()
		except Exception:
			return []

	def _map_diseno(self, diseno: ProduccionDiseno) -> dict:
		"""Mapear un ProduccionDiseno a dict para VirtualNavList."""
		return {
			"nombre": diseno.nombre or "",
			"coleccion": diseno.coleccion or "",
			"variante": diseno.variante or "",
			"_obj": diseno,
		}

	def _on_buscar_enter(self, event):
		"""Enter en la búsqueda: disparar búsqueda y mover foco a la lista."""
		texto = self.entry_busqueda.get()
		self.search_list.search(texto)
		nav = getattr(self.search_list, 'nav_list', None)
		if nav:
			try:
				nav._canvas.focus_set()
			except Exception:
				pass
		return "break"

	def _limpiar_busqueda(self):
		"""Limpiar el campo de búsqueda y recargar todos."""
		self.entry_busqueda.delete(0, "end")
		self.search_list.search("")
		self.entry_busqueda.focus_set()

	def _on_nuevo_diseno(self):
		"""Abrir la vista de creación de diseño."""
		from kool_tpv.modulos.produccion.ui.subvistas.produccion_diseno_nuevo import DisenoNuevoView
		
		# Ocultar temporalmente el contenido de esta subvista
		self.frame.pack_forget()
		
		# Crear la vista de nuevo diseño en el mismo parent
		self._vista_nuevo = DisenoNuevoView(
			self.parent,
			db=self.db,
			on_cerrar=self._on_nuevo_diseno_cerrar
		)

	def _on_nuevo_diseno_cerrar(self, diseno: Optional[ProduccionDiseno] = None):
		"""Callback al cerrar la vista de nuevo diseño."""
		if self._vista_nuevo:
			self._vista_nuevo.destruir()
			self._vista_nuevo = None
		
		# Mostrar de nuevo esta subvista si no hay diseño, o saltar si lo hay
		if diseno:
			if self.on_siguiente:
				self.on_siguiente(diseno)
		else:
			self.frame.pack(fill="both", expand=True)
			self.entry_busqueda.focus_set()

	def _on_diseno_doble_clic(self, data: dict):
		"""Doble clic en un diseño de la lista."""
		diseno = data.get("_obj") if data else None
		if diseno and self.on_siguiente:
			self.diseno_seleccionado = diseno
			self.on_siguiente(diseno)

	def _on_diseno_return(self):
		"""Enter en la lista: seleccionar y avanzar."""
		nav = getattr(self.search_list, 'nav_list', None)
		if nav:
			data = nav.get_selected_data()
			if data:
				diseno = data.get("_obj")
				if diseno and self.on_siguiente:
					self.diseno_seleccionado = diseno
					self.on_siguiente(diseno)

	def _crear_botones_navegacion(self):
		"""Crear los botones de navegación inferior."""
		frame_nav = ctk.CTkFrame(self.frame, fg_color=self._bg)
		frame_nav.pack(fill="x", padx=40, pady=20)

		# Botón VOLVER
		nav_volver = get_nav_button_config(self.config, "volver")
		style_volver = get_nav_button_style(self.config, nav_volver.get("style_key", "volver"))
		btn_volver = ctk.CTkButton(
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
			command=self._on_volver
		)
		btn_volver.pack(side=tk.LEFT, padx=10)

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
			command=self._on_siguiente
		)
		self.btn_siguiente.pack(side=tk.RIGHT, padx=10)

	# --- Callbacks de navegación ---

	def _on_siguiente(self):
		"""Manejador del botón SIGUIENTE."""
		if self.diseno_seleccionado and self.on_siguiente:
			self.on_siguiente(self.diseno_seleccionado)

	def _on_volver(self):
		"""Manejador del botón VOLVER."""
		if self.on_volver:
			self.on_volver()

	def obtener_seleccion(self) -> Optional[ProduccionDiseno]:
		"""Obtener el diseño seleccionado.

		Returns:
			Objeto ProduccionDiseno o None.
		"""
		return self.diseno_seleccionado

	def destruir(self):
		"""Destruir la subvista y limpiar recursos."""
		if self.keyboard_mgr:
			try:
				self.keyboard_mgr.clear_active_list()
			except Exception:
				pass
		self.frame.destroy()
