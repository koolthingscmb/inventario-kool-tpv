"""Subvista de resumen de producción.

Contiene la clase `NuevaProduccionResumenView` que muestra la lista de ítems
añadidos a la orden de producción y botones de AÑADIR / CONFIRMAR / VOLVER.
"""
import tkinter as tk
from dataclasses import dataclass, field
from typing import Callable, List, Optional

import customtkinter as ctk

from kool_tpv.modulos.produccion.ui.subvistas.config_helper import cargar_config_produccion, get_font, get_nav_button_config, get_nav_button_style


@dataclass
class ItemProduccion:
	"""Ítem de producción añadido a la orden."""
	tipo_nombre: str = ""
	tipo_id: Optional[int] = None
	variante_nombre: Optional[str] = None
	variante_id: Optional[int] = None
	diseno_coleccion: Optional[str] = None
	genero: Optional[str] = None
	genero_id: Optional[int] = None
	talla: Optional[str] = None
	color_nombre: Optional[str] = None
	color_id: Optional[int] = None
	diseno_codigo: Optional[str] = None
	diseno_nombre: Optional[str] = None
	cantidad: int = 0
	produccion_mixta: bool = False
	coste_unitario: float = 0.0
	coste_total: float = 0.0



class NuevaProduccionResumenView:
	"""Subvista de resumen con lista de ítems y botones de acción.

	Args:
		parent: Widget padre donde se mostrará la subvista.
		on_anadir: Callback cuando se pulsa AÑADIR (para añadir otro ítem).
		on_confirmar: Callback cuando se pulsa CONFIRMAR (recibe la lista de ítems).
		on_volver: Callback cuando se pulsa VOLVER.
	"""

	def __init__(self, parent,
	             on_anadir: Optional[Callable] = None,
	             on_confirmar: Optional[Callable[[List[ItemProduccion]], None]] = None,
	             on_volver: Optional[Callable] = None):
		self.parent = parent
		self.on_anadir = on_anadir
		self.on_confirmar = on_confirmar
		self.on_volver = on_volver
		self.items: List[ItemProduccion] = []

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
		"""Crear la tabla con cabeceras y filas de ítems."""
		self.tabla_frame = ctk.CTkFrame(self.frame, fg_color=self._bg)
		self.tabla_frame.pack(expand=True, fill="both", padx=40, pady=(0, 10))

		# Cabeceras
		self._headers = ["Cant", "Tipo", "Var", "Diseño", "Colección", "Género", "Talla", "Color", "Mixta"]
		self._col_widths = [50, 100, 80, 180, 120, 100, 60, 100, 50]

		header_frame = ctk.CTkFrame(self.tabla_frame, fg_color=self._colors.get("bg_dark", "#0d0d0d"), height=36)
		header_frame.pack(fill="x", pady=(0, 4))
		header_frame.pack_propagate(False)

		for i, h in enumerate(self._headers):
			lbl = ctk.CTkLabel(
				header_frame,
				text=h,
				font=self._get_font("label"),
				text_color=self._text_sec,
				width=self._col_widths[i],
				anchor="w"
			)
			lbl.pack(side="left", padx=(6, 0))

		# Frame scrollable para las filas
		self.filas_frame = ctk.CTkScrollableFrame(
			self.tabla_frame,
			fg_color=self._bg,
			label_text=""
		)
		self.filas_frame.pack(expand=True, fill="both")

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
		style_volver = get_nav_button_style(self.config, nav_volver.get("style_key", "volver"))
		self.btn_volver = ctk.CTkButton(
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
		self.btn_volver.pack(side=tk.LEFT, padx=10)

		# Botón AÑADIR
		nav_anadir = get_nav_button_config(self.config, "anadir")
		style_anadir = get_nav_button_style(self.config, nav_anadir.get("style_key", "anadir"))
		self.btn_anadir = ctk.CTkButton(
			frame_nav,
			text=nav_anadir.get("text", "AÑADIR"),
			font=self._get_font(nav_anadir.get("font_key", "button")),
			fg_color=style_anadir.get("bg", "#27ae60"),
			text_color=style_anadir.get("text", "#FFFFFF"),
			hover_color=style_anadir.get("hover", "#2ecc71"),
			border_color=style_anadir.get("border", "#27ae60"),
			border_width=style_anadir.get("focus_thickness", 0),
			width=nav_anadir.get("width", 15) * 10,
			height=nav_anadir.get("height", 2) * 20,
			cursor="hand2",
			command=self._on_anadir
		)
		self.btn_anadir.pack(side=tk.LEFT, padx=(10, 0))

		# Botón CONFIRMAR
		nav_conf = get_nav_button_config(self.config, "confirmar")
		style_confirmar = get_nav_button_style(self.config, nav_conf.get("style_key", "confirmar"))
		self.btn_confirmar = ctk.CTkButton(
			frame_nav,
			text=nav_conf.get("text", "CONFIRMAR"),
			font=self._get_font(nav_conf.get("font_key", "button")),
			fg_color=style_confirmar.get("bg", "#27ae60"),
			text_color=style_confirmar.get("text", "#FFFFFF"),
			hover_color=style_confirmar.get("hover", "#2ecc71"),
			border_color=style_confirmar.get("border", "#27ae60"),
			border_width=style_confirmar.get("focus_thickness", 0),
			width=nav_conf.get("width", 15) * 10,
			height=nav_conf.get("height", 2) * 20,
			cursor="hand2",
			command=self._on_confirmar
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
		"""Refrescar la tabla visual de ítems."""
		# Limpiar filas
		for w in list(self.filas_frame.winfo_children()):
			w.destroy()

		if not self.items:
			lbl_vacio = ctk.CTkLabel(
				self.filas_frame,
				text="No hay ítems añadidos",
				font=self._get_font("label"),
				text_color=self._text_sec
			)
			lbl_vacio.pack(pady=40)
			self._actualizar_total()
			return

		# Crear una fila por ítem
		for idx, item in enumerate(self.items):
			fila = ctk.CTkFrame(self.filas_frame, fg_color=self._bg, corner_radius=6)
			fila.pack(fill="x", padx=4, pady=3)

			valores = [
				str(item.cantidad),
				item.tipo_nombre or "",
				item.variante_nombre or "-",
				item.diseno_nombre or "",
				item.diseno_coleccion or "-",
				item.genero or "",
				item.talla or "",
				item.color_nombre or "",
				"Sí" if item.produccion_mixta else "No",
			]

			for i, val in enumerate(valores):
				lbl = ctk.CTkLabel(
					fila,
					text=val,
					font=self._get_font("label"),
					text_color=self._text,
					width=self._col_widths[i],
					anchor="w"
				)
				lbl.pack(side="left", padx=(6, 0))

			# Botón eliminar
			btn_eliminar = ctk.CTkButton(
				master=fila,
				text="X",
				command=lambda i=idx: self.eliminar_item(i),
				width=30,
				height=28,
				fg_color="#e74c3c",
				hover_color="#c0392b",
				text_color="#FFFFFF",
				cursor="hand2"
			)
			btn_eliminar.pack(side="right", padx=(0, 4))

		self._actualizar_total()

	def _actualizar_total(self):
		"""Actualizar el label del total de unidades."""
		total = sum(item.cantidad for item in self.items)
		self.lbl_total.configure(text=f"TOTAL UNIDADES: {total}")

	# --- Navegación por teclado ---

	def _setup_keyboard_nav(self):
		"""Configurar bindings de navegación por teclado."""
		self._nav_buttons = [self.btn_volver, self.btn_anadir, self.btn_confirmar]
		self._nav_callbacks = [self._on_volver, self._on_anadir, self._on_confirmar]
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
		self._on_destroy()
		self.frame.destroy()
