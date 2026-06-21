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
	talla: Optional[str] = None
	color_nombre: Optional[str] = None
	color_id: Optional[int] = None
	diseno_codigo: Optional[str] = None
	diseno_nombre: Optional[str] = None
	cantidad: int = 0
	produccion_mixta: bool = False
	coste_unitario: float = 0.0
	coste_total: float = 0.0

	def texto_resumen(self) -> str:
		"""Texto de una línea para mostrar en la lista."""
		partes = [f"{self.cantidad}x {self.tipo_nombre}"]
		if self.diseno_nombre:
			partes.append(self.diseno_nombre)
		if self.talla:
			partes.append(f"T:{self.talla}")
		if self.color_nombre:
			partes.append(f"C:{self.color_nombre}")
		if self.produccion_mixta:
			partes.append("[MIXTA]")
		return "  |  ".join(partes)

	def texto_coste(self) -> str:
		"""Texto del coste para mostrar en la lista."""
		return f"{self.coste_total:.2f}€"


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

		# Título + lista + total
		self._crear_titulo()
		self._crear_lista()
		self._crear_total()

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

	def _crear_lista(self):
		"""Crear el frame scrollable para la lista de ítems."""
		self.lista_frame = ctk.CTkScrollableFrame(
			self.frame,
			fg_color=self._bg,
			label_text=""
		)
		self.lista_frame.pack(expand=True, fill="both", padx=40, pady=(0, 10))

	def _crear_total(self):
		"""Crear el label del coste total."""
		self.lbl_total = ctk.CTkLabel(
			self.frame,
			text="TOTAL: 0.00€",
			font=self._get_font("subtitle"),
			text_color=self._text,
			fg_color=self._bg
		)
		self.lbl_total.pack(pady=(0, 10))

	def _crear_botones_navegacion(self):
		"""Crear los botones de navegación inferior."""
		frame_nav = tk.Frame(self.frame, bg=self._bg)
		frame_nav.pack(fill=tk.X, padx=40, pady=20)

		# Botón VOLVER
		nav_volver = get_nav_button_config(self.config, "volver")
		style_volver = get_nav_button_style(self.config, nav_volver.get("style_key", "volver"))
		btn_volver = tk.Button(
			frame_nav,
			text=nav_volver.get("text", "VOLVER"),
			font=self._get_font(nav_volver.get("font_key", "button")),
			bg=style_volver.get("bg", "#e74c3c"),
			fg=style_volver.get("text", "#FFFFFF"),
			activebackground=style_volver.get("hover", "#c0392b"),
			activeforeground=style_volver.get("text", "#FFFFFF"),
			takefocus=True,
			bd=nav_volver.get("bd", 0),
			width=nav_volver.get("width", 15),
			height=nav_volver.get("height", 2),
			command=self._on_volver
		)
		btn_volver.pack(side=tk.LEFT, padx=10)

		# Botón AÑADIR
		nav_anadir = get_nav_button_config(self.config, "anadir")
		style_anadir = get_nav_button_style(self.config, nav_anadir.get("style_key", "anadir"))
		btn_anadir = tk.Button(
			frame_nav,
			text=nav_anadir.get("text", "AÑADIR"),
			font=self._get_font(nav_anadir.get("font_key", "button")),
			bg=style_anadir.get("bg", "#27ae60"),
			fg=style_anadir.get("text", "#FFFFFF"),
			activebackground=style_anadir.get("hover", "#2ecc71"),
			activeforeground=style_anadir.get("text", "#FFFFFF"),
			takefocus=True,
			bd=nav_anadir.get("bd", 0),
			width=nav_anadir.get("width", 15),
			height=nav_anadir.get("height", 2),
			command=self._on_anadir
		)
		btn_anadir.pack(side=tk.LEFT, padx=(10, 0))

		# Botón CONFIRMAR
		nav_conf = get_nav_button_config(self.config, "confirmar")
		style_confirmar = get_nav_button_style(self.config, nav_conf.get("style_key", "confirmar"))
		self.btn_confirmar = tk.Button(
			frame_nav,
			text=nav_conf.get("text", "CONFIRMAR"),
			font=self._get_font(nav_conf.get("font_key", "button")),
			bg=style_confirmar.get("bg", "#27ae60"),
			fg=style_confirmar.get("text", "#FFFFFF"),
			activebackground=style_confirmar.get("hover", "#2ecc71"),
			activeforeground=style_confirmar.get("text", "#FFFFFF"),
			takefocus=True,
			bd=nav_conf.get("bd", 0),
			width=nav_conf.get("width", 15),
			height=nav_conf.get("height", 2),
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
		"""Refrescar la lista visual de ítems."""
		# Limpiar lista
		for w in list(self.lista_frame.winfo_children()):
			w.destroy()

		if not self.items:
			lbl_vacio = ctk.CTkLabel(
				self.lista_frame,
				text="No hay ítems añadidos",
				font=self._get_font("label"),
				text_color=self._text_sec
			)
			lbl_vacio.pack(pady=40)
			self._actualizar_total()
			return

		# Crear una fila por ítem
		for idx, item in enumerate(self.items):
			fila = ctk.CTkFrame(self.lista_frame, fg_color=self._bg)
			fila.pack(fill="x", padx=4, pady=4)

			# Texto del ítem
			lbl = ctk.CTkLabel(
				fila,
				text=item.texto_resumen(),
				font=self._get_font("label"),
				text_color=self._text,
				fg_color=self._bg,
				anchor="w"
			)
			lbl.pack(side="left", expand=True, fill="x", padx=(4, 8))

			# Coste
			lbl_coste = ctk.CTkLabel(
				fila,
				text=item.texto_coste(),
				font=self._get_font("label"),
				text_color=self._text_sec,
				fg_color=self._bg,
				width=80
			)
			lbl_coste.pack(side="right", padx=(8, 4))

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
		"""Actualizar el label del coste total."""
		total = sum(item.coste_total for item in self.items)
		self.lbl_total.configure(text=f"TOTAL: {total:.2f}€")

	# --- Navegación por teclado ---

	def _setup_keyboard_nav(self):
		"""Configurar bindings de navegación por teclado."""
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

	def _on_tab_next(self, event):
		focus = self.frame.focus_get()
		if focus is None:
			self.btn_confirmar.focus_set()
		elif focus is self.btn_confirmar:
			self._on_volver()
		return "break"

	def _on_tab_prev(self, event):
		focus = self.frame.focus_get()
		if focus is None:
			self.btn_confirmar.focus_set()
		return "break"

	def _on_enter_nav(self, event):
		"""Enter activa CONFIRMAR si hay ítems."""
		if self.items:
			self._on_confirmar()
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
