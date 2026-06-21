"""Subvista de selección de diseño.

Contiene la clase `NuevaProduccionDisenoView` que muestra un campo de búsqueda
y una lista de diseños cargados desde la base de datos (tabla `produccion_disenos`).
"""
import tkinter as tk
from typing import Callable, List, Optional

import customtkinter as ctk

from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.produccion.models.produccion_diseno_model import ProduccionDiseno
from kool_tpv.modulos.produccion.services.produccion_disenos_service import ProduccionDisenosService
from kool_tpv.modulos.produccion.ui.subvistas.config_helper import cargar_config_produccion, get_font, get_chip_config, get_chip_style, get_nav_button_config, get_nav_button_style


class NuevaProduccionDisenoView:
	"""Subvista para seleccionar un diseño.

	Args:
		parent: Widget padre donde se mostrará la subvista.
		db: Instancia de `Database` ya conectada.
		on_siguiente: Callback cuando se pulsa SIGUIENTE (recibe ProduccionDiseno).
		on_volver: Callback cuando se pulsa VOLVER.
	"""

	def __init__(self, parent, db: Database,
	             on_siguiente: Optional[Callable[[ProduccionDiseno], None]] = None,
	             on_volver: Optional[Callable] = None):
		self.parent = parent
		self.db = db
		self.on_siguiente = on_siguiente
		self.on_volver = on_volver
		self.diseno_seleccionado: Optional[ProduccionDiseno] = None
		self._chip_buttons: List[ctk.CTkButton] = []
		self._selected_chip: Optional[ctk.CTkButton] = None
		self._focused_index: int = -1

		# Servicio para cargar diseños desde BD
		self._service = ProduccionDisenosService(db)

		# Cargar configuración
		self.config = cargar_config_produccion()
		self._colors = self.config.get("colors", {})
		self._bg = self._colors.get("background", "#2c3e50")
		self._text = self._colors.get("text", "#ecf0f1")
		self._text_sec = self._colors.get("text_secondary", "#95a5a6")
		self._focus_border = self._colors.get("focus_border", "#FFD700")
		self._chip_cfg = get_chip_config(self.config, "diseno")

		# Frame principal
		self.frame = tk.Frame(parent, bg=self._bg)
		self.frame.pack(fill=tk.BOTH, expand=True)

		# Título + búsqueda + lista
		self._crear_titulo()
		self._crear_busqueda()
		self._crear_lista_disenos()

		# Botones de navegación
		self._crear_botones_navegacion()

		# Navegación por teclado
		self._setup_keyboard_nav()

		# Cargar diseños iniciales
		self._cargar_disenos("")

	def _get_font(self, key: str) -> tuple:
		"""Obtener una fuente desde la configuración."""
		return get_font(self.config, key)

	def _crear_titulo(self):
		"""Crear el título de la subvista."""
		titulo = ctk.CTkLabel(
			self.frame,
			text="SELECCIONA DISEÑO",
			font=self._get_font("title"),
			text_color=self._text,
			fg_color=self._bg
		)
		titulo.pack(pady=(20, 10))

	def _crear_busqueda(self):
		"""Crear el campo de búsqueda."""
		frame_search = ctk.CTkFrame(self.frame, fg_color=self._bg)
		frame_search.pack(fill="x", padx=40, pady=(0, 10))

		self.entry_busqueda = ctk.CTkEntry(
			frame_search,
			placeholder_text="Buscar por código, nombre o colección...",
			font=self._get_font("entry"),
			height=40
		)
		self.entry_busqueda.pack(fill="x", side="left", expand=True)
		self.entry_busqueda.bind("<KeyRelease>", self._on_buscar_change)
		self.entry_busqueda.bind("<Return>", self._on_buscar_enter)
		self.entry_busqueda.bind("<KP_Enter>", self._on_buscar_enter)

		btn_limpiar = ctk.CTkButton(
			master=frame_search,
			text="LIMPIAR",
			command=self._limpiar_busqueda,
			width=80,
			height=40,
			cursor="hand2"
		)
		btn_limpiar.pack(side="right", padx=(10, 0))

	def _crear_lista_disenos(self):
		"""Crear el frame scrollable para la lista de diseños."""
		self.lista_frame = ctk.CTkScrollableFrame(
			self.frame,
			fg_color=self._bg,
			label_text=""
		)
		self.lista_frame.pack(expand=True, fill="both", padx=40, pady=(0, 10))

	def _cargar_disenos(self, filtro: str):
		"""Cargar diseños desde BD según el filtro de búsqueda."""
		# Limpiar lista actual
		for w in list(self.lista_frame.winfo_children()):
			w.destroy()
		self._chip_buttons.clear()
		self._selected_chip = None
		self._focused_index = -1

		# Buscar diseños
		if filtro.strip():
			disenos = self._service.buscar(filtro.strip())
		else:
			disenos = self._service.obtener_activos()

		if not disenos:
			lbl_vacio = ctk.CTkLabel(
				self.lista_frame,
				text="No se encontraron diseños",
				font=self._get_font("label"),
				text_color=self._text_sec
			)
			lbl_vacio.pack(pady=40)
			return

		# Crear un chip por diseño (lista vertical)
		cols = self._chip_cfg.get("columns", 2)
		padx = self._chip_cfg.get("padx", 6)
		pady = self._chip_cfg.get("pady", 4)
		chip_height = self._chip_cfg.get("height", 40)
		corner_radius = self._chip_cfg.get("corner_radius", 8)
		font_key = self._chip_cfg.get("font_key", "label")
		default_style = get_chip_style(self._chip_cfg, "default")
		font_family = get_font(self.config, font_key)
		chip_font = (font_family[0], default_style.get("font_size", 14), font_family[2])
		for idx, diseno in enumerate(disenos):
			texto = f"{diseno.nombre}  [{diseno.coleccion}]"
			if diseno.variante:
				texto += f"  ({diseno.variante})"

			btn = ctk.CTkButton(
				master=self.lista_frame,
				text=texto,
				fg_color=default_style.get("bg", "#1a1a2e"),
				text_color=default_style.get("text", "#e0e0e0"),
				border_color=default_style.get("border", "#552583"),
				hover_color=default_style.get("hover", "#C77BFF"),
				border_width=default_style.get("border_width", 1),
				corner_radius=corner_radius,
				height=chip_height,
				font=chip_font,
				cursor="hand2",
				anchor="w"
			)
			row = idx // cols
			col = idx % cols
			btn.grid(row=row, column=col, padx=padx, pady=pady, sticky="ew")
			btn.bind("<Button-1>", lambda e, b=btn, d=diseno: self._on_chip_click(b, d))
			setattr(btn, "_diseno_data", diseno)
			self._chip_buttons.append(btn)

		# Pesos del grid
		for i in range(cols):
			self.lista_frame.columnconfigure(i, weight=1)
		n_rows = (len(disenos) + cols - 1) // cols
		for i in range(n_rows):
			self.lista_frame.rowconfigure(i, weight=0)

	def _on_buscar_change(self, event):
		"""Manejador del cambio de texto en la búsqueda."""
		filtro = self.entry_busqueda.get()
		self._cargar_disenos(filtro)

	def _on_buscar_enter(self, event):
		"""Enter en la búsqueda: si hay resultados, enfocar el primero."""
		if self._chip_buttons:
			self._focus_chip(0)
		return "break"

	def _limpiar_busqueda(self):
		"""Limpiar el campo de búsqueda y recargar todos."""
		self.entry_busqueda.delete(0, "end")
		self._cargar_disenos("")
		self.entry_busqueda.focus_set()

	def _on_chip_click(self, btn: ctk.CTkButton, diseno: ProduccionDiseno):
		"""Manejador del clic en un chip de diseño."""
		self._select_chip(btn, diseno)

	def _select_chip(self, btn: ctk.CTkButton, diseno: ProduccionDiseno):
		"""Seleccionar un chip visualmente y guardar la selección."""
		if self._selected_chip is not None:
			try:
				self._apply_chip_style(self._selected_chip, "default")
			except Exception:
				pass

		self._selected_chip = btn
		self.diseno_seleccionado = diseno
		try:
			self._apply_chip_style(btn, "selected")
		except Exception:
			pass

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

	# --- Navegación por teclado ---

	def _setup_keyboard_nav(self):
		"""Configurar bindings de navegación por teclado."""
		toplevel = self.frame.winfo_toplevel()
		toplevel.bind("<Tab>", self._on_tab_next)
		toplevel.bind("<Shift-Tab>", self._on_tab_prev)
		toplevel.bind("<Return>", self._on_enter)
		toplevel.bind("<KP_Enter>", self._on_enter)
		toplevel.bind("<Down>", self._on_arrow_down)
		toplevel.bind("<Up>", self._on_arrow_up)

		self.frame.bind("<Destroy>", self._on_destroy)

	def _on_destroy(self, event=None):
		"""Limpiar bindings al destruir."""
		try:
			toplevel = self.frame.winfo_toplevel()
			for key in ("<Tab>", "<Shift-Tab>", "<Return>", "<KP_Enter>",
			            "<Down>", "<Up>"):
				toplevel.unbind(key)
		except Exception:
			pass

	def _focus_chip(self, index: int):
		"""Aplicar foco visual a un chip por índice."""
		if not self._chip_buttons:
			return
		if index < 0:
			index = len(self._chip_buttons) - 1
		elif index >= len(self._chip_buttons):
			index = 0

		self._focused_index = index
		self._chip_buttons[index].focus_set()

	def _on_tab_next(self, event):
		if not self._chip_buttons:
			return "break"
		next_idx = self._focused_index + 1 if self._focused_index >= 0 else 0
		self._focus_chip(next_idx)
		return "break"

	def _on_tab_prev(self, event):
		if not self._chip_buttons:
			return "break"
		prev_idx = self._focused_index - 1 if self._focused_index >= 0 else len(self._chip_buttons) - 1
		self._focus_chip(prev_idx)
		return "break"

	def _on_enter(self, event):
		if 0 <= self._focused_index < len(self._chip_buttons):
			btn = self._chip_buttons[self._focused_index]
			diseno = getattr(btn, "_diseno_data", None)
			if diseno is not None:
				self._select_chip(btn, diseno)
		return "break"

	def _on_arrow_up(self, event):
		if self._chip_buttons:
			cols = self._chip_cfg.get("columns", 2)
			self._focus_chip(self._focused_index - cols if self._focused_index >= 0 else 0)
		return "break"

	def _on_arrow_down(self, event):
		if self._chip_buttons:
			cols = self._chip_cfg.get("columns", 2)
			self._focus_chip(self._focused_index + cols if self._focused_index >= 0 else 0)
		return "break"

	# --- Callbacks de navegación ---

	def _on_siguiente(self):
		"""Manejador del botón SIGUIENTE."""
		if self.diseno_seleccionado and self.on_siguiente:
			self.on_siguiente(self.diseno_seleccionado)

	def _on_volver(self):
		"""Manejador del botón VOLVER."""
		if self.on_volver:
			self.on_volver()

	def obtener_seleccion(self) -> Optional[ProduccionDiseno]:
		"""Obtener el diseño seleccionado.

		Returns:
			Objeto ProduccionDiseno o None.
		"""
		return self.diseno_seleccionado

	def destruir(self):
		"""Destruir la subvista y limpiar recursos."""
		self._on_destroy()
		self.frame.destroy()
