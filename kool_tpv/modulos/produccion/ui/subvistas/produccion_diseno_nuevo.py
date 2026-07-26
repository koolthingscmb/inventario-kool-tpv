"""Subvista para crear un nuevo diseño.

Contiene la clase `DisenoNuevoView` que muestra SearchableCombos para
colección, sufijo y tipo_producto, un entry para el nombre del diseño,
y un botón GUARDAR que persiste via ProduccionDisenosService.
"""
import logging
import tkinter as tk
from typing import Callable, Optional, List, Tuple

import customtkinter as ctk

from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.produccion.models.produccion_diseno_model import ProduccionDiseno, DisenoCoste
from kool_tpv.modulos.produccion.services.produccion_disenos_service import ProduccionDisenosService
from kool_tpv.modulos.produccion.services.produccion_tipos_service import ProduccionTiposService
from kool_tpv.modulos.produccion.services.produccion_tipos_variantes_service import ProduccionTiposVariantesService
from kool_tpv.modulos.produccion.repositories.produccion_colecciones_repository import ProduccionColeccionesRepository
from kool_tpv.modulos.produccion.repositories.produccion_sufijos_repository import ProduccionSufijosRepository
from kool_tpv.modulos.produccion.repositories.produccion_metodos_repository import ProduccionMetodosRepository
from kool_tpv.modulos.produccion.ui.subvistas.config_helper import cargar_config_produccion, get_font, get_nav_button_config, get_nav_button_style
from kool_tpv.utils.widgets.searchable_paginated_navlist import SearchablePaginatedNavList
from kool_tpv.utils.widgets.notificaciones.toast_widget import ToastWidget
from kool_tpv.base_datos.money_adapter import prepare_for_db, read_from_db


def _normalizar(texto: str) -> str:
	"""Normalizar texto: strip + title para consistencia en BD."""
	return texto.strip().title()


class DisenoNuevoView:
	"""Vista para crear un nuevo diseño.

	Args:
		parent: Widget padre.
		db: Instancia de Database.
		on_cerrar: Callback al cerrar/guardar correctamente.
	"""

	def __init__(self, parent, db: Database, on_cerrar: Optional[Callable[[Optional[ProduccionDiseno]], None]] = None):
		self.parent = parent
		self.db = db
		self.on_cerrar = on_cerrar
		self.service = ProduccionDisenosService(db)
		self.tipos_service = ProduccionTiposService(db)
		self.variantes_service = ProduccionTiposVariantesService(db)
		self.colecciones_repo = ProduccionColeccionesRepository(db)
		self.sufijos_repo = ProduccionSufijosRepository(db)
		self.metodos_repo = ProduccionMetodosRepository(db)

		# Estado de selección para chips
		self._coleccion_seleccionada: Optional[str] = None
		self._sufijo_seleccionado: Optional[str] = None

		# Cachés para evitar latencia
		self._colecciones_cache = {c.id: c.nombre for c in self.colecciones_repo.get_activas()}
		self._sufijos_cache = {s.id: s.nombre for s in self.sufijos_repo.get_activos()}
		self._metodos_cache = self.metodos_repo.get_activos()
		self._stats_cache = {}  # Caché temporal para estadísticas de la lista actual

		# Estado de edición
		self._diseno_cargado: Optional[ProduccionDiseno] = None
		self._cache_tipos = {t.id: t.nombre for t in self.tipos_service.obtener_activos()}
		self._coste_items: list = []  # Lista de dicts con datos de cada coste
		self._metodos_entries: dict = {} # {metodo_id: entry_widget}

		# Cargar configuración
		self.config = cargar_config_produccion()
		self._colors = self.config.get("colors", {})
		self._bg = self._colors.get("background", "#2c3e50")
		self._text = self._colors.get("text", "#ecf0f1")
		self._text_sec = self._colors.get("text_secondary", "#95a5a6")

		# Frame principal
		self.frame = ctk.CTkFrame(parent, fg_color=self._bg)
		self.frame.pack(fill="both", expand=True)

		# Reutilizar caches ya construidas (evita 3 consultas duplicadas)
		self._colecciones = list(self._colecciones_cache.values())
		self._sufijos = list(self._sufijos_cache.values())
		self._tipos = list(self._cache_tipos.items())

		# UI
		self._crear_formulario()
		self._render_chips_colecciones()
		self._render_chips_sufijos()

		# Foco inicial
		self.frame.after(100, lambda: self._entry_nombre.focus_set())

	def _get_font(self, key: str) -> tuple:
		return get_font(self.config, key)

	def _cargar_colecciones(self) -> List[str]:
		"""Obtener colecciones activas desde la tabla produccion_colecciones."""
		try:
			return [c.nombre for c in self.colecciones_repo.get_activas()]
		except Exception:
			logging.exception("Error cargando colecciones")
			return []

	def _cargar_sufijos(self) -> List[str]:
		"""Obtener sufijos activos desde la tabla produccion_sufijos."""
		try:
			return [s.nombre for s in self.sufijos_repo.get_activos()]
		except Exception:
			logging.exception("Error cargando sufijos")
			return []

	def _cargar_tipos(self) -> List[Tuple[int, str]]:
		"""Obtener tipos de producto activos como (id, nombre)."""
		try:
			tipos = self.tipos_service.obtener_activos()
			return [(t.id, t.nombre) for t in tipos]
		except Exception:
			logging.exception("Error cargando tipos")
			return []

	def _crear_formulario(self):
		"""Crear los campos del formulario organizados en frames independientes."""
		# 1. FRAME SUPERIOR (Nombre y Botones +)
		self.top_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
		self.top_frame.pack(side="top", fill="x", padx=40, pady=(10, 5))

		# Fila superior: Nombre + COMPROBAR + COLECCIÓN + SUFIJO
		lbl_nombre = ctk.CTkLabel(
			self.top_frame,
			text="CREAR DISEÑO O BUSCAR DISEÑO",
			font=self._get_font("label"),
			text_color=self._text_sec
		)
		lbl_nombre.pack(anchor="w", pady=(0, 2))

		controls_row = ctk.CTkFrame(self.top_frame, fg_color="transparent")
		controls_row.pack(fill="x")

		self._entry_nombre = ctk.CTkEntry(
			controls_row,
			font=self._get_font("entry")
		)
		self._entry_nombre.pack(side="left", fill="x", expand=True, padx=(0, 10))
		_entry_nombre_inner = self._entry_nombre._entry if hasattr(self._entry_nombre, '_entry') else self._entry_nombre
		_entry_nombre_inner.bind("<Tab>", self._on_tab_next)
		_entry_nombre_inner.bind("<Return>", lambda e: self._on_comprobar())

		self.btn_comprobar = ctk.CTkButton(
			controls_row,
			text="COMPROBAR",
			width=120,
			command=self._on_comprobar
		)
		# No empaquetamos el botón, lo dejamos solo para el binding de Return si fuera necesario, 
		# pero el usuario prefiere el botón abajo. Lo eliminamos visualmente.

		self._btn_add_coleccion = ctk.CTkButton(
			controls_row,
			text="+ COLECCIÓN",
			width=140,
			font=self._get_font("button"),
			command=self._on_add_coleccion
		)
		self._btn_add_coleccion.pack(side="left", padx=(0, 10))

		self._btn_add_sufijo = ctk.CTkButton(
			controls_row,
			text="+ SUFIJO",
			width=140,
			font=self._get_font("button"),
			command=self._on_add_sufijo
		)
		self._btn_add_sufijo.pack(side="left")

		# Botones Eliminar y Mostrar
		self._btn_eliminar = ctk.CTkButton(
			controls_row,
			text="ELIMINAR",
			width=100,
			font=self._get_font("button"),
			fg_color=self.config.get("colors", {}).get("buttons", {}).get("cancelar", {}).get("bg", "#e74c3c"),
			hover_color=self.config.get("colors", {}).get("buttons", {}).get("cancelar", {}).get("hover", "#c0392b"),
			command=self._on_eliminar
		)
		self._btn_eliminar.pack(side="left", padx=(20, 10))

		self._btn_mostrar = ctk.CTkButton(
			controls_row,
			text="MOSTRAR",
			width=100,
			font=self._get_font("button"),
			fg_color=self.config.get("colors", {}).get("buttons", {}).get("nuevo", {}).get("bg", "#3498db"),
			hover_color=self.config.get("colors", {}).get("buttons", {}).get("nuevo", {}).get("hover", "#2980b9"),
			command=self._on_mostrar
		)
		self._btn_mostrar.pack(side="left")

		# 2. FRAME DE LISTA (VirtualNavList) - El que se expande
		self.list_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
		self.list_frame.pack(side="top", fill="both", padx=40, pady=5)

		from kool_tpv.utils.config_loader import load_layout_config
		root = self.frame.winfo_toplevel()
		from kool_tpv.utils.keyboard_manager import KeyboardManager
		_km = getattr(root, 'keyboard_manager', None)

		columns = [
			("codigo", 100, "Código"),
			("nombre", 270, "Nombre"),
			("coleccion_nombre", 120, "Colección"),
			("sufijo_nombre", 100, "Sufijo"),
			("total_producido", 80, "Producciones")
		]

		self._paginated_list = SearchablePaginatedNavList(
			parent=self.list_frame,
			columns=columns,
			search_function=self._buscar_disenos_paginado,
			map_function=self._map_diseno_para_lista,
			module_name="produccion",
			page_limit=50,
			on_double_click=self._on_diseno_double_click,
			keyboard_manager=_km,
			layout_config=load_layout_config()
		)
		self._paginated_list.pack(fill="both", expand=True)
		self._nav_list = self._paginated_list.nav_list

		# 3. FRAME DE CHIPS (Colecciones y Sufijos)
		self.chips_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
		self.chips_frame.pack(side="top", fill="x", padx=40, pady=5)
		self._crear_chips_section(self.chips_frame)

		# 4. FRAME INFERIOR (Acción Principal)
		self.bottom_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
		self.bottom_frame.pack(side="top", fill="both", expand=True, padx=40, pady=(5, 20))

		# Rejilla de Métodos de Producción
		self._frame_metodos = ctk.CTkFrame(self.bottom_frame, fg_color="transparent")
		self._frame_metodos.pack(fill="x", pady=(0, 10))
		self._render_rejilla_metodos()

		buttons_row = ctk.CTkFrame(self.bottom_frame, fg_color="transparent")
		buttons_row.pack(fill="x", pady=10)

		self.btn_cancelar = ctk.CTkButton(
			buttons_row,
			text="CANCELAR",
			width=150,
			height=50,
			font=self._get_font("button"),
			fg_color=self.config.get("colors", {}).get("buttons", {}).get("cancelar", {}).get("bg", "#e74c3c"),
			hover_color=self.config.get("colors", {}).get("buttons", {}).get("cancelar", {}).get("hover", "#c0392b"),
			command=self._on_cancelar
		)
		self.btn_cancelar.pack(side="left", padx=(0, 10))

		self.btn_accion_principal = ctk.CTkButton(
			buttons_row,
			text="GUARDAR NUEVO DISEÑO",
			height=50,
			font=self._get_font("button"),
			command=self._on_accion_principal
		)
		self.btn_accion_principal.pack(side="left", fill="x", expand=True)
		self._update_main_button()

	def _crear_chips_section(self, parent):
		"""Crear la sección de chips."""
		self._chips_container = ctk.CTkFrame(parent, fg_color="transparent")
		self._chips_container.pack(fill="x", expand=False)

		# Grid 2 columnas
		self._chips_container.grid_columnconfigure(0, weight=1)
		self._chips_container.grid_columnconfigure(1, weight=1)

		# Columna COLECCIONES
		col_left = ctk.CTkFrame(self._chips_container, fg_color="transparent")
		col_left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

		lbl_col = ctk.CTkLabel(
			col_left, text="COLECCIONES",
			font=self._get_font("label"),
			text_color=self._text_sec
		)
		lbl_col.pack(pady=(0, 5))

		self._frame_chips_colecciones = ctk.CTkFrame(col_left, fg_color="transparent")
		self._frame_chips_colecciones.pack(fill="both", expand=True)

		# Columna SUFIJOS
		col_right = ctk.CTkFrame(self._chips_container, fg_color="transparent")
		col_right.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

		lbl_suf = ctk.CTkLabel(
			col_right, text="SUFIJOS",
			font=self._get_font("label"),
			text_color=self._text_sec
		)
		lbl_suf.pack(pady=(0, 5))

		self._frame_chips_sufijos = ctk.CTkFrame(col_right, fg_color="transparent")
		self._frame_chips_sufijos.pack(fill="both", expand=True)

	COL_COLS = 6

	def _render_chips_colecciones(self):
		"""Renderizar chips de colecciones activas en grid de 10 columnas."""
		for w in self._frame_chips_colecciones.winfo_children():
			w.destroy()

		# Colores desde config
		chips_cfg = self.config.get("chips", {}).get("diseno", {})
		default_cfg = chips_cfg.get("default", {})
		selected_cfg = chips_cfg.get("selected", {})

		colecciones_nombres = list(self._colecciones_cache.values())

		container = ctk.CTkFrame(self._frame_chips_colecciones, fg_color="transparent")
		container.pack(fill="both", expand=True)

		for c in range(self.COL_COLS):
			container.grid_columnconfigure(c, weight=1)

		for i, nombre in enumerate(colecciones_nombres):
			is_selected = (nombre == self._coleccion_seleccionada)
			row = i // self.COL_COLS
			col = i % self.COL_COLS

			bg_color = selected_cfg.get("bg", "#552583") if is_selected else default_cfg.get("bg", "#1a1a2e")
			text_color = selected_cfg.get("text", "#ffffff") if is_selected else default_cfg.get("text", "#e0e0e0")
			border_color = selected_cfg.get("border", "#C77BFF") if is_selected else default_cfg.get("border", "#552583")
			hover_color = selected_cfg.get("hover", "#8e44ad") if is_selected else default_cfg.get("hover", "#C77BFF")

			chip = ctk.CTkButton(
				container,
				text=nombre,
				width=0,
				height=32,
				corner_radius=16,
				fg_color=bg_color,
				text_color=text_color,
				border_color=border_color,
				border_width=2 if is_selected else 1,
				hover_color=hover_color,
				font=self._get_font("button_small") if "button_small" in self.config.get("fonts", {}) else (None, 12),
				command=lambda name=nombre: self._on_chip_coleccion_click(name)
			)
			chip.grid(row=row, column=col, padx=3, pady=3, sticky="ew")
			chip.bind("<Double-Button-1>", lambda e, name=nombre: self._on_chip_coleccion_doble_click(name))

	SUF_COLS = 10

	def _render_chips_sufijos(self):
		"""Renderizar chips de sufijos activos en grid de 12 columnas."""
		for w in self._frame_chips_sufijos.winfo_children():
			w.destroy()

		# Colores desde config
		chips_cfg = self.config.get("chips", {}).get("diseno", {})
		default_cfg = chips_cfg.get("default", {})
		selected_cfg = chips_cfg.get("selected", {})

		sufijos_nombres = list(self._sufijos_cache.values())

		container = ctk.CTkFrame(self._frame_chips_sufijos, fg_color="transparent")
		container.pack(fill="both", expand=True)

		for c in range(self.SUF_COLS):
			container.grid_columnconfigure(c, weight=1)

		for i, nombre in enumerate(sufijos_nombres):
			is_selected = (nombre == self._sufijo_seleccionado)
			row = i // self.SUF_COLS
			col = i % self.SUF_COLS

			bg_color = selected_cfg.get("bg", "#552583") if is_selected else default_cfg.get("bg", "#1a1a2e")
			text_color = selected_cfg.get("text", "#ffffff") if is_selected else default_cfg.get("text", "#e0e0e0")
			border_color = selected_cfg.get("border", "#C77BFF") if is_selected else default_cfg.get("border", "#552583")
			hover_color = selected_cfg.get("hover", "#8e44ad") if is_selected else default_cfg.get("hover", "#C77BFF")

			chip = ctk.CTkButton(
				container,
				text=nombre,
				width=0,
				height=32,
				corner_radius=16,
				fg_color=bg_color,
				text_color=text_color,
				border_color=border_color,
				border_width=2 if is_selected else 1,
				hover_color=hover_color,
				font=self._get_font("button_small") if "button_small" in self.config.get("fonts", {}) else (None, 12),
				command=lambda name=nombre: self._on_chip_sufijo_click(name)
			)
			chip.grid(row=row, column=col, padx=3, pady=3, sticky="ew")
			chip.bind("<Double-Button-1>", lambda e, name=nombre: self._on_chip_sufijo_doble_click(name))

	def _on_chip_coleccion_doble_click(self, nombre):
		"""Doble clic en chip de colección: renombrar."""
		from kool_tpv.utils.dialogs import InputDialog
		col = self.colecciones_repo.get_por_nombre(nombre)
		if not col:
			return

		def on_rename(nuevo_nombre):
			if nuevo_nombre and nuevo_nombre.strip():
				self.colecciones_repo.actualizar(col.id, nuevo_nombre.strip(), 1)
				self._colecciones_cache = {c.id: c.nombre for c in self.colecciones_repo.get_activas()}
				self._colecciones = list(self._colecciones_cache.values())
				self._render_chips_colecciones()
				ToastWidget.show(self.frame, "Colección renombrada", tipo='success')

		InputDialog(
			self.frame,
			titulo="RENOMBRAR COLECCIÓN",
			mensaje=f"NOMBRE ACTUAL: {nombre}",
			valor_defecto=nombre,
			callback=on_rename
		)

	def _on_chip_sufijo_doble_click(self, nombre):
		"""Doble clic en chip de sufijo: renombrar."""
		from kool_tpv.utils.dialogs import InputDialog
		suf = self.sufijos_repo.get_por_nombre(nombre)
		if not suf:
			return

		def on_rename(nuevo_nombre):
			if nuevo_nombre and nuevo_nombre.strip():
				self.sufijos_repo.actualizar(suf.id, nuevo_nombre.strip(), 1)
				self._sufijos_cache = {s.id: s.nombre for s in self.sufijos_repo.get_activos()}
				self._sufijos = list(self._sufijos_cache.values())
				self._render_chips_sufijos()
				ToastWidget.show(self.frame, "Sufijo renombrado", tipo='success')

		InputDialog(
			self.frame,
			titulo="RENOMBRAR SUFIJO",
			mensaje=f"NOMBRE ACTUAL: {nombre}",
			valor_defecto=nombre,
			callback=on_rename
		)

	def _render_rejilla_metodos(self):
		"""Renderizar rejilla de métodos de producción con sus costes usando widgets CTk."""
		for w in self._frame_metodos.winfo_children():
			w.destroy()
		
		self._metodos_entries = {}
		metodos = self._metodos_cache
		
		# Grid config: 3 columnas
		cols = 3
		for i in range(cols):
			self._frame_metodos.grid_columnconfigure(i, weight=1)

		# Título sección
		lbl_title = ctk.CTkLabel(
			self._frame_metodos, 
			text="COSTES POR MÉTODO DE PRODUCCIÓN",
			font=self._get_font("label"),
			text_color=self._text_sec
		)
		lbl_title.grid(row=0, column=0, columnspan=cols, pady=(0, 10), sticky="w")

		# Si hay un diseño cargado, obtener sus costes
		costes_actuales = {}
		if self._diseno_cargado:
			costes_actuales = self.metodos_repo.get_costes_por_diseno(self._diseno_cargado.codigo)

		row = 1
		col = 0
		for m in metodos:
			# Contenedor para cada método (usamos CTkFrame para coherencia visual)
			m_frame = ctk.CTkFrame(self._frame_metodos, fg_color="transparent")
			m_frame.grid(row=row, column=col, padx=10, pady=5, sticky="ew")
			
			lbl = ctk.CTkLabel(
				m_frame, text=f"{m.nombre}:",
				font=self._get_font("label")
			)
			lbl.pack(side="left", padx=(0, 5))
			
			entry = ctk.CTkEntry(
				m_frame, width=100,
				font=self._get_font("entry"),
				justify="right"
			)
			entry.pack(side="right", fill="x", expand=True)
			
			# Valor inicial
			valor_db = costes_actuales.get(m.id, 0)
			entry.insert(0, f"{read_from_db(valor_db):.2f}")
			
			self._metodos_entries[m.id] = entry
			
			# Bindings
			_inner = entry._entry if hasattr(entry, '_entry') else entry

			col += 1
			if col >= cols:
				col = 0
				row += 1

		# Botón + MÉTODO
		btn_add = ctk.CTkButton(
			self._frame_metodos,
			text="+ MÉTODO",
			width=100,
			fg_color=self.config.get("colors", {}).get("buttons", {}).get("nuevo", {}).get("bg", "#3498db"),
			command=self._on_add_metodo
		)
		btn_add.grid(row=row, column=col, padx=10, pady=5, sticky="w")
		

	def _on_chip_coleccion_click(self, nombre):
		"""Seleccionar/Deseleccionar chip de colección."""
		if self._coleccion_seleccionada == nombre:
			self._coleccion_seleccionada = None
		else:
			self._coleccion_seleccionada = nombre
		self._render_chips_colecciones()

	def _on_chip_sufijo_click(self, nombre):
		"""Seleccionar/Deseleccionar chip de sufijo."""
		if self._sufijo_seleccionado == nombre:
			self._sufijo_seleccionado = None
		else:
			self._sufijo_seleccionado = nombre
		self._render_chips_sufijos()

	def _on_eliminar(self):
		"""Lógica para eliminar la colección o sufijo seleccionado."""
		if not self._coleccion_seleccionada and not self._sufijo_seleccionado:
			ToastWidget.show(self.frame, "Selecciona una colección o sufijo para eliminar", tipo="warning")
			return

		# Caso 1: Eliminar Colección
		if self._coleccion_seleccionada:
			col_obj = self.colecciones_repo.get_por_nombre(self._coleccion_seleccionada)
			if not col_obj:
				return
			
			# Check dependencias
			disenos = self.service.obtener_por_coleccion(col_obj.id)
			if disenos:
				nombres = ", ".join([d.nombre for d in disenos[:5]])
				if len(disenos) > 5:
					nombres += "..."
				ToastWidget.show(
					self.frame, 
					f"Error: {len(disenos)} diseños usan esta colección ({nombres})", 
					tipo="error"
				)
				return
			
			# Eliminar
			if self.colecciones_repo.eliminar(col_obj.id):
				self._coleccion_seleccionada = None
				self._colecciones_cache = {c.id: c.nombre for c in self.colecciones_repo.get_activas()}
				self._colecciones = list(self._colecciones_cache.values())
				self._render_chips_colecciones()
				ToastWidget.show(self.frame, "Colección eliminada", tipo="success")
			else:
				ToastWidget.show(self.frame, "Error al eliminar colección", tipo="error")
			return

		# Caso 2: Eliminar Sufijo
		if self._sufijo_seleccionado:
			suf_obj = self.sufijos_repo.get_por_nombre(self._sufijo_seleccionado)
			if not suf_obj:
				return
			
			# Check dependencias
			disenos = self.service.obtener_por_sufijo(suf_obj.id)
			if disenos:
				nombres = ", ".join([d.nombre for d in disenos[:5]])
				if len(disenos) > 5:
					nombres += "..."
				ToastWidget.show(
					self.frame, 
					f"Error: {len(disenos)} diseños usan este sufijo ({nombres})", 
					tipo="error"
				)
				return
			
			# Eliminar
			if self.sufijos_repo.eliminar(suf_obj.id):
				self._sufijo_seleccionado = None
				self._sufijos_cache = {s.id: s.nombre for s in self.sufijos_repo.get_activos()}
				self._sufijos = list(self._sufijos_cache.values())
				self._render_chips_sufijos()
				ToastWidget.show(self.frame, "Sufijo eliminado", tipo="success")
			else:
				ToastWidget.show(self.frame, "Error al eliminar sufijo", tipo="error")
			return

	def _on_mostrar(self):
		"""Filtrar la lista de diseños por la colección o sufijo seleccionado."""
		if not self._coleccion_seleccionada and not self._sufijo_seleccionado:
			# Si no hay nada seleccionado, mostramos todos (limpiar filtro)
			self._paginated_list.search("")
			return

		# La búsqueda actual usa un filtro de texto. Necesitamos que soporte filtrar por ID de colección/sufijo
		# o simplemente pasar el nombre al search si el repo ya lo soporta.
		# Mirando el repo, el método 'buscar' busca por nombre. 
		# Podríamos inyectar una lógica de filtro en _buscar_disenos_paginado.
		
		self._paginated_list.search("") # Forzar refresco con los seleccionados

	def _on_tab_next(self, event):
		"""Tab: mover foco al siguiente widget."""
		widgets = [
			self._entry_nombre._entry if hasattr(self._entry_nombre, '_entry') else self._entry_nombre,
			self.btn_comprobar,
			self._btn_add_coleccion,
			self._btn_add_sufijo
		]
		current = event.widget
		try:
			idx = widgets.index(current)
		except ValueError:
			for i, w in enumerate(widgets):
				try:
					if w is current or (hasattr(w, 'winfo_containing') and current is not None):
						if hasattr(w, '_entry') and current is w._entry:
							idx = i
							break
				except Exception:
					pass
			else:
				idx = 0
		next_idx = (idx + 1) % len(widgets)
		next_widget = widgets[next_idx]
		try:
			if hasattr(next_widget, '_entry'):
				next_widget._entry.focus_set()
			elif hasattr(next_widget, 'focus_set'):
				next_widget.focus_set()
		except Exception:
			try:
				next_widget.focus_set()
			except Exception:
				pass
		return "break"

	def _on_comprobar(self):
		"""Buscar diseños por el nombre introducido usando el componente paginado."""
		nombre = self._entry_nombre.get().strip()
		# _cache_tipos ya cargado en __init__
		
		# Al buscar de nuevo, reseteamos el estado de "diseño cargado" 
		# para que el botón vuelva a "GUARDAR NUEVO"
		self._diseno_cargado = None
		self._update_main_button()
		
		# Ejecutar búsqueda a través del widget
		self._paginated_list.search(nombre)
		
		# Mostrar toast si no hay resultados y hay un filtro
		if nombre and not self._paginated_list.nav_list._all_data:
			ToastWidget.show(self.frame, "NO SE ENCONTRÓ DISEÑO", tipo="warning")

	def _buscar_disenos_paginado(self, filtro: str) -> List[ProduccionDiseno]:
		"""Función de búsqueda para SearchablePaginatedNavList."""
		# Caso 1: Filtro de texto (prioritario)
		if filtro.strip():
			disenos = self.service.buscar(filtro.strip())
		# Caso 2: Filtros por chips (si hay seleccionados y no hay texto)
		elif self._coleccion_seleccionada or self._sufijo_seleccionado:
			col_id = None
			if self._coleccion_seleccionada:
				col_obj = self.colecciones_repo.get_por_nombre(self._coleccion_seleccionada)
				col_id = col_obj.id if col_obj else None
			
			suf_id = None
			if self._sufijo_seleccionado:
				suf_obj = self.sufijos_repo.get_por_nombre(self._sufijo_seleccionado)
				suf_id = suf_obj.id if suf_obj else None
			
			# Filtrar activos
			todos = self.service.obtener_activos()
			disenos = []
			for d in todos:
				match_col = (col_id is None or d.coleccion_id == col_id)
				match_suf = (suf_id is None or d.sufijo_id == suf_id)
				if match_col and match_suf:
					disenos.append(d)
		# Caso 3: Todos
		else:
			disenos = self.service.obtener_activos()
		
		# Pre-cargar estadísticas para la lista actual
		codigos = [d.codigo for d in disenos]
		self._stats_cache = self.service.obtener_estadisticas_disenos(codigos)
		
		return disenos

	def _map_diseno_para_lista(self, r: ProduccionDiseno) -> dict:
		"""Función de mapeo para SearchablePaginatedNavList."""
		coleccion_nombre = self._get_coleccion_nombre(r.coleccion_id)
		sufijo_nombre = self._get_sufijo_nombre(r.sufijo_id) if r.sufijo_id else ""
		
		# Estadísticas desde la caché pre-cargada en _buscar_disenos_paginado
		stats = self._stats_cache.get(r.codigo, {"total_producido": 0})
		total_producido = stats["total_producido"]

		return {
			"codigo": r.codigo,
			"nombre": r.nombre,
			"coleccion_nombre": coleccion_nombre,
			"sufijo_nombre": sufijo_nombre,
			"total_producido": total_producido,
			"obj": r
		}

	def _update_main_button(self):
		"""Actualizar texto y estilo del botón principal según el estado."""
		if self._diseno_cargado:
			self.btn_accion_principal.configure(
				text="MODIFICAR DISEÑO",
				fg_color=self.config.get("colors", {}).get("buttons", {}).get("costes", {}).get("bg", "#f39c12"),
				hover_color=self.config.get("colors", {}).get("buttons", {}).get("costes", {}).get("hover", "#d68910")
			)
		else:
			self.btn_accion_principal.configure(
				text="GUARDAR NUEVO DISEÑO",
				fg_color=self.config.get("colors", {}).get("buttons", {}).get("confirmar", {}).get("bg", "#27ae60"),
				hover_color=self.config.get("colors", {}).get("buttons", {}).get("confirmar", {}).get("hover", "#2ecc71")
			)

	def _on_cancelar(self):
		"""Cancelar y volver a la vista anterior sin guardar."""
		if self.on_cerrar:
			self.on_cerrar(None)

	def _on_accion_principal(self):
		"""Lógica del botón principal: Guardar o Modificar."""
		self._on_guardar()

	def _on_guardar(self):
		"""Guardar o Modificar el diseño."""
		nombre = self._entry_nombre.get().strip()
		coleccion_nombre = self._coleccion_seleccionada
		sufijo_nombre = self._sufijo_seleccionado

		if not nombre:
			ToastWidget.show(self.frame, "El nombre del diseño es obligatorio", tipo="warning")
			self._entry_nombre.focus_set()
			return
		if not coleccion_nombre:
			ToastWidget.show(self.frame, "La colección es obligatoria", tipo="warning")
			return

		# Resolver IDs desde los nombres seleccionados en chips
		coleccion_obj = self.colecciones_repo.get_por_nombre(coleccion_nombre)
		coleccion_id = coleccion_obj.id if coleccion_obj else None
		
		sufijo_id = None
		if sufijo_nombre:
			sufijo_obj = self.sufijos_repo.get_por_nombre(sufijo_nombre)
			sufijo_id = sufijo_obj.id if sufijo_obj else None

		if not coleccion_id:
			ToastWidget.show(self.frame, "Error al resolver la colección", tipo="error")
			return

		# Recopilar tipos_ids desde los ítems de coste
		tipos_ids = list(set(item["tipo_id"] for item in self._coste_items))
		
		logging.info(f"[PRODUCCION] Guardando diseño: nombre='{nombre}', coleccion='{coleccion_nombre}' (ID={coleccion_id}), sufijo='{sufijo_nombre}' (ID={sufijo_id}), tipos={tipos_ids}")

		if self._diseno_cargado:
			# MODO MODIFICAR
			logging.info(f"[PRODUCCION] Modo MODIFICAR: codigo='{self._diseno_cargado.codigo}'")
			ok = self.service.actualizar(
				codigo=self._diseno_cargado.codigo,
				coleccion_id=coleccion_id,
				nombre=nombre,
				sufijo_id=sufijo_id,
				tipos=tipos_ids
			)
			if ok:
				# Guardar costes por método
				for metodo_id, entry in self._metodos_entries.items():
					try:
						coste_val = float(entry.get().replace(',', '.'))
						self.metodos_repo.guardar_coste_diseno(
							self._diseno_cargado.codigo,
							metodo_id,
							prepare_for_db(coste_val)
						)
					except ValueError:
						pass

				ToastWidget.show(self.frame, "Diseño modificado correctamente", tipo="success")
				# Resetear estado tras modificar con éxito para que el botón vuelva a GUARDAR
				self._diseno_cargado = None
				self._update_main_button()
				self._render_rejilla_metodos() # Limpiar campos
				self.frame.after(500, self._on_guardar_ok)
			else:
				ToastWidget.show(self.frame, "Error al modificar el diseño", tipo="error")
		else:
			# MODO CREAR
			if self.service.repository.existe_diseno(coleccion_id, nombre, sufijo_id):
				ToastWidget.show(self.frame, "Ya existe un diseño con ese nombre en esta colección", tipo="warning")
				return

			result = self.service.crear(
				coleccion_id=coleccion_id,
				nombre=nombre,
				sufijo_id=sufijo_id,
				tipos=tipos_ids
			)
			if result is None:
				# Buscar el recién creado
				self._diseno_cargado = self._buscar_diseno_exacto(coleccion_id, nombre, sufijo_id)
				
				# Guardar costes por método
				if self._diseno_cargado:
					for metodo_id, entry in self._metodos_entries.items():
						try:
							coste_val = float(entry.get().replace(',', '.'))
							self.metodos_repo.guardar_coste_diseno(
								self._diseno_cargado.codigo,
								metodo_id,
								prepare_for_db(coste_val)
							)
						except ValueError:
							pass

				ToastWidget.show(self.frame, "Diseño guardado correctamente", tipo="success")
				self.frame.after(500, self._on_guardar_ok)
			else:
				ToastWidget.show(self.frame, result, tipo="error")

	def _on_diseno_double_click(self, item_data: dict):
		"""Al hacer doble click, cargar el diseño y sus chips."""
		diseno: ProduccionDiseno = item_data["obj"]
		logging.info(f"[PRODUCCION] Cargando diseño para editar: {diseno.codigo} - {diseno.nombre} (Tipos: {diseno.tipos})")
		self._diseno_cargado = diseno
		
		# Rellenar nombre
		self._entry_nombre.delete(0, tk.END)
		self._entry_nombre.insert(0, diseno.nombre)
		
		# Seleccionar chips automáticamente
		self._coleccion_seleccionada = self._get_coleccion_nombre(diseno.coleccion_id)
		self._sufijo_seleccionado = self._get_sufijo_nombre(diseno.sufijo_id) if diseno.sufijo_id else None
		
		# Cargar tipos del diseño en _coste_items para no perderlos al guardar
		self._coste_items = []
		if diseno.tipos:
			for tid in diseno.tipos:
				self._coste_items.append({"tipo_id": tid})
		
		# Refrescar UI
		self._render_chips_colecciones()
		self._render_chips_sufijos()
		self._render_rejilla_metodos() # Cargar costes del diseño
		self._update_main_button()

	def _buscar_diseno_exacto(self, coleccion_id: int, nombre: str, sufijo_id: Optional[int]) -> Optional[ProduccionDiseno]:
		"""Buscar el diseño exacto por sus campos de negocio."""
		try:
			todos = self.service.obtener_todos()
			for d in todos:
				if (d.coleccion_id == coleccion_id and 
					d.nombre.lower() == nombre.lower() and 
					d.sufijo_id == sufijo_id):
					return d
			return None
		except Exception:
			return None

	def _limpiar_formulario(self):
		"""Limpiar todos los campos para crear un nuevo diseño."""
		logging.info("[PRODUCCION] Limpiando formulario")
		self._diseno_cargado = None
		self._entry_nombre.delete(0, tk.END)
		self._coste_items = []
		self._coleccion_seleccionada = None
		self._sufijo_seleccionado = None
		self._cache_tipos = {t.id: t.nombre for t in self.tipos_service.obtener_activos()}
		self._render_chips_colecciones()
		self._render_chips_sufijos()
		self._render_rejilla_metodos()
		self._paginated_list.search("")
		self._entry_nombre.focus_set()

	def _on_add_coleccion(self):
		"""Añadir una nueva colección."""
		from kool_tpv.utils.dialogs import show_input_dialog
		nombre = show_input_dialog(self.frame, "Nueva Colección", "Nombre de la colección:")
		if nombre and nombre.strip():
			new_id = self.colecciones_repo.crear(nombre.strip())
			if new_id:
				# Actualizar caché
				self._colecciones_cache = {c.id: c.nombre for c in self.colecciones_repo.get_activas()}
				self._colecciones = list(self._colecciones_cache.values())
				self._render_chips_colecciones()
				ToastWidget.show(self.frame, "Colección añadida", tipo='success')
			else:
				ToastWidget.show(self.frame, "Error al añadir colección", tipo='error')

	def _on_add_sufijo(self):
		"""Añadir un nuevo sufijo."""
		from kool_tpv.utils.dialogs import show_input_dialog
		nombre = show_input_dialog(self.frame, "Nuevo Sufijo", "Nombre del sufijo:")
		if nombre and nombre.strip():
			new_id = self.sufijos_repo.crear(nombre.strip())
			if new_id:
				# Actualizar caché
				self._sufijos_cache = {s.id: s.nombre for s in self.sufijos_repo.get_activos()}
				self._sufijos = list(self._sufijos_cache.values())
				self._render_chips_sufijos()
				ToastWidget.show(self.frame, "Sufijo añadido", tipo='success')
			else:
				ToastWidget.show(self.frame, "Error al añadir sufijo", tipo='error')

	def _on_add_metodo(self):
		"""Añadir un nuevo método de producción."""
		from kool_tpv.utils.dialogs import show_input_dialog
		nombre = show_input_dialog(self.frame, "Nuevo Método", "Nombre de la técnica (DTG, Bordado...):")
		if nombre and nombre.strip():
			new_id = self.metodos_repo.crear(nombre.strip().upper())
			if new_id:
				# Actualizar caché de métodos
				self._metodos_cache = self.metodos_repo.get_activos()
				self._render_rejilla_metodos()
				ToastWidget.show(self.frame, "Método añadido", tipo='success')
			else:
				ToastWidget.show(self.frame, "Error al añadir método", tipo='error')

	def _get_coleccion_nombre(self, coleccion_id: int) -> str:
		"""Resolver nombre de colección desde caché."""
		return self._colecciones_cache.get(coleccion_id, "")

	def _get_sufijo_nombre(self, sufijo_id: int) -> str:
		"""Resolver nombre de sufijo desde caché."""
		return self._sufijos_cache.get(sufijo_id, "")

	def _on_guardar_ok(self, confirmed=None):
		"""Callback tras guardar OK: cerrar vista enviando el diseño."""
		if self.on_cerrar:
			self.on_cerrar(self._diseno_cargado)

	def destruir(self):
		"""Destruir la subvista."""
		try:
			self.frame.winfo_toplevel().grab_release()
		except Exception:
			pass
		self.frame.destroy()
