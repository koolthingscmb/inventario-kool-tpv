"""Subvista de autenticación de cajero para producción.

Muestra chips de cajeros y solicita password al seleccionar uno.
Si la autenticación es correcta, llama a `on_success(usuario_id, nombre)`.
Reusa AuthService y show_password_dialog del proyecto.
"""
import logging
from typing import Callable, Optional

import customtkinter as ctk

from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.base_datos.usuario_service import UsuarioService
from kool_tpv.utils.auth_service import AuthService
from kool_tpv.utils.dialogs.helpers import show_password_dialog, show_warning
from kool_tpv.utils.keyboard_nav_mixin import KeyboardNavigableMixin
from kool_tpv.modulos.produccion.ui.subvistas.config_helper import (
	cargar_config_produccion, get_font, get_chip_config, get_chip_style, get_nav_button_config, get_nav_button_style
)
from kool_tpv.utils.factories.button_factory import ButtonFactory


class CajeroAuthView(ctk.CTkFrame, KeyboardNavigableMixin):
	"""Vista de selección y autenticación de cajero para producción.

	Args:
		parent: Widget padre.
		db: Instancia de Database.
		on_success: Callback(usuario_id: int, nombre: str) cuando auth OK.
		on_cancel: Callback cuando se cancela (botón VOLVER).
	"""

	def __init__(self, parent, db: Database,
	             on_success: Optional[Callable[[int, str], None]] = None,
	             on_cancel: Optional[Callable] = None):
		ctk.CTkFrame.__init__(self, parent, fg_color=self._get_bg())
		KeyboardNavigableMixin.__init_keyboard_mixin__(self)

		self.db = db
		self.on_success = on_success
		self.on_cancel = on_cancel

		self._usuario_service = UsuarioService(db)
		self._auth_service = AuthService(db)

		self.config = cargar_config_produccion()
		self._colors = self.config.get("colors", {})
		self._bg = self._colors.get("background", "#2c3e50")
		self._text = self._colors.get("text", "#ecf0f1")
		self._text_sec = self._colors.get("text_secondary", "#95a5a6")
		self._chip_cfg = get_chip_config(self.config, "producto")

		self._chip_buttons = []
		self._selected_chip: Optional[ctk.CTkButton] = None

		self.configure(fg_color=self._bg)
		self.pack(fill="both", expand=True)

		self._crear_titulo()
		self._crear_chips()
		self._crear_botones_navegacion()

		self._navigable_buttons = [
			(btn, lambda u=getattr(btn, '_usr_data', None): self._on_nav_enter_callback(u))
			for btn in self._chip_buttons
		]
		self._navigable_buttons.append((self.btn_volver, self._on_volver_handler))
		if self._navigable_buttons:
			self._setup_keyboard_navigation()

		if self._chip_buttons:
			self.after(100, lambda: self._focus_nav_widget(0))

	@staticmethod
	def _get_bg():
		try:
			cfg = cargar_config_produccion()
			return cfg.get("colors", {}).get("background", "#2c3e50")
		except Exception:
			return "#2c3e50"

	def _crear_titulo(self):
		ctk.CTkLabel(
			self,
			text="SELECCIONA CAJERO",
			font=get_font(self.config, "title"),
			text_color=self._text
		).pack(pady=20)

	def _crear_chips(self):
		self.chips_frame = ctk.CTkScrollableFrame(self, fg_color=self._bg, label_text="")
		self.chips_frame.pack(expand=True, fill="both", padx=40, pady=20)

		usuarios = self._usuario_service.get_all_usuarios()
		if not usuarios:
			ctk.CTkLabel(
				self.chips_frame,
				text="No hay cajeros configurados",
				font=get_font(self.config, "label"),
				text_color=self._text_sec
			).pack(pady=40)
			return

		cols = self._chip_cfg.get("columns", 3)
		padx = self._chip_cfg.get("padx", 8)
		pady = self._chip_cfg.get("pady", 8)
		chip_height = self._chip_cfg.get("height", 48)
		corner_radius = self._chip_cfg.get("corner_radius", 8)
		font_key = self._chip_cfg.get("font_key", "label")
		default_style = get_chip_style(self._chip_cfg, "default")
		font_family = get_font(self.config, font_key)
		chip_font = (font_family[0], default_style.get("font_size", 14), font_family[2])

		for idx, usr in enumerate(usuarios):
			nombre = usr.get("nombre", "")
			uid = usr.get("id")
			btn = ctk.CTkButton(
				master=self.chips_frame,
				text=nombre,
				fg_color=default_style.get("bg", "#1a1a2e"),
				text_color=default_style.get("text", "#e0e0e0"),
				border_color=default_style.get("border", "#C77BFF"),
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
			btn.bind("<Button-1>", lambda e, b=btn, u=usr: self._on_chip_click(b, u))
			setattr(btn, "_usr_data", usr)
			self._chip_buttons.append(btn)

		for i in range(cols):
			self.chips_frame.columnconfigure(i, weight=1)
		n_rows = (len(usuarios) + cols - 1) // cols
		for i in range(n_rows):
			self.chips_frame.rowconfigure(i, weight=1)

	def _on_chip_click(self, btn: ctk.CTkButton, usr: dict):
		self._select_chip(btn, usr)

	def _select_chip(self, btn: ctk.CTkButton, usr: dict):
		if self._selected_chip is not None:
			try:
				self._apply_chip_style(self._selected_chip, "default")
			except Exception:
				pass
		self._selected_chip = btn
		try:
			self._apply_chip_style(btn, "selected")
		except Exception:
			pass
		self._intentar_auth(usr)

	def _apply_chip_style(self, btn: ctk.CTkButton, state: str):
		style = get_chip_style(self._chip_cfg, state)
		font_key = self._chip_cfg.get("font_key", "label")
		font_family = get_font(self.config, font_key)
		btn.configure(
			fg_color=style.get("bg", "#1a1a2e"),
			text_color=style.get("text", "#e0e0e0"),
			border_color=style.get("border", "#C77BFF"),
			font=(font_family[0], style.get("font_size", 14), font_family[2])
		)

	def _intentar_auth(self, usr: dict):
		uid = usr.get("id")
		nombre = usr.get("nombre", "")
		if not uid:
			return

		parent = self.winfo_toplevel()
		password = show_password_dialog(
			parent,
			titulo="Autenticar Cajero",
			mensaje=f"Introduce la contraseña de {nombre}:"
		)

		if not password:
			self._deselect()
			return

		valid = self._auth_service.validate_user_password(uid, password)
		if valid:
			logging.info(f"Cajero autenticado para producción: {nombre}")
			if self.on_success:
				self.on_success(uid, nombre)
		else:
			show_warning(
				parent,
				"CÓDIGO NO VÁLIDO",
				"La contraseña introducida es incorrecta.\nInténtalo de nuevo.",
				callback=lambda _: self._intentar_auth(usr)
			)

	def _deselect(self):
		if self._selected_chip is not None:
			try:
				self._apply_chip_style(self._selected_chip, "default")
			except Exception:
				pass
		self._selected_chip = None

	def _crear_botones_navegacion(self):
		"""Crear los botones de navegación inferior (solo VOLVER en auth)."""
		frame_nav = ctk.CTkFrame(self, fg_color=self._bg)
		frame_nav.pack(fill="x", padx=40, pady=20)

		# Botón VOLVER
		nav_volver = get_nav_button_config(self.config, "volver")
		self.btn_volver = ButtonFactory.create_button(
			parent=frame_nav,
			text=nav_volver.get("text", "VOLVER"),
			command=self._on_volver_handler,
			width=nav_volver.get("width", 15) * 10,
			height=nav_volver.get("height", 2) * 20,
			font=get_font(self.config, nav_volver.get("font_key", "button")),
			style_key="action_confirm",
			module="produccion",
			palette_key="primary",
			cursor="hand2"
		)
		self.btn_volver.pack(side="left", padx=10)

	def _on_volver_handler(self):
		"""Manejador del botón VOLVER."""
		if self.on_cancel:
			self.on_cancel()

	def _on_nav_enter_callback(self, usr: dict):
		"""Callback de Enter en navegación: seleccionar chip y auth."""
		if usr:
			btn = None
			for b in self._chip_buttons:
				if getattr(b, '_usr_data', None) == usr:
					btn = b
					break
			if btn:
				self._select_chip(btn, usr)

	def destruir(self):
		try:
			from kool_tpv.utils.keyboard_manager import KeyboardManager
			KeyboardManager.get_instance().set_capture_enabled(True)
		except Exception:
			pass
		self.clear_keyboard_navigation()
		self.destroy()
