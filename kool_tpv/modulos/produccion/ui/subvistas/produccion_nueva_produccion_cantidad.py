"""Subvista de selección de cantidad.

Contiene la clase `NuevaProduccionCantidadView` que muestra botones
para seleccionar cantidad (+1, +5, +10), producción mixta y navegación.
"""
import tkinter as tk
import logging
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
	extra_id: Optional[int] = None
	extra_coste: float = 0.0
	extra_nombre: Optional[str] = None


class NuevaProduccionCantidadView(KeyboardNavigableMixin):
	"""Subvista para seleccionar la cantidad mediante botones.

	Args:
		parent: Widget padre donde se mostrará la subvista.
		on_siguiente: Callback cuando se pulsa SIGUIENTE (recibe CantidadSeleccion).
		on_volver: Callback cuando se pulsa VOLVER.
		on_anadir: Callback cuando se pulsa OTRO PRODUCTO (recibe CantidadSeleccion).
		mostrar_mixta: Si True, muestra el botón MIXTA.
	"""

	def __init__(self, parent, db: Database,
	             on_siguiente: Optional[Callable[[CantidadSeleccion], None]] = None,
	             on_volver: Optional[Callable] = None,
	             on_anadir: Optional[Callable[[CantidadSeleccion], None]] = None,
	             on_origen: Optional[Callable] = None,
	             mostrar_mixta: bool = False,
	             diseno_nombre: str = "",
	             stock_disponible: int = 0):
		KeyboardNavigableMixin.__init_keyboard_mixin__(self)
		self.parent = parent
		self.db = db
		self.on_siguiente = on_siguiente
		self.on_volver = on_volver
		self.on_anadir = on_anadir
		self.on_origen = on_origen
		self.mostrar_mixta = mostrar_mixta
		self.diseno_nombre = diseno_nombre
		self.cantidad: int = 0
		self.stock_disponible: int = stock_disponible
		
		from kool_tpv.modulos.produccion.services.produccion_extras_service import ProduccionExtrasService
		self.extras_service = ProduccionExtrasService(db)
		self.extra_seleccionado: Optional[any] = None
		self._extra_btns = {}

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
		self._crear_chips_extras()
		self._crear_boton_otro_producto()
		self._crear_botones_navegacion()

		# Configurar navegación con KeyboardNavigableMixin
		self._navigable_buttons = []
		for btn in self._btns_cantidad:
			self._navigable_buttons.append((btn, lambda b=btn: self._on_cantidad_btn(b)))
		
		for btn in self._extra_btns.values():
			self._navigable_buttons.append((btn, lambda b=btn: self._on_extra_click(getattr(b, "_extra_obj"))))

		self._navigable_buttons.append((self.btn_otro, self._on_anadir))
		self._navigable_buttons.append((self.btn_origen, self._on_origen))
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

		stock_txt = f"Stock disponible: {self.stock_disponible}" if self.stock_disponible > 0 else ""
		if stock_txt:
			self.lbl_stock = ctk.CTkLabel(
				self.frame,
				text=stock_txt,
				font=self._get_font("label"),
				text_color=self._text_sec,
				fg_color=self._bg
			)
			self.lbl_stock.pack(pady=(0, 5))

		self.lbl_total = ctk.CTkLabel(
			self.frame,
			text="TOTAL: 0",
			font=self._get_font("subtitle"),
			text_color=self._text_sec,
			fg_color=self._bg
		)
		self.lbl_total.pack(pady=(0, 10))

	def _crear_botones_cantidad(self):
		"""Crear los botones -1, +1, +5, +10."""
		frame_cant = ctk.CTkFrame(self.frame, fg_color=self._bg)
		frame_cant.pack(pady=(10, 10))

		style = get_chip_style(self._chip_cfg, "default")
		font_key = self._chip_cfg.get("font_key", "label")
		font_family = get_font(self.config, font_key)
		chip_font = (font_family[0], style.get("font_size", 14), font_family[2])
		corner_radius = self._chip_cfg.get("corner_radius", 8)
		chip_height = self._chip_cfg.get("height", 48)

		self._btns_cantidad = []
		
		# Botón -1 (Naranja/Rojo para diferenciar)
		btn_minus = ctk.CTkButton(
			master=frame_cant,
			text="-1",
			fg_color="#d35400", # Naranja oscuro
			text_color="#ffffff",
			border_color="#e67e22",
			hover_color="#e67e22",
			border_width=style.get("border_width", 2),
			corner_radius=corner_radius,
			height=chip_height,
			width=100,
			font=chip_font,
			cursor="hand2"
		)
		btn_minus.pack(side=tk.LEFT, padx=12)
		btn_minus.bind("<Button-1>", lambda e, b=btn_minus: self._on_cantidad_btn(b))
		setattr(btn_minus, "_incremento", -1)
		self._btns_cantidad.append(btn_minus)

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
				width=100,
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

		# Botón ORIGEN
		self.btn_origen = ctk.CTkButton(
			master=frame_otro,
			text="ORIGEN",
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
		self.btn_origen.pack(pady=(8, 0))
		self.btn_origen.bind("<Button-1>", lambda e: self._on_origen())

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
		"""Incrementar/Decrementar la cantidad según el botón pulsado, respetando el stock disponible."""
		incremento = getattr(btn, "_incremento", 0)
		nueva_cantidad = self.cantidad + incremento
		
		# Validar mínimo 0
		if nueva_cantidad < 0:
			nueva_cantidad = 0
			
		if incremento > 0 and self.stock_disponible > 0 and nueva_cantidad > self.stock_disponible:
			from kool_tpv.utils.widgets.notificaciones.toast_widget import ToastWidget
			ToastWidget.show(self.frame, f"Stock insuficiente (máx {self.stock_disponible} uds)", tipo="error")
			return
			
		self.cantidad = nueva_cantidad
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

	def _crear_chips_extras(self):
		"""Crear chips dinámicos para los extras configurados."""
		extras = self.extras_service.get_todos(solo_activos=True)
		if not extras:
			return

		frame_extras = ctk.CTkFrame(self.frame, fg_color=self._bg)
		frame_extras.pack(pady=(10, 10))

		style = get_chip_style(self._chip_cfg, "default")
		font_key = self._chip_cfg.get("font_key", "label")
		font_family = get_font(self.config, font_key)
		chip_font = (font_family[0], style.get("font_size", 14), font_family[2])
		corner_radius = self._chip_cfg.get("corner_radius", 18) # Más redondo para chips de extra
		chip_height = self._chip_cfg.get("height", 40)

		for extra in extras:
			btn = ctk.CTkButton(
				master=frame_extras,
				text=extra.nombre.upper(),
				fg_color=style.get("bg", "#1a1a2e"),
				text_color=style.get("text", "#e0e0e0"),
				border_color=style.get("border", "#552583"),
				hover_color=style.get("hover", "#C77BFF"),
				border_width=style.get("border_width", 2),
				corner_radius=corner_radius,
				height=chip_height,
				width=0, # Ajuste automático al texto
				font=chip_font,
				cursor="hand2"
			)
			btn.pack(side=tk.LEFT, padx=6)
			btn.bind("<Button-1>", lambda e, ex=extra: self._on_extra_click(ex))
			setattr(btn, "_extra_obj", extra)
			self._extra_btns[extra.id] = btn

	def _on_extra_click(self, extra):
		"""Manejar el click en un chip de extra (selección única/deselección)."""
		# Si pulsamos el mismo que ya está seleccionado -> deseleccionar
		if self.extra_seleccionado and self.extra_seleccionado.id == extra.id:
			self.extra_seleccionado = None
		else:
			self.extra_seleccionado = extra

		self._actualizar_estilo_extras()

	def _actualizar_estilo_extras(self):
		"""Actualizar visualmente qué chip de extra está seleccionado."""
		selected_style = get_chip_style(self._chip_cfg, "selected")
		default_style = get_chip_style(self._chip_cfg, "default")
		font_key = self._chip_cfg.get("font_key", "label")
		font_family = get_font(self.config, font_key)

		for extra_id, btn in self._extra_btns.items():
			is_selected = (self.extra_seleccionado and self.extra_seleccionado.id == extra_id)
			style = selected_style if is_selected else default_style
			
			btn.configure(
				fg_color=style.get("bg"),
				text_color=style.get("text"),
				border_color=style.get("border"),
				hover_color=style.get("hover"),
				border_width=style.get("border_width", 2),
				font=(font_family[0], style.get("font_size", 14), font_family[2])
			)

	def _on_siguiente(self):
		"""Manejador del botón SIGUIENTE."""
		logger = logging.getLogger(__name__)
		logger.info(f"_on_siguiente llamado. cantidad={self.cantidad}, on_siguiente={self.on_siguiente}")
		if self.cantidad < 1:
			logger.warning("SIGUIENTE ignorado: cantidad < 1")
			return
		if self.on_siguiente:
			try:
				from kool_tpv.base_datos.money_adapter import read_from_db
				extra_coste = float(read_from_db(self.extra_seleccionado.coste)) if self.extra_seleccionado else 0.0
				
				result = CantidadSeleccion(
					cantidad=self.cantidad,
					produccion_mixta=(self.extra_seleccionado.nombre.upper() == "MIXTA") if self.extra_seleccionado else False,
					extra_id=self.extra_seleccionado.id if self.extra_seleccionado else None,
					extra_coste=extra_coste,
					extra_nombre=self.extra_seleccionado.nombre if self.extra_seleccionado else None
				)
				logger.info(f"Llamando on_siguiente con result={result}")
				self.on_siguiente(result)
			except Exception as e:
				logger.exception(f"Error en _on_siguiente: {e}")

	def _on_anadir(self):
		"""Manejador del botón OTRO PRODUCTO."""
		if self.cantidad < 1:
			return
		if self.on_anadir:
			from kool_tpv.base_datos.money_adapter import read_from_db
			extra_coste = float(read_from_db(self.extra_seleccionado.coste)) if self.extra_seleccionado else 0.0
			
			result = CantidadSeleccion(
				cantidad=self.cantidad,
				produccion_mixta=(self.extra_seleccionado.nombre.upper() == "MIXTA") if self.extra_seleccionado else False,
				extra_id=self.extra_seleccionado.id if self.extra_seleccionado else None,
				extra_coste=extra_coste,
				extra_nombre=self.extra_seleccionado.nombre if self.extra_seleccionado else None
			)
			self.on_anadir(result)

	def _on_origen(self):
		"""Manejador del botón ORIGEN."""
		if self.cantidad < 1:
			return
		if self.on_origen:
			from kool_tpv.base_datos.money_adapter import read_from_db
			extra_coste = float(read_from_db(self.extra_seleccionado.coste)) if self.extra_seleccionado else 0.0
			
			result = CantidadSeleccion(
				cantidad=self.cantidad,
				produccion_mixta=(self.extra_seleccionado.nombre.upper() == "MIXTA") if self.extra_seleccionado else False,
				extra_id=self.extra_seleccionado.id if self.extra_seleccionado else None,
				extra_coste=extra_coste,
				extra_nombre=self.extra_seleccionado.nombre if self.extra_seleccionado else None
			)
			self.on_origen(result)


	def _on_volver(self):
		"""Manejador del botón VOLVER."""
		if self.on_volver:
			self.on_volver()

	def obtener_seleccion(self) -> CantidadSeleccion:
		"""Obtener la selección de cantidad."""
		from kool_tpv.base_datos.money_adapter import read_from_db
		extra_coste = float(read_from_db(self.extra_seleccionado.coste)) if self.extra_seleccionado else 0.0
		return CantidadSeleccion(
			cantidad=self.cantidad,
			produccion_mixta=(self.extra_seleccionado.nombre.upper() == "MIXTA") if self.extra_seleccionado else False,
			extra_id=self.extra_seleccionado.id if self.extra_seleccionado else None,
			extra_coste=extra_coste,
			extra_nombre=self.extra_seleccionado.nombre if self.extra_seleccionado else None
		)

	def destruir(self):
		"""Destruir la subvista y limpiar recursos."""
		self.clear_keyboard_navigation()
		self.frame.destroy()
