"""Widget selector de tipo de producto fabricable.

Contiene la clase `ProductoSelectorWidget` que muestra los tipos de producto
como chips cargados desde la base de datos (tabla `produccion_tipos`).

Soporta:
- Clic táctil (dedo) en cada chip.
- Navegación con Tab/Shift+Tab y Enter via KeyboardNavigableMixin.
- Navegación con flechas Up/Down via KeyboardManager.
"""
from typing import Callable, List, Optional

import customtkinter as ctk

from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.produccion.models.produccion_tipos_model import ProduccionTipo
from kool_tpv.modulos.produccion.services.produccion_tipos_service import ProduccionTiposService
from kool_tpv.modulos.produccion.services.produccion_menu_service import ProduccionMenuService
from kool_tpv.modulos.produccion.ui.subvistas.config_helper import cargar_config_produccion, get_font, get_chip_config, get_chip_style
from kool_tpv.utils.keyboard_nav_mixin import KeyboardNavigableMixin


class ProductoSelectorWidget(KeyboardNavigableMixin):
	"""Widget para seleccionar el tipo de producto fabricable.

	Usa KeyboardNavigableMixin para Tab/Shift+Tab/Enter (mismo patrón que el TPV).

	Args:
		parent: Widget padre donde se mostrará el selector.
		db: Instancia de `Database` ya conectada.
		on_seleccion: Callback cuando se selecciona un tipo (recibe ProduccionTipo).
		on_advance: Callback cuando se pulsa Enter con un chip ya seleccionado.
		keyboard_mgr: Instancia de KeyboardManager para flechas.
		titulo: Título opcional del widget.
	"""

	def __init__(self, parent, db: Database,
	             on_seleccion: Optional[Callable[[ProduccionTipo], None]] = None,
	             on_advance: Optional[Callable] = None,
	             keyboard_mgr=None,
	             titulo: str = "SELECCIONA PRODUCTO"):
		KeyboardNavigableMixin.__init_keyboard_mixin__(self)
		self.parent = parent
		self.db = db
		self.on_seleccion = on_seleccion
		self.on_advance = on_advance
		self.keyboard_mgr = keyboard_mgr
		self.titulo = titulo
		self.tipo_seleccionado: Optional[ProduccionTipo] = None
		self._chip_buttons: List[ctk.CTkButton] = []
		self._selected_chip: Optional[ctk.CTkButton] = None

		# Servicio para cargar menú desde BD
		self._menu_service = ProduccionMenuService(db)

		# Cargar configuración
		self.config = cargar_config_produccion()
		self._colors = self.config.get("colors", {})
		self._bg = self._colors.get("background", "#2c3e50")
		self._text = self._colors.get("text", "#ecf0f1")
		self._text_sec = self._colors.get("text_secondary", "#95a5a6")
		self._chip_cfg = get_chip_config(self.config, "producto")

		# Frame principal (debe ser CTkFrame para que winfo_toplevel() funcione)
		self.frame = ctk.CTkFrame(parent, fg_color=self._bg)
		self.frame.pack(fill="both", expand=True)

		# Título
		self._crear_titulo()

		# Chips de tipos
		self._crear_chips_tipos()

		# Configurar navegación con KeyboardNavigableMixin (Tab/Shift+Tab/Enter)
		self._navigable_buttons = [
			(btn, lambda b=btn, t=getattr(btn, '_tipo_data', None): self._on_nav_enter_callback(b, t))
			for btn in self._chip_buttons
		]
		# Usar self.frame como widget para toplevel (ProductoSelectorWidget no es widget)
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

		# Auto-focus primer chip
		if self._chip_buttons:
			self.frame.after(100, lambda: self._focus_nav_widget(0))

		# Registrarse en KeyboardManager (para flechas Up/Down)
		if self.keyboard_mgr:
			self.keyboard_mgr.set_active_list(self)

	def _crear_titulo(self):
		"""Crear el título del widget."""
		titulo = ctk.CTkLabel(
			self.frame,
			text=self.titulo,
			font=get_font(self.config, "title"),
			text_color=self._text,
			fg_color=self._bg
		)
		titulo.pack(pady=20)

	def _crear_chips_tipos(self):
		"""Crear los chips de tipos de producto cargados desde el menú de producción."""
		# Frame scrollable para los chips
		self.chips_frame = ctk.CTkScrollableFrame(
			self.frame,
			fg_color=self._bg,
			label_text=""
		)
		self.chips_frame.pack(expand=True, fill="both", padx=40, pady=20)

		# Cargar elementos del menú desde BD
		menu_items = self._menu_service.obtener_menu_activos()

		if not menu_items:
			lbl_vacio = ctk.CTkLabel(
				self.chips_frame,
				text="No hay opciones de producción configuradas",
				font=get_font(self.config, "label"),
				text_color=self._text_sec
			)
			lbl_vacio.pack(pady=40)
			return

		# Crear chips en grid
		cols = self._chip_cfg.get("columns", 4)
		padx = self._chip_cfg.get("padx", 8)
		pady = self._chip_cfg.get("pady", 8)
		chip_height = self._chip_cfg.get("height", 48)
		corner_radius = self._chip_cfg.get("corner_radius", 8)
		font_key = self._chip_cfg.get("font_key", "label")
		default_style = get_chip_style(self._chip_cfg, "default")
		font_family = get_font(self.config, font_key)
		chip_font = (font_family[0], default_style.get("font_size", 14), font_family[2])
		
		for idx, item in enumerate(menu_items):
			# Por ahora, mapeamos el item del menú a un ProduccionTipo para mantener la compatibilidad del flujo
			tipo = self._menu_service.obtener_tipo_asociado(item)
			
			btn = ctk.CTkButton(
				master=self.chips_frame,
				text=item.nombre,
				fg_color=default_style.get("bg", "#1a1a2e"),
				text_color=default_style.get("text", "#e0e0e0"),
				border_color=default_style.get("border", "#552583"),
				hover_color=default_style.get("hover", "#C77BFF"),
				border_width=default_style.get("border_width", 1),
				corner_radius=corner_radius,
				height=chip_height,
				font=chip_font,
				cursor="hand2"
			)

			row = idx // cols
			col = idx % cols
			btn.grid(row=row, column=col, padx=padx, pady=pady, sticky="nsew")
			btn.bind("<Button-1>", lambda e, b=btn, t=tipo: self._on_chip_click(b, t))
			setattr(btn, "_tipo_data", tipo)
			self._chip_buttons.append(btn)

		# Configurar pesos del grid
		for i in range(cols):
			self.chips_frame.columnconfigure(i, weight=1)
		n_rows = (len(menu_items) + cols - 1) // cols
		for i in range(n_rows):
			self.chips_frame.rowconfigure(i, weight=1)

	def _on_chip_click(self, btn: ctk.CTkButton, tipo: ProduccionTipo):
		"""Manejador del clic en un chip de tipo."""
		self._select_chip(btn, tipo)

	def _select_chip(self, btn: ctk.CTkButton, tipo: ProduccionTipo):
		"""Seleccionar un chip visualmente y guardar la selección."""
		# Deseleccionar el anterior
		if self._selected_chip is not None:
			try:
				self._apply_chip_style(self._selected_chip, "default")
			except Exception:
				pass

		# Seleccionar el nuevo
		self._selected_chip = btn
		self.tipo_seleccionado = tipo
		try:
			self._apply_chip_style(btn, "selected")
		except Exception:
			pass

		# Notificar selección
		if self.on_seleccion:
			self.on_seleccion(tipo)

	def _apply_chip_style(self, btn: ctk.CTkButton, state: str):
		"""Aplicar estilo de color directo desde config al chip."""
		style = get_chip_style(self._chip_cfg, state)
		font_key = self._chip_cfg.get("font_key", "label")
		font_family = get_font(self.config, font_key)
		btn.configure(
			fg_color=style.get("bg", "#1a1a2e"),
			text_color=style.get("text", "#e0e0e0"),
			border_color=style.get("border", "#552583"),
			hover_color=style.get("hover", "#C77BFF"),
			border_width=style.get("border_width", 1),
			font=(font_family[0], style.get("font_size", 14), font_family[2])
		)

	# --- Callback para Enter desde KeyboardNavigableMixin ---

	def _on_nav_enter_callback(self, btn: ctk.CTkButton, tipo: Optional[ProduccionTipo]):
		"""Manejar Enter desde el mixin: seleccionar o avanzar."""
		if self._selected_chip is not None and self._selected_chip == btn:
			# Ya estaba seleccionado → avanzar
			if self.on_advance:
				self.on_advance()
		elif tipo is not None:
			# Seleccionar chip
			self._select_chip(btn, tipo)

	# --- Protocolo Navigable para KeyboardManager (flechas) ---

	def select_next(self) -> bool:
		"""Flecha abajo → siguiente chip."""
		if not self._chip_buttons:
			return False
		next_idx = self._nav_focused_index + 1 if self._nav_focused_index >= 0 else 0
		if next_idx >= len(self._chip_buttons):
			next_idx = 0
		self._focus_nav_widget(next_idx)
		return True

	def select_previous(self) -> bool:
		"""Flecha arriba → chip anterior."""
		if not self._chip_buttons:
			return False
		prev_idx = self._nav_focused_index - 1 if self._nav_focused_index >= 0 else len(self._chip_buttons) - 1
		if prev_idx < 0:
			prev_idx = len(self._chip_buttons) - 1
		self._focus_nav_widget(prev_idx)
		return True

	def obtener_seleccion(self) -> Optional[ProduccionTipo]:
		"""Obtener el tipo seleccionado."""
		return self.tipo_seleccionado

	def destruir(self):
		"""Destruir el widget y limpiar recursos."""
		self.clear_keyboard_navigation()
		if self.keyboard_mgr:
			self.keyboard_mgr.clear_active_list()
		self.frame.destroy()