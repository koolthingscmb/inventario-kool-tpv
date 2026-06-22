"""Subvista de selección de cantidad.

Contiene la clase `NuevaProduccionCantidadView` que muestra botones
para seleccionar cantidad (+1, +5, +10), producción mixta y navegación.
"""
import tkinter as tk
from dataclasses import dataclass
from typing import Callable, Optional

import customtkinter as ctk

from kool_tpv.modulos.produccion.ui.subvistas.config_helper import cargar_config_produccion, get_font, get_chip_config, get_chip_style, get_nav_button_config, get_nav_button_style
from kool_tpv.utils.keyboard_nav_mixin import KeyboardNavigableMixin


@dataclass
class CantidadSeleccion:
	"""Resultado de la selección de cantidad."""
	cantidad: int
	produccion_mixta: bool = False


class NuevaProduccionCantidadView(KeyboardNavigableMixin):
	"""Subvista para seleccionar la cantidad mediante botones.

	Args:
		parent: Widget padre donde se mostrará la subvista.
		on_siguiente: Callback cuando se pulsa SIGUIENTE (recibe CantidadSeleccion).
		on_volver: Callback cuando se pulsa VOLVER.
		on_anadir: Callback cuando se pulsa OTRO PRODUCTO (recibe CantidadSeleccion).
		mostrar_mixta: Si True, muestra el botón MIXTA.
	"""

	def __init__(self, parent,
	             on_siguiente: Optional[Callable[[CantidadSeleccion], None]] = None,
	             on_volver: Optional[Callable] = None,
	             on_anadir: Optional[Callable[[CantidadSeleccion], None]] = None,
	             mostrar_mixta: bool = False,
	             diseno_nombre: str = ""):
		KeyboardNavigableMixin.__init_keyboard_mixin__(self)
		self.parent = parent
		self.on_siguiente = on_siguiente
		self.on_volver = on_volver
		self.on_anadir = on_anadir
		self.mostrar_mixta = mostrar_mixta
		self.diseno_nombre = diseno_nombre
		self.cantidad: int = 0
		self.produccion_mixta: bool = False
		self._mixta_seleccionada: bool = False

		# Cargar configuración
		self.config = cargar_config_produccion()
		self._colors = self.config.get("colors", {})
		self._bg = self._colors.get("background", "#2c3e50")
		self._text = self._colors.get("text", "#ecf0f1")
		self._text_sec = self._colors.get("text_secondary", "#95a5a6")
		self._chip_cfg = get_chip_config(self.config, "cantidad")

		# Frame principal
		self.frame = ctk.CTkFrame(parent, fg_color=self._bg)
		self.frame.pack(fill="both", expand=True)

		# Título + botones
		self._crear_titulo()
		self._crear_botones_cantidad()
		if self.mostrar_mixta:
			self._crear_boton_mixta()
		self._crear_boton_otro_producto()
		self._crear_botones_navegacion()

		# Configurar navegación con KeyboardNavigableMixin
		self._navigable_buttons = []
		for btn in self._btns_cantidad:
			self._navigable_buttons.append((btn, lambda b=btn: self._on_cantidad_btn(b)))
		if self.mostrar_mixta:
			self._navigable_buttons.append((self.btn_mixta, self._on_mixta_toggle))
		self._navigable_buttons.append((self.btn_otro, self._on_anadir))
		self._navigable_buttons.append((self.btn_volver, self._on_volver))
		self._navigable_buttons.append((self.btn_siguiente, self._on_siguiente))

		if self._navigable_buttons:
			try:
				self._nav_toplevel = self.frame.winfo_toplevel()
			except Exception:
				self._nav_toplevel = self.frame
			self._nav_toplevel.bind("<Tab>", self._on_nav_tab_next)
			self._nav_toplevel.bind("<Shift-Tab>", self._on_nav_tab_prev)
			self._nav_toplevel.bind("<Return>", self._on_nav_enter)
			self._nav_toplevel.bind("<KP_Enter>", self._on_nav_enter)
			self.frame.bind("<Destroy>", self._on_nav_destroy)

		if self._navigable_buttons:
			self.frame.after(100, lambda: self._focus_nav_widget(0))

	def _get_font(self, key: str) -> tuple:
		"""Obtener una fuente desde la configuración."""
		return get_font(self.config, key)

	def _crear_titulo(self):
		"""Crear el título de la subvista."""
		txt = f"CANTIDAD para {self.diseno_nombre}" if self.diseno_nombre else "CANTIDAD"
		titulo = ctk.CTkLabel(
			self.frame,
			text=txt,
			font=self._get_font("title"),
			text_color=self._text,
			fg_color=self._bg
		)
		titulo.pack(pady=(20, 5))

		self.lbl_total = ctk.CTkLabel(
			self.frame,
			text="TOTAL: 0",
			font=self._get_font("subtitle"),
			text_color=self._text_sec,
			fg_color=self._bg
		)
		self.lbl_total.pack(pady=(0, 10))

	def _crear_botones_cantidad(self):
		"""Crear los botones +1, +5, +10."""
		frame_cant = ctk.CTkFrame(self.frame, fg_color=self._bg)
		frame_cant.pack(pady=(10, 10))

		style = get_chip_style(self._chip_cfg, "default")
		font_key = self._chip_cfg.get("font_key", "label")
		font_family = get_font(self.config, font_key)
		chip_font = (font_family[0], style.get("font_size", 14), font_family[2])
		corner_radius = self._chip_cfg.get("corner_radius", 8)
		chip_height = self._chip_cfg.get("height", 48)

		self._btns_cantidad = []
		for label in ("+1", "+5", "+10"):
			btn = ctk.CTkButton(
				master=frame_cant,
				text=label,
				fg_color=style.get("bg", "#1a1a2e"),
				text_color=style.get("text", "#e0e0e0"),
				border_color=style.get("border", "#552583"),
				hover_color=style.get("hover", "#C77BFF"),
				border_width=style.get("border_width", 2),
				corner_radius=corner_radius,
				height=chip_height,
				width=120,
				font=chip_font,
				cursor="hand2"
			)
			btn.pack(side=tk.LEFT, padx=12)
			btn.bind("<Button-1>", lambda e, b=btn: self._on_cantidad_btn(b))
			setattr(btn, "_incremento", int(label[1:]))
			self._btns_cantidad.append(btn)

	def _crear_boton_mixta(self):
		"""Crear el botón MIXTA."""
		frame_mixta = ctk.CTkFrame(self.frame, fg_color=self._bg)
		frame_mixta.pack(pady=(10, 10))

		style = get_chip_style(self._chip_cfg, "default")
		font_key = self._chip_cfg.get("font_key", "label")
		font_family = get_font(self.config, font_key)
		chip_font = (font_family[0], style.get("font_size", 14), font_family[2])
		corner_radius = self._chip_cfg.get("corner_radius", 8)
		chip_height = self._chip_cfg.get("height", 48)

		self.btn_mixta = ctk.CTkButton(
			master=frame_mixta,
			text="MIXTA",
			fg_color=style.get("bg", "#1a1a2e"),
			text_color=style.get("text", "#e0e0e0"),
			border_color=style.get("border", "#552583"),
			hover_color=style.get("hover", "#C77BFF"),
			border_width=style.get("border_width", 2),
			corner_radius=corner_radius,
			height=chip_height,
			width=300,
			font=chip_font,
			cursor="hand2"
		)
		self.btn_mixta.pack()
		self.btn_mixta.bind("<Button-1>", lambda e: self._on_mixta_toggle())

	def _crear_boton_otro_producto(self):
		"""Crear el botón OTRO PRODUCTO."""
		frame_otro = ctk.CTkFrame(self.frame, fg_color=self._bg)
		frame_otro.pack(pady=(10, 10))

		style = get_chip_style(self._chip_cfg, "default")
		font_key = self._chip_cfg.get("font_key", "label")
		font_family = get_font(self.config, font_key)
		chip_font = (font_family[0], style.get("font_size", 14), font_family[2])
		corner_radius = self._chip_cfg.get("corner_radius", 8)
		chip_height = self._chip_cfg.get("height", 48)

		self.btn_otro = ctk.CTkButton(
			master=frame_otro,
			text="OTRO PRODUCTO",
			fg_color=style.get("bg", "#1a1a2e"),
			text_color=style.get("text", "#e0e0e0"),
			border_color=style.get("border", "#552583"),
			hover_color=style.get("hover", "#C77BFF"),
			border_width=style.get("border_width", 2),
			corner_radius=corner_radius,
			height=chip_height,
			width=300,
			font=chip_font,
			cursor="hand2"
		)
		self.btn_otro.pack()
		self.btn_otro.bind("<Button-1>", lambda e: self._on_anadir())

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

	# --- Lógica ---

	def _on_cantidad_btn(self, btn):
		"""Incrementar la cantidad según el botón pulsado."""
		incremento = getattr(btn, "_incremento", 0)
		self.cantidad += incremento
		self.lbl_total.configure(text=f"TOTAL: {self.cantidad}")

	def _on_mixta_toggle(self):
		"""Alternar selección de producción mixta."""
		self._mixta_seleccionada = not self._mixta_seleccionada
		self.produccion_mixta = self._mixta_seleccionada
		selected_style = get_chip_style(self._chip_cfg, "selected")
		default_style = get_chip_style(self._chip_cfg, "default")
		font_key = self._chip_cfg.get("font_key", "label")
		font_family = get_font(self.config, font_key)
		if self._mixta_seleccionada:
			self.btn_mixta.configure(
				fg_color=selected_style.get("bg", "#552583"),
				text_color=selected_style.get("text", "#ffffff"),
				border_color=selected_style.get("border", "#C77BFF"),
				hover_color=selected_style.get("hover", "#8e44ad"),
				border_width=selected_style.get("border_width", 4),
				font=(font_family[0], selected_style.get("font_size", 14), font_family[2])
			)
		else:
			self.btn_mixta.configure(
				fg_color=default_style.get("bg", "#1a1a2e"),
				text_color=default_style.get("text", "#e0e0e0"),
				border_color=default_style.get("border", "#552583"),
				hover_color=default_style.get("hover", "#C77BFF"),
				border_width=default_style.get("border_width", 2),
				font=(font_family[0], default_style.get("font_size", 14), font_family[2])
			)

	def _on_siguiente(self):
		"""Manejador del botón SIGUIENTE."""
		if self.cantidad < 1:
			return
		if self.on_siguiente:
			result = CantidadSeleccion(
				cantidad=self.cantidad,
				produccion_mixta=self.produccion_mixta
			)
			self.on_siguiente(result)

	def _on_anadir(self):
		"""Manejador del botón OTRO PRODUCTO."""
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
		return CantidadSeleccion(
			cantidad=self.cantidad,
			produccion_mixta=self.produccion_mixta
		)

	def destruir(self):
		"""Destruir la subvista y limpiar recursos."""
		self.clear_keyboard_navigation()
		self.frame.destroy()
