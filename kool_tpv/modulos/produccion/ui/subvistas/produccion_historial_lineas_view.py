"""Subvista de historial de líneas de producción.

Muestra todas las líneas de producción con sus datos enriquecidos
(fecha, usuario, tipo, variante, color, talla, colección, sufijo, diseño, coste)
usando SearchablePaginatedNavList con VirtualNavList.
"""
import tkinter as tk
from typing import Callable, Optional
from datetime import datetime

import customtkinter as ctk

from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.produccion.services.produccion_ordenes_service import ProduccionOrdenesService
from kool_tpv.modulos.produccion.ui.subvistas.config_helper import cargar_config_produccion, get_font
from kool_tpv.utils.widgets.searchable_paginated_navlist import SearchablePaginatedNavList
from kool_tpv.utils.config_loader import load_layout_config
from kool_tpv.base_datos.money_adapter import read_from_db


class ProduccionHistorialLineasView:
	"""Subvista para mostrar el historial de líneas de producción.

	Args:
		parent: Widget padre donde se mostrará la subvista.
		db: Instancia de `Database` ya conectada.
		on_volver: Callback cuando se pulsa VOLVER.
	"""

	def __init__(self, parent, db: Database,
	             on_volver: Optional[Callable] = None,
	             keyboard_manager=None,
	             owner=None):
		self.parent = parent
		self.db = db
		self.on_volver = on_volver
		self.keyboard_manager = keyboard_manager
		self.owner = owner

		# Servicio para cargar líneas
		self._service = ProduccionOrdenesService(db)

		# Cargar configuración
		self.config = cargar_config_produccion()
		self._colors = self.config.get("colors", {})
		self._bg = self._colors.get("background", "#2c3e50")
		self._text = self._colors.get("text", "#ecf0f1")

		# Frame principal
		self.frame = ctk.CTkFrame(parent, fg_color=self._bg)
		self.frame.pack(fill="both", expand=True)

		# Título + búsqueda + lista
		self._crear_titulo()
		self._crear_busqueda()
		self._crear_lista()

		# Botón VOLVER
		self._crear_boton_volver()

		# Vincular para navegación por botón Power / Esc
		self.frame._volver = self._on_volver

		# Foco automático en el entry
		self.frame.after(100, self.entry_busqueda.focus_set)

	def _get_font(self, key: str) -> tuple:
		"""Obtener una fuente desde la configuración."""
		return get_font(self.config, key)

	def _crear_titulo(self):
		"""Crear el título de la subvista."""
		titulo = ctk.CTkLabel(
			self.frame,
			text="HISTORIAL DE LÍNEAS DE PRODUCCIÓN",
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
			placeholder_text="Buscar por nombre de diseño...",
			font=self._get_font("entry"),
			height=40
		)
		self.entry_busqueda.pack(fill="x", side="left", expand=True)
		self.entry_busqueda.bind("<Return>", self._on_buscar_enter)
		self.entry_busqueda.bind("<KP_Enter>", self._on_buscar_enter)

	def _crear_lista(self):
		"""Crear la lista de líneas usando SearchablePaginatedNavList."""
		columns = [
			("fecha", 150, "Fecha"),
			("usuario", 120, "Usuario"),
			("tipo_producto", 120, "Tipo"),
			("variante", 100, "Variante"),
			("color", 100, "Color"),
			("talla", 60, "Talla"),
			("coleccion", 120, "Colección"),
			("sufijo", 80, "Sufijo"),
			("diseno", 200, "Diseño"),
			("coste_total", 100, "Coste"),
		]

		self.search_list = SearchablePaginatedNavList(
			parent=self.frame,
			columns=columns,
			search_function=self._buscar_lineas,
			map_function=self._map_linea,
			module_name="produccion",
			page_limit=50,
			on_double_click=self._on_item_double_click,
			keyboard_manager=self.keyboard_manager,
			layout_config=load_layout_config(),
		)
		self.search_list.pack(expand=True, fill="both", padx=40, pady=(0, 10))

	def _buscar_lineas(self, texto: str) -> list:
		"""Función de búsqueda para SearchablePaginatedNavList."""
		try:
			return self._service.obtener_lineas_historial(texto.strip())
		except Exception:
			return []

	def _map_linea(self, linea: dict) -> dict:
		"""Mapear una línea de producción a dict para VirtualNavList."""
		# Formatear fecha
		fecha_str = ""
		if linea.get("fecha"):
			try:
				fecha_obj = datetime.fromisoformat(linea["fecha"])
				fecha_str = fecha_obj.strftime("%d/%m/%Y %H:%M")
			except Exception:
				fecha_str = str(linea["fecha"])

		# Formatear coste
		coste_str = f"{read_from_db(linea.get('coste_total', 0)):.2f} €"

		return {
			"id": linea.get("id"),
			"fecha": fecha_str,
			"usuario": linea.get("usuario", ""),
			"tipo_producto": linea.get("tipo_producto", ""),
			"variante": linea.get("variante", ""),
			"color": linea.get("color", ""),
			"talla": linea.get("talla", ""),
			"coleccion": linea.get("coleccion", ""),
			"sufijo": linea.get("sufijo", ""),
			"diseno": linea.get("diseno", ""),
			"coste_total": coste_str,
		}

	def _on_item_double_click(self, item_data: dict):
		"""Manejador para el doble clic en una línea: Abrir edición."""
		from kool_tpv.utils.widgets.notificaciones import ToastWidget
		linea_id = item_data.get("id")
		if not linea_id:
			return
			
		if self.owner and hasattr(self.owner, 'show_editar_linea'):
			# Al editar desde el historial, al volver queremos regresar aquí
			self.owner.show_editar_linea(linea_id, state_informe=None)
		else:
			ToastWidget.show(self.frame, "No se puede editar: falta el controlador de vistas", tipo='warning')

	def _on_buscar_enter(self, event):
		"""Enter en la búsqueda: disparar búsqueda."""
		texto = self.entry_busqueda.get()
		self.search_list.search(texto)
		return "break"

	def _crear_boton_volver(self):
		"""Crear el botón VOLVER."""
		frame_nav = ctk.CTkFrame(self.frame, fg_color=self._bg)
		frame_nav.pack(fill="x", padx=40, pady=20)

		nav_volver = self.config.get("nav_buttons", {}).get("volver", {})
		style_volver = nav_volver.get("style", {})
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

	def _on_volver(self):
		"""Manejador del botón VOLVER."""
		if self.on_volver:
			self.on_volver()

	def destruir(self):
		"""Destruir la subvista y limpiar recursos."""
		if self.keyboard_manager:
			try:
				self.keyboard_manager.clear_active_list()
			except Exception:
				pass
		self.frame.destroy()
