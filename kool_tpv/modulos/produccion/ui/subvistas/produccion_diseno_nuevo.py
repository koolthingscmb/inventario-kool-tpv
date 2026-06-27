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
from kool_tpv.modulos.produccion.ui.subvistas.config_helper import cargar_config_produccion, get_font, get_nav_button_config, get_nav_button_style
from kool_tpv.utils.widgets.searchable_combo import SearchableCombo
from kool_tpv.utils.widgets.searchable_paginated_navlist import SearchablePaginatedNavList
from kool_tpv.utils.widgets.notificaciones.toast_widget import ToastWidget


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

		# Estado de edición
		self._diseno_cargado: Optional[ProduccionDiseno] = None
		self._cache_tipos = {t.id: t.nombre for t in self.tipos_service.obtener_activos()}
		self._coste_items: list = []  # Lista de dicts con datos de cada coste

		# Cargar configuración
		self.config = cargar_config_produccion()
		self._colors = self.config.get("colors", {})
		self._bg = self._colors.get("background", "#2c3e50")
		self._text = self._colors.get("text", "#ecf0f1")
		self._text_sec = self._colors.get("text_secondary", "#95a5a6")

		# Frame principal
		self.frame = ctk.CTkFrame(parent, fg_color=self._bg)
		self.frame.pack(fill="both", expand=True)

		# Cargar datos para combos
		self._colecciones = self._cargar_colecciones()
		self._sufijos = self._cargar_sufijos()
		self._tipos = self._cargar_tipos()

		# UI
		self._crear_titulo()
		self._crear_formulario()
		self._crear_boton_guardar()

		# Foco inicial
		self.frame.after(100, lambda: self._entry_nombre.focus_set())

	def _get_font(self, key: str) -> tuple:
		return get_font(self.config, key)

	def _cargar_colecciones(self) -> List[str]:
		"""Obtener colecciones existentes (DISTINCT) normalizadas."""
		try:
			rows = self.db.fetch_all(
				"SELECT DISTINCT coleccion FROM produccion_disenos WHERE coleccion IS NOT NULL AND coleccion != '' ORDER BY coleccion"
			)
			return [_normalizar(r[0]) for r in rows if r[0]]
		except Exception:
			logging.exception("Error cargando colecciones")
			return []

	def _cargar_sufijos(self) -> List[str]:
		"""Obtener sufijos existentes (DISTINCT) normalizados."""
		try:
			rows = self.db.fetch_all(
				"SELECT DISTINCT sufijo FROM produccion_disenos WHERE sufijo IS NOT NULL AND sufijo != '' ORDER BY sufijo"
			)
			return [_normalizar(r[0]) for r in rows if r[0]]
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

	def _crear_titulo(self):
		"""Crear el título de la subvista."""
		titulo = ctk.CTkLabel(
			self.frame,
			text="NUEVO DISEÑO",
			font=self._get_font("title"),
			text_color=self._text,
			fg_color=self._bg
		)
		titulo.pack(pady=(20, 20))

	def _crear_formulario(self):
		"""Crear los campos del formulario."""
		form_frame = ctk.CTkFrame(self.frame, fg_color=self._bg)
		form_frame.pack(pady=(0, 20), padx=40, fill="both", expand=True)

		# --- Fila superior: Nombre + COMPROBAR | Colección | Sufijo ---
		top_row = ctk.CTkFrame(form_frame, fg_color="transparent")
		top_row.pack(fill="x", pady=(10, 5))

		# Nombre + COMPROBAR
		name_frame = ctk.CTkFrame(top_row, fg_color="transparent")
		name_frame.pack(side="left", fill="x", expand=True, padx=(0, 10))

		lbl_nombre = ctk.CTkLabel(
			name_frame,
			text="NOMBRE DEL DISEÑO",
			font=self._get_font("label"),
			text_color=self._text_sec,
			fg_color=self._bg
		)
		lbl_nombre.pack(anchor="w", pady=(0, 2))

		name_search_frame = ctk.CTkFrame(name_frame, fg_color="transparent")
		name_search_frame.pack(fill="x")

		self._entry_nombre = ctk.CTkEntry(
			name_search_frame,
			font=self._get_font("entry")
		)
		self._entry_nombre.pack(side="left", fill="x", expand=True, padx=(0, 10))
		_entry_nombre_inner = self._entry_nombre._entry if hasattr(self._entry_nombre, '_entry') else self._entry_nombre
		_entry_nombre_inner.bind("<Tab>", self._on_tab_next)
		_entry_nombre_inner.bind("<Return>", lambda e: self._on_comprobar())
		_entry_nombre_inner.bind("<FocusIn>", self._on_entry_focus_in)
		_entry_nombre_inner.bind("<FocusOut>", self._on_entry_focus_out)

		self.btn_comprobar = ctk.CTkButton(
			name_search_frame,
			text="COMPROBAR",
			width=120,
			command=self._on_comprobar
		)
		self.btn_comprobar.pack(side="left")

		# Colección
		col_frame = ctk.CTkFrame(top_row, fg_color="transparent")
		col_frame.pack(side="left", fill="x", expand=True, padx=(0, 10))

		lbl_coleccion = ctk.CTkLabel(
			col_frame,
			text="COLECCIÓN",
			font=self._get_font("label"),
			text_color=self._text_sec,
			fg_color=self._bg
		)
		lbl_coleccion.pack(anchor="w", pady=(0, 2))

		self._combo_coleccion = SearchableCombo(
			col_frame,
			values=self._colecciones,
			placeholder="Selecciona colección...",
			module_name="produccion"
		)
		self._combo_coleccion.pack(fill="x")
		self._combo_coleccion.entry.bind("<Tab>", self._on_tab_next)

		# Sufijo
		var_frame = ctk.CTkFrame(top_row, fg_color="transparent")
		var_frame.pack(side="left", fill="x", expand=True)

		lbl_sufijo = ctk.CTkLabel(
			var_frame,
			text="SUFIJO",
			font=self._get_font("label"),
			text_color=self._text_sec,
			fg_color=self._bg
		)
		lbl_sufijo.pack(anchor="w", pady=(0, 2))

		self._combo_sufijo = SearchableCombo(
			var_frame,
			values=self._sufijos,
			placeholder="Selecciona sufijo...",
			module_name="produccion"
		)
		self._combo_sufijo.pack(fill="x")
		self._combo_sufijo.entry.bind("<Tab>", self._on_tab_next)

		# --- SearchablePaginatedNavList ---
		from kool_tpv.utils.config_loader import load_layout_config
		root = self.frame.winfo_toplevel()
		from kool_tpv.utils.keyboard_manager import KeyboardManager
		_km = getattr(root, 'keyboard_manager', None)

		columns = [
			("nombre", 200, "Nombre"),
			("coleccion", 150, "Colección"),
			("sufijo", 150, "Sufijo"),
			("tipos_nombres", 200, "Tipos")
		]

		self._paginated_list = SearchablePaginatedNavList(
			parent=form_frame,
			columns=columns,
			search_function=self._buscar_disenos_paginado,
			map_function=self._map_diseno_para_lista,
			module_name="produccion",
			page_limit=50,
			on_double_click=self._on_diseno_double_click,
			keyboard_manager=_km,
			layout_config=load_layout_config()
		)
		self._paginated_list.pack(fill="x", pady=(0, 20))
		# Referencia interna para compatibilidad con código existente
		self._nav_list = self._paginated_list.nav_list

		# --- Sección de costes (50% abajo) ---
		bottom_frame = ctk.CTkFrame(self.frame, fg_color=self._bg)
		bottom_frame.pack(fill="both", expand=True, padx=40, pady=(0, 10))

		lbl_costes = ctk.CTkLabel(
			bottom_frame,
			text="BUSCA TIPO, GÉNERO O VARIANTE:",
			font=self._get_font("label"),
			text_color=self._text_sec,
			fg_color=self._bg
		)
		lbl_costes.pack(anchor="w", pady=(10, 2))

		self._combo_costes = SearchableCombo(
			bottom_frame,
			placeholder="Buscar tipo, género o variante...",
			width=400,
			module_name="produccion",
			search_function=self._buscar_costes_callback,
			command=self._on_coste_selected
		)
		self._combo_costes.pack(fill="x", pady=(0, 10))

		self._costes_grid = ctk.CTkScrollableFrame(bottom_frame, fg_color=self._bg, height=150)
		self._costes_grid.pack(fill="both", expand=True, pady=(0, 10))

	def _crear_boton_guardar(self):
		"""Crear el botón GUARDAR desde config."""
		nav_guardar = get_nav_button_config(self.config, "confirmar")
		style_guardar = get_nav_button_style(self.config, nav_guardar.get("style_key", "confirmar"))
		self.btn_guardar = ctk.CTkButton(
			self.frame,
			text="GUARDAR",
			font=self._get_font(nav_guardar.get("font_key", "button")),
			fg_color=style_guardar.get("bg", "#27ae60"),
			text_color=style_guardar.get("text", "#FFFFFF"),
			hover_color=style_guardar.get("hover", "#2ecc71"),
			border_color=style_guardar.get("border", "#27ae60"),
			border_width=style_guardar.get("focus_thickness", 0),
			width=nav_guardar.get("width", 15) * 10,
			height=nav_guardar.get("height", 2) * 20,
			cursor="hand2",
			command=self._on_guardar
		)
		self.btn_guardar.pack(pady=(0, 20))

	def _buscar_costes_callback(self, filtro: str) -> List[dict]:
		"""Buscar tipos, géneros y variantes de forma unificada."""
		try:
			results = []
			fl = filtro.lower()

			# 1. Tipos
			for t in self.tipos_service.obtener_activos():
				if fl in t.nombre.lower():
					results.append({
						"id": f"t{t.id}",
						"nombre_display": t.nombre,
						"tipo_id": t.id,
						"variante_id": None,
						"label": t.nombre
					})

			# 2. Variantes
			for v in self.variantes_service.obtener_todos():
				if v.activo and fl in v.nombre.lower():
					tipo_nombre = self._cache_tipos.get(v.tipo_id, str(v.tipo_id))
					label = f"{tipo_nombre} {v.nombre}"
					results.append({
						"id": f"v{v.id}",
						"nombre_display": label,
						"tipo_id": v.tipo_id,
						"variante_id": v.id,
						"label": label
					})

			return results
		except Exception:
			logging.exception("Error en búsqueda unificada de costes")
			return []

	def _on_coste_selected(self, value: str):
		"""Callback al seleccionar un item del buscador de costes."""
		try:
			data = self._combo_costes.get_producto_data()
			if not data:
				return
			self._add_coste_item(
				tipo_id=data["tipo_id"],
				variante_id=data.get("variante_id"),
				label=data["label"]
			)
			self._combo_costes.clear()
		except Exception:
			logging.exception("Error al seleccionar coste")

	def _add_coste_item(self, tipo_id: int, variante_id: Optional[int], label: str, coste: int = 0):
		"""Añadir un item de coste al grid si no existe ya."""
		for item in self._coste_items:
			if (item["tipo_id"] == tipo_id and
				item.get("variante_id") == variante_id):
				return
		self._coste_items.append({
			"tipo_id": tipo_id,
			"variante_id": variante_id,
			"label": label,
			"coste": coste,
			"entry": None
		})
		self._render_costes_grid()

	def _remove_coste_item(self, idx: int):
		"""Eliminar un item de coste del grid."""
		if 0 <= idx < len(self._coste_items):
			self._coste_items.pop(idx)
			self._render_costes_grid()

	def _render_costes_grid(self):
		"""Renderizar el grid de costes, máx 3 por fila."""
		try:
			for w in list(self._costes_grid.winfo_children()):
				w.destroy()

			for i, item in enumerate(self._coste_items):
				row = i // 3
				col = i % 3
				cell = ctk.CTkFrame(self._costes_grid, fg_color="transparent")
				cell.grid(row=row, column=col, sticky="ew", padx=4, pady=4)

				lbl = ctk.CTkLabel(cell, text=item["label"], font=self._get_font("label"), text_color=self._text, fg_color="transparent")
				lbl.pack(side="left", padx=(4, 8))

				entry = ctk.CTkEntry(cell, placeholder_text="0.00", width=70, font=self._get_font("entry"))
				entry.pack(side="left", padx=(0, 4))
				if item.get("coste"):
					entry.insert(0, f"{item['coste'] / 100:.2f}")
				item["entry"] = entry

				btn_x = ctk.CTkButton(
					cell, text="✕", width=20, height=20,
					fg_color="transparent", hover_color="#e74c3c", text_color=self._text_sec,
					command=lambda idx=i: self._remove_coste_item(idx)
				)
				btn_x.pack(side="left")

			for col in range(3):
				self._costes_grid.grid_columnconfigure(col, weight=1)
		except Exception:
			logging.exception("Error renderizando grid de costes")

	def _build_lista_costes(self) -> List[DisenoCoste]:
		"""Construir lista de DisenoCoste desde los items del grid."""
		lista = []
		for item in self._coste_items:
			entry = item.get("entry")
			if entry:
				try:
					val = entry.get().strip().replace(",", ".")
					coste_cent = int(float(val) * 100) if val else 0
				except ValueError:
					coste_cent = 0
			else:
				coste_cent = item.get("coste", 0)
			lista.append(DisenoCoste(
				diseno_codigo=self._diseno_cargado.codigo if self._diseno_cargado else "",
				tipo_id=item["tipo_id"],
				variante_id=item.get("variante_id"),
				coste=coste_cent
			))
		return lista

	def _on_tab_next(self, event):
		"""Tab: mover foco al siguiente widget."""
		widgets = [
			self._entry_nombre._entry if hasattr(self._entry_nombre, '_entry') else self._entry_nombre,
			self.btn_comprobar,
			self._combo_coleccion.entry,
			self._combo_sufijo.entry,
			self._combo_costes.entry,
			self.btn_guardar
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

	def _on_entry_focus_in(self, event):
		"""Liberar flechas del teclado al entrar al entry."""
		try:
			from kool_tpv.utils.keyboard_manager import KeyboardManager
			KeyboardManager.get_instance().set_capture_enabled(False)
		except Exception:
			pass

	def _on_entry_focus_out(self, event):
		"""Reactivar flechas del teclado al salir del entry."""
		try:
			from kool_tpv.utils.keyboard_manager import KeyboardManager
			KeyboardManager.get_instance().set_capture_enabled(True)
		except Exception:
			pass

	def _on_comprobar(self):
		"""Buscar diseños por el nombre introducido usando el componente paginado."""
		nombre = self._entry_nombre.get().strip()
		# Pre-cargar tipos para el map_function
		self._cache_tipos = {t.id: t.nombre for t in self.tipos_service.obtener_activos()}
		self._paginated_list.search(nombre)

	def _buscar_disenos_paginado(self, filtro: str) -> List[ProduccionDiseno]:
		"""Función de búsqueda para SearchablePaginatedNavList."""
		if filtro.strip():
			return self.service.buscar(filtro.strip())
		return self.service.obtener_activos()

	def _map_diseno_para_lista(self, r: ProduccionDiseno) -> dict:
		"""Función de mapeo para SearchablePaginatedNavList."""
		tipos_nombres = ", ".join([self._cache_tipos.get(tid, str(tid)) for tid in r.tipos])
		return {
			"codigo": r.codigo,
			"nombre": r.nombre,
			"coleccion": r.coleccion,
			"sufijo": r.sufijo or "",
			"tipos_nombres": tipos_nombres,
			"obj": r
		}

	def _on_diseno_double_click(self, item_data: dict):
		"""Al hacer doble click, cargar el diseño."""
		diseno: ProduccionDiseno = item_data["obj"]
		self._diseno_cargado = diseno
		
		# Rellenar campos
		self._entry_nombre.delete(0, tk.END)
		self._entry_nombre.insert(0, diseno.nombre)
		
		self._combo_coleccion.set(diseno.coleccion)
		self._combo_sufijo.set(diseno.sufijo or "")
		
		# Cargar costes existentes en el grid
		self._coste_items = []
		for c in diseno.costes:
			tipo_nombre = self._cache_tipos.get(c.tipo_id, str(c.tipo_id))
			label = tipo_nombre
			if c.variante_id:
				rows = self.db.fetch_all("SELECT nombre FROM produccion_tipos_variantes WHERE id = ?", (c.variante_id,))
				variante_nombre = rows[0][0] if rows else str(c.variante_id)
				label = f"{tipo_nombre} {variante_nombre}"
			self._coste_items.append({
				"tipo_id": c.tipo_id,
				"variante_id": c.variante_id,
				"label": label,
				"coste": c.coste,
				"entry": None
			})
		self._render_costes_grid()

		# Cambiar texto botón guardar
		self.btn_guardar.configure(text="MODIFICAR DISEÑO")

	def _on_guardar(self):
		"""Guardar o Modificar el diseño."""
		coleccion = _normalizar(self._combo_coleccion.get())
		sufijo = _normalizar(self._combo_sufijo.get())
		# Recopilar tipos_ids desde los items de coste
		tipos_ids = list(set(item["tipo_id"] for item in self._coste_items))
		nombre = self._entry_nombre.get().strip()

		if not nombre:
			ToastWidget.show(self.frame, "El nombre del diseño es obligatorio", tipo="warning")
			self._entry_nombre.focus_set()
			return
		if not coleccion:
			ToastWidget.show(self.frame, "La colección es obligatoria", tipo="warning")
			self._combo_coleccion.entry.focus_set()
			return

		if self._diseno_cargado:
			# MODO MODIFICAR
			lista_costes = self._build_lista_costes()
			ok = self.service.actualizar(
				codigo=self._diseno_cargado.codigo,
				coleccion=coleccion,
				nombre=nombre,
				sufijo=sufijo if sufijo else None,
				tipos=tipos_ids,
				lista_costes=lista_costes
			)
			if ok:
				ToastWidget.show(self.frame, "Diseño modificado correctamente", tipo="success")
				self.frame.after(500, self._on_guardar_ok)
			else:
				ToastWidget.show(self.frame, "Error al modificar el diseño", tipo="error")
		else:
			# MODO CREAR (Verificar duplicado exacto antes)
			if self.service.repository.existe_diseno(coleccion, nombre, sufijo if sufijo else None):
				from kool_tpv.utils.dialogs import show_warning as show_confirm_dialog
				confirm = show_confirm_dialog(
					self.frame,
					"Diseño Duplicado",
					f"Ya existe el diseño '{coleccion} - {nombre}'.\n¿Deseas MODIFICARLO?",
					confirm=True
				)
				if confirm:
					# Buscar el existente y re-cargar
					existente = self._buscar_diseno_exacto(coleccion, nombre, sufijo)
					if existente:
						self._on_diseno_double_click({"obj": existente})
					return
				else:
					return

			lista_costes = self._build_lista_costes()
			result = self.service.crear(
				coleccion=coleccion,
				nombre=nombre,
				sufijo=sufijo if sufijo else None,
				tipos=tipos_ids,
				lista_costes=lista_costes
			)
			if result is None:
				self._diseno_cargado = self._buscar_diseno_exacto(coleccion, nombre, sufijo)
				ToastWidget.show(self.frame, "Diseño guardado correctamente", tipo="success")
				self.frame.after(500, self._on_guardar_ok)
			else:
				ToastWidget.show(self.frame, result, tipo="error")

	def _buscar_diseno_exacto(self, coleccion: str, nombre: str, sufijo: Optional[str]) -> Optional[ProduccionDiseno]:
		"""Buscar el diseño exacto por sus campos de negocio."""
		try:
			# Usar el repository para buscar por campos
			# Podríamos añadir un método get_by_fields al repo, pero usaremos buscar() por ahora
			todos = self.service.obtener_todos()
			for d in todos:
				if (d.coleccion.lower() == coleccion.lower() and 
					d.nombre.lower() == nombre.lower() and 
					(d.sufijo or "").lower() == (sufijo or "").lower()):
					return d
			return None
		except Exception:
			return None

	def _limpiar_formulario(self):
		"""Limpiar todos los campos para crear un nuevo diseño."""
		self._diseno_cargado = None
		self._entry_nombre.delete(0, tk.END)
		self._combo_coleccion.clear()
		self._combo_sufijo.clear()
		self._coste_items = []
		self._render_costes_grid()
		self.btn_guardar.configure(text="GUARDAR DISEÑO")
		self._cache_tipos = {t.id: t.nombre for t in self.tipos_service.obtener_activos()}
		self._paginated_list.search("")
		self._entry_nombre.focus_set()

	def _on_guardar_ok(self, confirmed=None):
		"""Callback tras guardar OK: cerrar vista enviando el diseño."""
		if self.on_cerrar:
			self.on_cerrar(self._diseno_cargado)

	def destruir(self):
		"""Destruir la subvista."""
		try:
			from kool_tpv.utils.keyboard_manager import KeyboardManager
			KeyboardManager.get_instance().set_capture_enabled(True)
		except Exception:
			pass
		try:
			self.frame.winfo_toplevel().grab_release()
		except Exception:
			pass
		self.frame.destroy()
