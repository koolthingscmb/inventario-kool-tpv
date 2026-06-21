"""Subvista de selección de cantidad.

Contiene la clase `NuevaProduccionCantidadView` que muestra un entry grande
para la cantidad y botones SÍ/NO para indicar producción mixta.
"""
import tkinter as tk
from dataclasses import dataclass
from typing import Callable, Optional

import customtkinter as ctk

from kool_tpv.modulos.produccion.ui.subvistas.config_helper import cargar_config_produccion, get_font, get_nav_button_config, get_nav_button_style


@dataclass
class CantidadSeleccion:
	"""Resultado de la selección de cantidad."""
	cantidad: int
	produccion_mixta: bool = False


class NuevaProduccionCantidadView:
	"""Subvista para introducir la cantidad y producción mixta.

	Args:
		parent: Widget padre donde se mostrará la subvista.
		on_siguiente: Callback cuando se pulsa SIGUIENTE (recibe CantidadSeleccion).
		on_volver: Callback cuando se pulsa VOLVER.
		mostrar_mixta: Si True, muestra el entry de producción mixta.
	"""

	def __init__(self, parent,
	             on_siguiente: Optional[Callable[[CantidadSeleccion], None]] = None,
	             on_volver: Optional[Callable] = None,
	             on_anadir: Optional[Callable[[CantidadSeleccion], None]] = None,
	             mostrar_mixta: bool = False):
		self.parent = parent
		self.on_siguiente = on_siguiente
		self.on_volver = on_volver
		self.on_anadir = on_anadir
		self.mostrar_mixta = mostrar_mixta
		self.cantidad: int = 1
		self.produccion_mixta: bool = False

		# Cargar configuración
		self.config = cargar_config_produccion()
		self._colors = self.config.get("colors", {})
		self._bg = self._colors.get("background", "#2c3e50")
		self._text = self._colors.get("text", "#ecf0f1")
		self._text_sec = self._colors.get("text_secondary", "#95a5a6")

		# Frame principal
		self.frame = tk.Frame(parent, bg=self._bg)
		self.frame.pack(fill=tk.BOTH, expand=True)

		# Título + entry + botones mixta
		self._crear_titulo()
		self._crear_campo_cantidad()
		if self.mostrar_mixta:
			self._crear_botones_mixta()

		# Botones de navegación
		self._crear_botones_navegacion()

		# Navegación por teclado
		self._setup_keyboard_nav()

		# Foco automático en el entry de cantidad
		def _focus_cantidad():
			try:
				self.entry_cantidad._entry.focus_set()
			except Exception:
				self.entry_cantidad.focus_set()
		self.frame.after(100, _focus_cantidad)

	def _get_font(self, key: str) -> tuple:
		"""Obtener una fuente desde la configuración."""
		return get_font(self.config, key)

	def _crear_titulo(self):
		"""Crear el título de la subvista."""
		titulo = ctk.CTkLabel(
			self.frame,
			text="CANTIDAD",
			font=self._get_font("title"),
			text_color=self._text,
			fg_color=self._bg
		)
		titulo.pack(pady=(20, 10))

	def _crear_campo_cantidad(self):
		"""Crear el entry gigante de cantidad."""
		frame_cantidad = ctk.CTkFrame(self.frame, fg_color=self._bg)
		frame_cantidad.pack(pady=(30, 10))

		lbl = ctk.CTkLabel(
			frame_cantidad,
			text="UNIDADES",
			font=self._get_font("subtitle"),
			text_color=self._text_sec,
			fg_color=self._bg
		)
		lbl.pack(pady=(0, 5))

		self.entry_cantidad = ctk.CTkEntry(
			frame_cantidad,
			font=self._get_font("title"),
			width=300,
			height=120,
			justify="center"
		)
		self.entry_cantidad.pack()
		self.entry_cantidad.insert(0, "1")
		_entry = self.entry_cantidad._entry if hasattr(self.entry_cantidad, '_entry') else self.entry_cantidad
		_entry.bind("<Return>", self._on_cantidad_enter)
		_entry.bind("<KP_Enter>", self._on_cantidad_enter)

	def _crear_botones_mixta(self):
		"""Crear botones SÍ/NO para producción mixta."""
		frame_mixta = ctk.CTkFrame(self.frame, fg_color=self._bg)
		frame_mixta.pack(pady=(20, 10))

		lbl = ctk.CTkLabel(
			frame_mixta,
			text="¿ES MIXTA?",
			font=self._get_font("subtitle"),
			text_color=self._text_sec,
			fg_color=self._bg
		)
		lbl.pack(pady=(0, 10))

		frame_btns_mixta = ctk.CTkFrame(frame_mixta, fg_color=self._bg)
		frame_btns_mixta.pack()

		self.btn_mixta_no = ctk.CTkButton(
			frame_btns_mixta,
			text="NO",
			font=self._get_font("button"),
			fg_color="#1a1a2e",
			hover_color="#333333",
			text_color="#e0e0e0",
			border_color="#555555",
			border_width=2,
			width=120,
			height=50,
			cursor="hand2",
			command=self._on_mixta_no
		)
		self.btn_mixta_no.pack(side=tk.LEFT, padx=10)

		self.btn_mixta_si = ctk.CTkButton(
			frame_btns_mixta,
			text="SÍ",
			font=self._get_font("button"),
			fg_color="#1a1a2e",
			hover_color="#333333",
			text_color="#e0e0e0",
			border_color="#555555",
			border_width=2,
			width=120,
			height=50,
			cursor="hand2",
			command=self._on_mixta_si
		)
		self.btn_mixta_si.pack(side=tk.LEFT, padx=10)

		self.produccion_mixta = False

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

		# Botón AÑADIR (al lado de SIGUIENTE)
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
		self.btn_anadir.pack(side=tk.RIGHT, padx=(0, 10))

	# --- Lógica de cantidad ---

	def _on_cantidad_enter(self, event):
		"""Enter en el entry de cantidad: pasar al siguiente widget (Tab natural)."""
		return "break"

	def _on_mixta_si(self):
		"""Seleccionar producción mixta SÍ."""
		self.produccion_mixta = True
		self.btn_mixta_si.configure(fg_color="#27ae60", text_color="#FFFFFF")
		self.btn_mixta_no.configure(fg_color="#1a1a2e", text_color="#e0e0e0")

	def _on_mixta_no(self):
		"""Seleccionar producción mixta NO."""
		self.produccion_mixta = False
		self.btn_mixta_no.configure(fg_color="#e74c3c", text_color="#FFFFFF")
		self.btn_mixta_si.configure(fg_color="#1a1a2e", text_color="#e0e0e0")

	def _validar_cantidad(self):
		"""Validar que el entry contenga un número entero positivo."""
		valor = self.entry_cantidad.get().strip()
		try:
			self.cantidad = int(valor)
			if self.cantidad < 1:
				self.cantidad = 0
		except ValueError:
			self.cantidad = 0

	# --- Navegación por teclado ---

	def _setup_keyboard_nav(self):
		"""Configurar bindings de teclado."""
		toplevel = self.frame.winfo_toplevel()
		toplevel.bind("<Return>", self._on_enter_nav)
		toplevel.bind("<KP_Enter>", self._on_enter_nav)

		self.frame.bind("<Destroy>", self._on_destroy)

	def _on_destroy(self, event=None):
		"""Limpiar bindings al destruir."""
		try:
			toplevel = self.frame.winfo_toplevel()
			for key in ("<Return>", "<KP_Enter>"):
				toplevel.unbind(key)
		except Exception:
			pass

	def _on_enter_nav(self, event):
		"""Enter: si está en el entry de cantidad, pasar foco al siguiente widget."""
		focus = self.frame.focus_get()
		is_cantidad = focus is self.entry_cantidad or (hasattr(self.entry_cantidad, '_entry') and focus is self.entry_cantidad._entry)
		if is_cantidad:
			self.frame.focus_set()
			self.frame.event_generate("<Tab>")
		return "break"

	# --- Callbacks de navegación ---

	def _on_siguiente(self):
		"""Manejador del botón SIGUIENTE."""
		self._validar_cantidad()
		if self.cantidad < 1:
			return
		if self.on_siguiente:
			result = CantidadSeleccion(
				cantidad=self.cantidad,
				produccion_mixta=self.produccion_mixta
			)
			self.on_siguiente(result)

	def _on_anadir(self):
		"""Manejador del botón AÑADIR."""
		self._validar_cantidad()
		if self.cantidad < 1:
			return
		if self.on_anadir:
			result = CantidadSeleccion(
				cantidad=self.cantidad,
				produccion_mixta=self.produccion_mixta
			)
			self.on_anadir(result)

	def _on_volver(self):
		"""Manejador del botón VOLVER."""
		if self.on_volver:
			self.on_volver()

	def obtener_seleccion(self) -> CantidadSeleccion:
		"""Obtener la selección de cantidad.

		Returns:
			Objeto CantidadSeleccion con cantidad y produccion_mixta.
		"""
		self._validar_cantidad()
		return CantidadSeleccion(
			cantidad=self.cantidad,
			produccion_mixta=self.produccion_mixta
		)

	def destruir(self):
		"""Destruir la subvista y limpiar recursos."""
		self._on_destroy()
		self.frame.destroy()
