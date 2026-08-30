"""Helpers de configuración para subvistas de producción.

Funciones utilitarias para extraer configuración de chips y botones de
navegación desde `config_produccion.json`, evitando hardcoded en las vistas.
"""
import json
import os
from typing import Optional
from kool_tpv.paths import get_resource_path

_CONFIG_PATH = get_resource_path("kool_tpv", "config", "config_produccion.json")


def cargar_config_produccion() -> dict:
	"""Cargar la configuración de producción desde JSON."""
	try:
		with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
			return json.load(f)
	except (FileNotFoundError, json.JSONDecodeError):
		return {}


def get_font(config: dict, key: str) -> tuple:
	"""Obtener una fuente desde la configuración.

	Args:
		config: Dict de configuración de producción.
		key: Clave de la fuente (ej. "title", "label", "button").

	Returns:
		Tupla (family, size, weight) para tkinter/customtkinter.
	"""
	f = config.get("fonts", {}).get(key, {})
	return (f.get("family", "Courier New"), f.get("size", 16), f.get("weight", "normal"))


def get_chip_config(config: dict, subvista: str) -> dict:
	"""Obtener la configuración de chips para una subvista.

	Args:
		config: Dict de configuración de producción.
		subvista: Nombre de la subvista ("producto", "talla", "color", "diseno").

	Returns:
		Dict con keys: columns, padx, pady, height, corner_radius,
		font_key, default, selected.
	"""
	chips = config.get("chips", {})
	return chips.get(subvista, {
		"columns": 3,
		"padx": 10,
		"pady": 10,
		"height": 48,
		"corner_radius": 8,
		"font_key": "label",
		"default": {},
		"selected": {},
	})


def get_chip_style(chip_cfg: dict, state: str = "default") -> dict:
	"""Obtener el estilo de color directo para un chip.

	Args:
		chip_cfg: Dict de configuración del chip (de get_chip_config).
		state: "default" o "selected".

	Returns:
		Dict con keys: bg, text, border, hover, border_width, font_size.
	"""
	return chip_cfg.get(state, {})


def get_nav_button_config(config: dict, key: str) -> dict:
	"""Obtener la configuración de un botón de navegación.

	Args:
		config: Dict de configuración de producción.
		key: Clave del botón ("volver", "siguiente", "anadir", "confirmar").

	Returns:
		Dict con keys: text, width, height, font_key, bd, style_key.
	"""
	nav = config.get("nav_buttons", {})
	defaults = {
		"text": key.upper(),
		"width": 15,
		"height": 2,
		"font_key": "button",
		"bd": 0,
		"style_key": key,
	}
	return nav.get(key, defaults)


def get_nav_button_style(config: dict, key: str) -> dict:
	"""Obtener el estilo de color de un botón de navegación.

	Args:
		config: Dict de configuración de producción.
		key: Clave del estilo ("volver", "siguiente", etc.).

	Returns:
		Dict con keys: bg, hover, text, border.
	"""
	buttons = config.get("colors", {}).get("buttons", {})
	return buttons.get(key, {})
