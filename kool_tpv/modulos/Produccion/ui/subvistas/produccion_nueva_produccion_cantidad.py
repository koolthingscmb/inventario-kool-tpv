"""Subvista de selección de cantidad.

Contiene la clase `NuevaProduccionCantidadView` que muestra un entry numérico
para la cantidad y un checkbox de producción mixta (solo visible si el tipo
de producto lo permite, ej. camiseta).
"""
import tkinter as tk
from dataclasses import dataclass
from typing import Callable, Optional

import customtkinter as ctk

from kool_tpv.modulos.produccion.ui.subvistas.config_helper import cargar_config_produccion, get_font, get_chip_config, get_chip_style, get_nav_button_config, get_nav_button_style


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
		mostrar_mixta: Si True, muestra el checkbox de producción mixta.
	"""

	def __init__(self, parent,
	             on_siguiente: Optional[Callable[[CantidadSeleccion], None]] = None,
	             on_volver: Optional[Callable] = None,
	             mostrar_mixta: bool = False):
		self.parent = parent
		self.on_siguiente = on_siguiente
		self.on_volver = on_volver
		self.mostrar_mixta = mostrar_mixta
		self.cantidad: int = 0
		self.produccion_mixta: bool = False

		# Cargar configuración
		self.config = cargar_config_produccion()
		self._colors = self.config.get("colors", {})
		self._bg = self._colors.get("background", "#2c3e50")
		self._text = self._colors.get("text", "#ecf0f1")
		self._text_sec = self._colors.get("text_secondary", "#95a5a6")
		self._chip_cfg = get_chip_config(self.config, "producto")

		# Frame principal
		self.frame = tk.Frame(parent, bg=self._bg)
		self.frame.pack(fill=tk.BOTH, expand=True)

		# Título + cantidad + mixta
		self._crear_titulo()
		self._crear_campo_cantidad()
		if self.mostrar_mixta:
			self._crear_checkbox_mixta()

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
			text="CANTIDAD",
			font=self._get_font("title"),
			text_color=self._text,
			fg_color=self._bg
		)
		titulo.pack(pady=(20, 10))

	def _crear_campo_cantidad(self):
		"""Crear el campo de entrada de cantidad."""
		frame_cantidad = ctk.CTkFrame(self.frame, fg_color=self._bg)
		frame_cantidad.pack(pady=(20, 10))

		lbl = ctk.CTkLabel(
			frame_cantidad,
			text="Unidades:",
			font=self._get_font("label"),
			text_color=self._text,
			fg_color=self._bg
		)
		lbl.pack(side="left", padx=(0, 10))

		self.entry_cantidad = ctk.CTkEntry(
			frame_cantidad,
			font=self._get_font("entry"),
			width=120,
			height=40,
			justify="center"
		)
		self.entry_cantidad.pack(side="left")
		self.entry_cantidad.insert(0, "1")
		self.entry_cantidad.bind("<KeyRelease>", self._on_cantidad_change)
		self.entry_cantidad.bind("<Return>", self._on_cantidad_enter)
		self.entry_cantidad.bind("<KP_Enter>", self._on_cantidad_enter)

		# Botones + / -
		frame_pm = ctk.CTkFrame(self.frame, fg_color=self._bg)
		frame_pm.pack(pady=(0, 10))

		btn_menos = ctk.CTkButton(
			master=frame_pm,
			text="-",
			command=self._decrementar,
			width=50,
			height=40,
			cursor="hand2"
		)
		btn_menos.pack(side="left", padx=5)

		btn_mas = ctk.CTkButton(
			master=frame_pm,
			text="+",
			command=self._incrementar,
			width=50,
			height=40,
			cursor="hand2"
		)
		btn_mas.pack(side="left", padx=5)

	def _crear_checkbox_mixta(self):
		"""Crear el checkbox de producción mixta."""
		self.chk_mixta_var = tk.IntVar(value=0)
		self.chk_mixta = ctk.CTkCheckBox(
			self.frame,
			text="PRODUCCIÓN MIXTA",
			font=self._get_font("label"),
			text_color=self._text,
			fg_color=self._bg,
			variable=self.chk_mixta_var,
			command=self._on_mixta_change
		)
		self.chk_mixta.pack(pady=(10, 0))

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

		# Botón SIGUIENTE
		nav_sig = get_nav_button_config(self.config, "siguiente")
		style_siguiente = get_nav_button_style(self.config, nav_sig.get("style_key", "siguiente"))
		self.btn_siguiente = tk.Button(
			frame_nav,
			text=nav_sig.get("text", "SIGUIENTE"),
			font=self._get_font(nav_sig.get("font_key", "button")),
			bg=style_siguiente.get("bg", "#27ae60"),
			fg=style_siguiente.get("text", "#FFFFFF"),
			activebackground=style_siguiente.get("hover", "#2ecc71"),
			activeforeground=style_siguiente.get("text", "#FFFFFF"),
			takefocus=True,
			bd=nav_sig.get("bd", 0),
			width=nav_sig.get("width", 15),
			height=nav_sig.get("height", 2),
			command=self._on_siguiente
		)
		self.btn_siguiente.pack(side=tk.RIGHT, padx=10)

	# --- Lógica de cantidad ---

	def _on_cantidad_change(self, event):
		"""Manejador del cambio de texto en el entry."""
		self._validar_cantidad()

	def _on_cantidad_enter(self, event):
		"""Enter en el entry: ir al siguiente paso."""
		self._on_siguiente()
		return "break"

	def _validar_cantidad(self):
		"""Validar que el entry contenga un número entero positivo."""
		valor = self.entry_cantidad.get().strip()
		try:
			self.cantidad = int(valor)
			if self.cantidad < 1:
				self.cantidad = 0
		except ValueError:
			self.cantidad = 0

	def _incrementar(self):
		"""Incrementar la cantidad en 1."""
		try:
			actual = int(self.entry_cantidad.get())
		except ValueError:
			actual = 0
		self.entry_cantidad.delete(0, "end")
		self.entry_cantidad.insert(0, str(actual + 1))
		self._validar_cantidad()
		self.entry_cantidad.focus_set()

	def _decrementar(self):
		"""Decrementar la cantidad en 1 (mínimo 1)."""
		try:
			actual = int(self.entry_cantidad.get())
		except ValueError:
			actual = 1
		if actual > 1:
			self.entry_cantidad.delete(0, "end")
			self.entry_cantidad.insert(0, str(actual - 1))
		self._validar_cantidad()
		self.entry_cantidad.focus_set()

	def _on_mixta_change(self):
		"""Manejador del checkbox de producción mixta."""
		self.produccion_mixta = self.chk_mixta_var.get() == 1

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
		self.frame.focus_get()
		# Tab simple: mover entre entry, checkbox (si existe) y botones
		focus = self.frame.focus_get()
		if focus is self.entry_cantidad:
			if self.mostrar_mixta:
				self.chk_mixta.focus_set()
			else:
				self.btn_siguiente.focus_set()
		elif hasattr(self, "chk_mixta") and focus is self.chk_mixta:
			self.btn_siguiente.focus_set()
		else:
			self.entry_cantidad.focus_set()
		return "break"

	def _on_tab_prev(self, event):
		focus = self.frame.focus_get()
		if focus is self.entry_cantidad:
			self.btn_siguiente.focus_set()
		elif hasattr(self, "chk_mixta") and focus is self.chk_mixta:
			self.entry_cantidad.focus_set()
		else:
			if self.mostrar_mixta:
				self.chk_mixta.focus_set()
			else:
				self.entry_cantidad.focus_set()
		return "break"

	def _on_enter_nav(self, event):
		"""Enter activa el widget con foco."""
		focus = self.frame.focus_get()
		if focus is self.entry_cantidad:
			self._on_siguiente()
		elif hasattr(self, "chk_mixta") and focus is self.chk_mixta:
			self._on_mixta_change()
		elif focus is self.btn_siguiente:
			self._on_siguiente()
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
