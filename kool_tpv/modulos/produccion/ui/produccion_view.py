"""Vista principal del módulo de Producción.

Extiende `BaseModuleView` para reutilizar la estética del sidebar,
breadcrumb y navegación por power button. Los botones del menú se
cargan desde `buttons_menu.json` (sección `produccion`).
"""
import json
import logging
from pathlib import Path
import unicodedata

from kool_tpv.modulos.produccion.services.produccion_main_service import ProduccionMainService
from kool_tpv.utils.templates.base_module_view import BaseModuleView


class ProduccionView(BaseModuleView):
	"""Vista del módulo de Producción usando `BaseModuleView`.

	Args:
		parent: Widget padre (normalmente `main_frame` de la app).
		db: Instancia de `Database` ya conectada.
		keyboard_manager: Gestor de teclado opcional.
	"""

	def __init__(self, parent, db, keyboard_manager=None):
		super().__init__(parent, config_section='produccion')
		try:
			self.keyboard_mgr = keyboard_manager
		except Exception:
			self.keyboard_mgr = None
		try:
			self._module_key = 'produccion'
			self.module_name = 'produccion'
		except Exception:
			pass
		try:
			self.actualizar_ruta('PRODUCCIÓN')
		except Exception:
			pass

		self.parent = parent
		self.db = db
		self.service = ProduccionMainService(db)

		# Rebind menu buttons to local handlers
		try:
			base = Path(__file__).resolve().parents[3]
			cfg_file = base / 'config' / 'buttons_menu.json'
			cfg = {}
			if cfg_file.exists():
				with cfg_file.open('r', encoding='utf-8') as fh:
					cfg = json.load(fh)
			menu = cfg.get('produccion', {}) if isinstance(cfg, dict) else {}
			buttons = menu.get('buttons', []) if isinstance(menu, dict) else []
		except Exception:
			logging.exception('Error leyendo buttons_menu.json en ProduccionView')
			buttons = []

		action_map = {
			'show_nuevo': self.show_nuevo,
			'show_costes': self.show_costes,
			'show_colores': self.show_colores,
			'show_stock': self.show_stock,
		}

		try:
			def _norm(s: str) -> str:
				try:
					return ''.join(ch for ch in unicodedata.normalize("NFKD", (s or '')).upper() if not unicodedata.combining(ch)).strip()
				except Exception:
					return (s or '').upper().strip()

			for b in buttons:
				lbl = (b.get('label') or b.get('text') or '')
				action = b.get('action')
				norm_lbl = _norm(lbl)
				for child in list(self._menu_frame.winfo_children()):
					try:
						txt = child.cget('text') if hasattr(child, 'cget') else None
						if txt and _norm(txt) == norm_lbl:
							if action in action_map:
								def _wrap(func):
									def _wrapped(*a, **k):
										try:
											return func(*a, **k)
										except Exception:
											logging.exception("Error al ejecutar acción %r:", getattr(func, '__name__', str(func)))
											raise
									return _wrapped
								try:
									child.configure(command=_wrap(action_map[action]))
								except Exception:
									logging.exception("Failed configuring command for %r", lbl)
							else:
								logging.warning("  Action %r not found in action_map", action)
							break
					except Exception:
						logging.exception("Error inspeccionando child en ProduccionView")
		except Exception:
			logging.exception('Error enlazando botones en ProduccionView')

		self.breadcrumb_callbacks = {
			'PRODUCCIÓN': self.show_nuevo,
		}

	def _on_power(self):
		"""Gestionar botón Power: cerrar sub-vista o indicar que se cierre el módulo."""
		try:
			if self.central_area.winfo_children():
				for widget in self.central_area.winfo_children():
					widget.destroy()
				try:
					self.actualizar_ruta('PRODUCCIÓN')
				except Exception:
					pass
				return True
			return False
		except Exception:
			logging.exception('Error en _on_power de ProduccionView')
			return False

	def show_nuevo(self):
		"""Abrir flujo de nueva producción en la zona central."""
		try:
			from kool_tpv.modulos.produccion.ui.subvistas.produccion_nuevo_flow import NuevoProduccionFlow
			try:
				for w in list(self.central_area.winfo_children()):
					w.destroy()
				flow = NuevoProduccionFlow(
					self.central_area,
					db=self.db,
					on_cerrar=self._on_flow_cerrar
				)
				try:
					self.actualizar_ruta('PRODUCCIÓN / NUEVO')
				except Exception:
					pass
				logging.info('Abriendo flujo de nueva producción...')
			except Exception:
				logging.exception('Error instanciando NuevoProduccionFlow en show_nuevo')
		except Exception:
			logging.exception('Error abriendo show_nuevo en ProduccionView')

	def _on_flow_cerrar(self):
		"""Callback cuando se cierra el flujo de nueva producción."""
		try:
			for w in list(self.central_area.winfo_children()):
				w.destroy()
			self.actualizar_ruta('PRODUCCIÓN')
		except Exception:
			logging.exception('Error en _on_flow_cerrar de ProduccionView')

	def show_costes(self):
		"""Mostrar vista de costes (placeholder)."""
		logging.info('COSTES - Gestión de costes de productos')

	def show_colores(self):
		"""Mostrar vista de colores (placeholder)."""
		logging.info('COLORES - Gestión de colores')

	def show_stock(self):
		"""Mostrar vista de stock (placeholder)."""
		logging.info('STOCK - Gestión de stock')
