"""Subvista de resumen de producción.

Contiene la clase `NuevaProduccionResumenView` que muestra la lista de ítems
añadidos a la orden de producción y botones de AÑADIR / CONFIRMAR / VOLVER.
"""
import tkinter as tk
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Dict

import customtkinter as ctk

from kool_tpv.modulos.produccion.services.produccion_ordenes_service import ItemProduccion
from kool_tpv.modulos.produccion.ui.subvistas.config_helper import cargar_config_produccion, get_font, get_nav_button_config, get_nav_button_style
from kool_tpv.utils.widgets.virtual_nav_list import VirtualNavList
from kool_tpv.utils.widgets.notificaciones.toast_widget import ToastWidget
from kool_tpv.modulos.tpv.services.reposicion_store import ReposicionStore
from kool_tpv.utils.dialogs.helpers import show_info, show_warning
from kool_tpv.utils.factories.button_factory import ButtonFactory


class NuevaProduccionResumenView:
	"""Subvista de resumen con lista de ítems y botones de acción.

	Args:
		parent: Widget padre donde se mostrará la subvista.
		on_anadir: Callback cuando se pulsa AÑADIR (para añadir otro ítem).
		on_confirmar: Callback cuando se pulsa CONFIRMAR (recibe la lista de ítems).
		on_volver: Callback cuando se pulsa VOLVER.
	"""

	def __init__(self, parent, db: Database,
	             on_anadir: Optional[Callable] = None,
	             on_confirmar: Optional[Callable[[List[ItemProduccion]], None]] = None,
	             on_volver: Optional[Callable] = None):
		self.parent = parent
		self.db = db
		self.on_anadir = on_anadir
		self.on_confirmar = on_confirmar
		self.on_volver = on_volver
		self.items: List[ItemProduccion] = []
		self.reposicion_store = ReposicionStore()
		self._reposicion_pendientes = self.reposicion_store.cargar()

		# Animación de pulso para el botón VINCULAR
		self._pulse_active = False
		self._pulse_after_id = None
		self._pulse_state = False
		self._accent_color = "#FFD700"  # Default gold
		self._original_border_color = None

		# Cargar configuración
		self.config = cargar_config_produccion()
		self._colors = self.config.get("colors", {})
		self._bg = self._colors.get("background", "#2c3e50")
		self._text = self._colors.get("text", "#ecf0f1")
		self._text_sec = self._colors.get("text_secondary", "#95a5a6")

		# Frame principal
		self.frame = tk.Frame(parent, bg=self._bg)
		self.frame.pack(fill=tk.BOTH, expand=True)

		# Título + tabla + total unidades
		self._crear_titulo()
		self._crear_tabla()
		self._crear_total_unidades()

		# Botones de navegación
		self._crear_botones_navegacion()

		# Obtener colores para el pulso desde la factoría
		try:
			prod_accent = ButtonFactory.get_module_colors("produccion").get("buttons", {}).get("accent", {})
			if prod_accent.get("bg"):
				self._accent_color = prod_accent["bg"]
			
			# Guardar el color de borde original del botón vincular para restaurarlo
			# El botón vincular usa palette_key="primary" y style_key="action_secondary" (outline)
			prod_primary = ButtonFactory.get_module_colors("produccion").get("buttons", {}).get("primary", {})
			self._original_border_color = prod_primary.get("border")
		except Exception:
			pass

		# Navegación por teclado
		self._setup_keyboard_nav()

	def _get_font(self, key: str) -> tuple:
		"""Obtener una fuente desde la configuración."""
		return get_font(self.config, key)

	def _crear_titulo(self):
		"""Crear el título de la subvista."""
		titulo = ctk.CTkLabel(
			self.frame,
			text="RESUMEN PRODUCCIÓN",
			font=self._get_font("title"),
			text_color=self._text,
			fg_color=self._bg
		)
		titulo.pack(pady=(20, 10))

	def _crear_tabla(self):
		"""Crear la tabla con cabeceras y filas de ítems usando VirtualNavList."""
		self.tabla_frame = ctk.CTkFrame(self.frame, fg_color=self._bg)
		self.tabla_frame.pack(expand=True, fill="both", padx=40, pady=(0, 10))

		# Configuración de columnas para VirtualNavList
		self.columns = [
			("usuario", 100, "Usuario"),
			("origen", 80, "Origen"),
			("cantidad", 60, "Cant"),
			("tipo", 120, "Tipo"),
			("variante", 100, "Variante"),
			("repos", 100, "Repos."),
			("color", 100, "Color"),
			("talla", 60, "Talla"),
			("extra", 100, "Extra"),
			("metodo", 100, "Método"),
			("coleccion", 100, "Colección"),
			("sufijo", 80, "Sufijo"),
			("diseno", 150, "Diseño"),
		]

		# Obtener el keyboard manager del toplevel
		root = self.frame.winfo_toplevel()
		km = getattr(root, 'keyboard_manager', None)

		self.nav_list = VirtualNavList(
			self.tabla_frame,
			columns=self.columns,
			module_name="produccion",
			keyboard_manager=km,
			on_double_click=self._on_item_double_click,
			row_color_callback=self._row_color_callback,
			multi_select=True
		)
		self.nav_list.pack(expand=True, fill="both")
		
		# Bind tecla Delete para eliminar ítems
		self.nav_list.bind('<Delete>', lambda e: self._on_eliminar_teclado())

	def _on_item_double_click(self, data):
		"""Doble clic para vincular o editar."""
		idx = data.get("_idx")
		if idx is not None:
			self._vincular_item(idx)

	def _on_vincular_click(self):
		"""Vincular los ítems seleccionados."""
		selected = self.nav_list.get_selected_items()
		if not selected:
			ToastWidget.show(self.frame, "Seleccione una línea para vincular", tipo='warning')
			return
		
		# Si hay varios seleccionados, ir uno a uno o avisar
		if len(selected) > 1:
			ToastWidget.show(self.frame, "Por favor, vincule las líneas una a una", tipo='info')
		
		idx = selected[0].get("_idx")
		if idx is not None:
			self._vincular_item(idx)

	def _find_potenciales(self, item) -> List[Dict]:
		"""
		Busca líneas de reposición pendientes que coinciden con el ítem de producción.
		Criterio: Deben coincidir Tipo y Variante obligatoriamente.
		"""
		return [r for r in self._reposicion_pendientes 
				if r.get('tipo_id') == item.tipo_id and 
				   r.get('variante_id') == item.variante_id]

	def _vincular_item(self, idx: int):
		"""Lógica de vinculación manual inteligente."""
		if not (0 <= idx < len(self.items)):
			return
		
		item = self.items[idx]
		
		# 1. Buscar potenciales coincidencias en reposición
		potenciales = self._find_potenciales(item)
		
		if not potenciales:
			show_info(self.frame, "Vincular Reposición", 
					 f"No se han encontrado líneas de reposición pendientes para:\n{item.tipo_nombre} {item.variante_nombre or ''}")
			return

		# 2. Enriquecer potenciales con nombre de diseño desde la BD
		from kool_tpv.utils.dialogs.reposicion_select_dialog import show_reposicion_select_dialog
		from kool_tpv.modulos.produccion.repositories.produccion_disenos_repository import ProduccionDisenosRepository
		
		repo_disenos = ProduccionDisenosRepository(self.db)
		
		# Enriquecer potenciales con diseno_nombre
		for p in potenciales:
			codigo = p.get('diseno_codigo')
			if codigo:
				try:
					dis = repo_disenos.get_por_codigo(codigo)
					if dis:
						p['_diseno_nombre_db'] = dis.nombre
				except Exception:
					pass
		
		# 3. Mostrar diálogo de selección (siempre, aunque solo haya una opción)
		seleccion_id = show_reposicion_select_dialog(self.frame, potenciales)
		if seleccion_id:
			item.reposicion_id = seleccion_id
			ToastWidget.show(self.frame, "Línea vinculada manualmente", tipo='success')
			self._refrescar_lista()

	def _row_color_callback(self, data, index):
		"""Colorear filas según su estado de vinculación."""
		idx = data.get("_idx")
		if idx is not None and 0 <= idx < len(self.items):
			item = self.items[idx]
			if item.reposicion_id:
				return {'bg': '#1b5e20', 'fg': '#ffffff'} # Verde oscuro (Vinculado)
			
			# Verificar si hay potenciales mediante el método centralizado
			if self._find_potenciales(item):
				return {'bg': '#7f5a00', 'fg': '#ffffff'} # Marrón/Naranja oscuro (Sugerencia)
		
		return None

	def _on_eliminar_teclado(self):
		"""Eliminar los ítems seleccionados con la tecla Supr."""
		self._on_eliminar_click()

	def _on_eliminar_click(self):
		"""Eliminar todos los ítems seleccionados en la tabla."""
		selected = self.nav_list.get_selected_items()
		if not selected:
			ToastWidget.show(self.frame, "Seleccione al menos una línea para eliminar", tipo='warning')
			return
		
		# Obtener índices reales y ordenarlos de mayor a menor para no romper el pop()
		indices = sorted([d.get("_idx") for d in selected if d.get("_idx") is not None], reverse=True)
		
		if indices:
			for idx in indices:
				if 0 <= idx < len(self.items):
					self.items.pop(idx)
			
			self._refrescar_lista()
			ToastWidget.show(self.frame, f"Eliminadas {len(indices)} líneas", tipo='success')

	def _crear_total_unidades(self):
		"""Crear el label del total de unidades."""
		self.lbl_total = ctk.CTkLabel(
			self.frame,
			text="TOTAL UNIDADES: 0",
			font=self._get_font("subtitle"),
			text_color=self._text,
			fg_color=self._bg
		)
		self.lbl_total.pack(pady=(0, 10))

	def _crear_botones_navegacion(self):
		"""Crear los botones de navegación inferior."""
		frame_nav = ctk.CTkFrame(self.frame, fg_color=self._bg)
		frame_nav.pack(fill="x", padx=40, pady=20)

		# Botón VOLVER
		nav_volver = get_nav_button_config(self.config, "volver")
		self.btn_volver = ButtonFactory.create_button(
			parent=frame_nav,
			text=nav_volver.get("text", "VOLVER"),
			command=self._on_volver,
			width=nav_volver.get("width", 15) * 10,
			height=nav_volver.get("height", 2) * 20,
			font=self._get_font(nav_volver.get("font_key", "button")),
			style_key="action_confirm",
			module="produccion",
			palette_key="primary",
			cursor="hand2"
		)
		self.btn_volver.pack(side=tk.LEFT, padx=10)

		# Botón AÑADIR
		nav_anadir = get_nav_button_config(self.config, "anadir")
		self.btn_anadir = ButtonFactory.create_button(
			parent=frame_nav,
			text=nav_anadir.get("text", "AÑADIR"),
			command=self._on_anadir,
			width=nav_anadir.get("width", 15) * 10,
			height=nav_anadir.get("height", 2) * 20,
			font=self._get_font(nav_anadir.get("font_key", "button")),
			style_key="action_confirm",
			module="produccion",
			palette_key="primary",
			cursor="hand2"
		)
		self.btn_anadir.pack(side=tk.LEFT, padx=(10, 10))

		# Botón ELIMINAR
		self.btn_eliminar = ButtonFactory.create_button(
			parent=frame_nav,
			text="ELIMINAR",
			command=self._on_eliminar_click,
			width=120,
			height=nav_anadir.get("height", 2) * 20,
			font=self._get_font("button"),
			style_key="action_secondary",
			module="produccion",
			palette_key="accent",
			cursor="hand2"
		)
		self.btn_eliminar.pack(side=tk.LEFT, padx=10)

		# Botón VINCULAR REPOSICIÓN
		self.btn_vincular = ButtonFactory.create_button(
			parent=frame_nav,
			text="VINCULAR REPOS.",
			command=self._on_vincular_click,
			width=140,
			height=nav_anadir.get("height", 2) * 20,
			font=self._get_font("button"),
			style_key="action_secondary",
			module="produccion",
			palette_key="primary",
			cursor="hand2"
		)
		self.btn_vincular.pack(side=tk.LEFT, padx=10)

		# Botón CONFIRMAR
		nav_conf = get_nav_button_config(self.config, "confirmar")
		self.btn_confirmar = ButtonFactory.create_button(
			parent=frame_nav,
			text=nav_conf.get("text", "CONFIRMAR"),
			command=self._on_confirmar,
			width=nav_conf.get("width", 15) * 10,
			height=nav_conf.get("height", 2) * 20,
			font=self._get_font(nav_conf.get("font_key", "button")),
			style_key="action_confirm",
			module="produccion",
			palette_key="primary",
			cursor="hand2"
		)
		self.btn_confirmar.pack(side=tk.RIGHT, padx=10)

	# --- Gestión de ítems ---

	def anadir_item(self, item: ItemProduccion):
		"""Añadir un ítem a la lista y refrescar la vista."""
		self.items.append(item)
		self._refrescar_lista()

	def eliminar_item(self, index: int):
		"""Eliminar un ítem de la lista por índice."""
		if 0 <= index < len(self.items):
			self.items.pop(index)
			self._refrescar_lista()

	def _refrescar_lista(self):
		"""Refrescar la tabla virtual de ítems."""
		rows = []
		any_to_link = False
		for idx, item in enumerate(self.items):
			# Estado reposición
			repos_status = "-"
			if item.reposicion_id:
				repos_status = "VINCULADO"
			else:
				# Obtener todos los potenciales para este ítem
				potenciales = self._find_potenciales(item)
				
				# Ver si hay coincidencia automática (por diseño_codigo)
				auto_match = any(r.get('diseno_codigo') == item.diseno_codigo 
								for r in potenciales if r.get('diseno_codigo'))
				
				if auto_match:
					repos_status = "AUTO"
				elif potenciales:
					# Si hay potenciales (aunque tengan otro diseño o ninguno), es vinculable
					repos_status = "VINCULAR?"
					any_to_link = True

			rows.append({
				"usuario": getattr(item, 'usuario_nombre', '') or '',
				"origen": getattr(item, 'origen', '') or '',
				"cantidad": str(item.cantidad),
				"tipo": item.tipo_nombre or "",
				"variante": item.variante_nombre or "-",
				"repos": repos_status,
				"color": item.color_nombre or "",
				"talla": item.talla or "",
				"extra": getattr(item, 'extra_nombre', '-') or ('Mixta' if item.produccion_mixta else '-'),
				"metodo": getattr(item, 'metodo_nombre', '-') or '-',
				"coleccion": item.diseno_coleccion or "-",
				"sufijo": getattr(item, 'diseno_sufijo', '') or '-',
				"diseno": item.diseno_nombre or "",
				"_idx": idx  # Guardar índice real para eliminar
			})
		
		self.nav_list.set_items(rows)
		self._actualizar_total()

		# Gestionar animación de pulso
		if any_to_link:
			self._start_pulse()
		else:
			self._stop_pulse()

	def _start_pulse(self):
		"""Iniciar la animación de pulso en el botón VINCULAR."""
		if not self._pulse_active:
			self._pulse_active = True
			self._toggle_pulse()

	def _stop_pulse(self):
		"""Detener la animación de pulso y restaurar estado original."""
		self._pulse_active = False
		if self._pulse_after_id:
			self.frame.after_cancel(self._pulse_after_id)
			self._pulse_after_id = None
		
		# Restaurar estado visual original del botón
		try:
			self.btn_vincular.configure(
				border_width=1,
				border_color=self._original_border_color or "transparent"
			)
		except Exception:
			pass

	def _toggle_pulse(self):
		"""Alternar el estado visual del pulso."""
		if not self._pulse_active or not self.btn_vincular.winfo_exists():
			return

		self._pulse_state = not self._pulse_state
		
		try:
			if self._pulse_state:
				# Estado de atención
				self.btn_vincular.configure(
					border_width=3,
					border_color=self._accent_color
				)
			else:
				# Estado normal
				self.btn_vincular.configure(
					border_width=1,
					border_color=self._original_border_color or "transparent"
				)
		except Exception:
			self._pulse_active = False
			return

		self._pulse_after_id = self.frame.after(800, self._toggle_pulse)

	def _actualizar_total(self):
		"""Actualizar el label del total de unidades."""
		total = sum(item.cantidad for item in self.items)
		self.lbl_total.configure(text=f"TOTAL UNIDADES: {total}")

	# --- Navegación por teclado ---

	def _setup_keyboard_nav(self):
		"""Configurar bindings de navegación por teclado."""
		self._nav_buttons = [self.btn_volver, self.btn_anadir, self.btn_eliminar, self.btn_vincular, self.btn_confirmar]
		self._nav_callbacks = [self._on_volver, self._on_anadir, self._on_eliminar_click, self._on_vincular_click, self._on_confirmar]
		self._nav_index = -1

		toplevel = self.frame.winfo_toplevel()
		toplevel.bind("<Tab>", self._on_tab_next)
		toplevel.bind("<Shift-Tab>", self._on_tab_prev)
		toplevel.bind("<Return>", self._on_enter_nav)
		toplevel.bind("<KP_Enter>", self._on_enter_nav)

		self.frame.bind("<Destroy>", self._on_destroy)

	def _on_destroy(self, event=None):
		"""Limpiar bindings al destruir."""
		try:
			toplevel = self.frame.winfo_toplevel()
			for key in ("<Tab>", "<Shift-Tab>", "<Return>", "<KP_Enter>"):
				toplevel.unbind(key)
		except Exception:
			pass

	def _focus_nav_button(self, index):
		"""Aplicar foco visual a un botón por índice."""
		if not self._nav_buttons:
			return
		index = index % len(self._nav_buttons)
		# Restaurar borde anterior
		if 0 <= self._nav_index < len(self._nav_buttons):
			prev = self._nav_buttons[self._nav_index]
			try:
				prev.configure(border_width=0)
			except Exception:
				pass
		self._nav_index = index
		btn = self._nav_buttons[index]
		try:
			btn.configure(border_width=3, border_color="#FFD700")
		except Exception:
			pass
		btn.focus_set()

	def _on_tab_next(self, event):
		self._focus_nav_button(self._nav_index + 1)
		return "break"

	def _on_tab_prev(self, event):
		self._focus_nav_button(self._nav_index - 1)
		return "break"

	def _on_enter_nav(self, event):
		"""Enter activa el botón que tiene el foco."""
		if 0 <= self._nav_index < len(self._nav_callbacks):
			self._nav_callbacks[self._nav_index]()
		return "break"

	# --- Callbacks ---

	def _on_anadir(self):
		"""Manejador del botón AÑADIR."""
		if self.on_anadir:
			self.on_anadir()

	def _on_confirmar(self):
		"""Manejador del botón CONFIRMAR."""
		if self.items and self.on_confirmar:
			self.on_confirmar(self.items)

	def _on_volver(self):
		"""Manejador del botón VOLVER."""
		if self.on_volver:
			self.on_volver()

	def obtener_items(self) -> List[ItemProduccion]:
		"""Obtener la lista de ítems.

		Returns:
			Lista de objetos ItemProduccion.
		"""
		return self.items

	def destruir(self):
		"""Destruir la subvista y limpiar recursos."""
		self._stop_pulse()
		self._on_destroy()
		self.frame.destroy()
