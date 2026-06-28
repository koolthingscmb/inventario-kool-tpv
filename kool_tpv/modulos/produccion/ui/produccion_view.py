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

		# Cajero autenticado (persiste mientras el módulo esté activo)
		self._cajero_id = None
		self._cajero_nombre = ''

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
			'show_diseno_nuevo': self.show_diseno_nuevo,
			'show_config': self.show_config,
			'show_colores': self.show_proveedores,
			'show_stock': self.show_stock,
			'show_informes': self.show_informes,
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
			# No hay subvista → cerrar módulo → resetear cajero
			self._cajero_id = None
			self._cajero_nombre = ''
			return False
		except Exception:
			logging.exception('Error en _on_power de ProduccionView')
			return False

	def show_nuevo(self):
		"""Abrir flujo de nueva producción: autenticar cajero si no hay, luego flow."""
		try:
			for w in list(self.central_area.winfo_children()):
				w.destroy()
			if self._cajero_id is not None:
				self._iniciar_flow()
			else:
				self._mostrar_auth_cajero()
		except Exception:
			logging.exception('Error abriendo show_nuevo en ProduccionView')

	def _mostrar_auth_cajero(self):
		"""Mostrar vista de autenticación de cajero."""
		try:
			from kool_tpv.modulos.produccion.ui.subvistas.produccion_cajero_auth import CajeroAuthView
			self._cajero_auth = CajeroAuthView(
				self.central_area,
				db=self.db,
				on_success=self._on_cajero_auth_ok,
				on_cancel=self._on_flow_cerrar,
			)
			try:
				self.actualizar_ruta('PRODUCCIÓN / CAJERO')
			except Exception:
				pass
			logging.info('Autenticando cajero para producción...')
		except Exception:
			logging.exception('Error instanciando CajeroAuthView en show_nuevo')

	def _on_cajero_auth_ok(self, usuario_id: int, usuario_nombre: str):
		"""Cajero autenticado → guardar y crear flow."""
		self._cajero_id = usuario_id
		self._cajero_nombre = usuario_nombre
		try:
			if hasattr(self, '_cajero_auth') and self._cajero_auth:
				self._cajero_auth.destruir()
				self._cajero_auth = None
		except Exception:
			pass
		self._iniciar_flow()

	def _iniciar_flow(self):
		"""Crear el flujo de producción con el cajero ya autenticado."""
		try:
			from kool_tpv.modulos.produccion.ui.subvistas.produccion_nuevo_flow import NuevoProduccionFlow
			for w in list(self.central_area.winfo_children()):
				w.destroy()
			self._flow = NuevoProduccionFlow(
				self.central_area,
				db=self.db,
				keyboard_mgr=self.keyboard_mgr,
				on_cerrar=self._on_flow_cerrar,
				usuario_id=self._cajero_id,
				usuario_nombre=self._cajero_nombre,
			)
			try:
				self.actualizar_ruta('PRODUCCIÓN / NUEVO')
			except Exception:
				pass
			logging.info(f'Flujo de producción iniciado por cajero: {self._cajero_nombre}')
		except Exception:
			logging.exception('Error creando NuevoProduccionFlow tras auth')

	def _on_flow_cerrar(self):
		"""Callback cuando se cierra el flujo de nueva producción."""
		try:
			for w in list(self.central_area.winfo_children()):
				w.destroy()
			self.actualizar_ruta('PRODUCCIÓN')
		except Exception:
			logging.exception('Error en _on_flow_cerrar de ProduccionView')

	def show_diseno_nuevo(self):
		"""Abrir vista de nuevo diseño en la zona central."""
		try:
			from kool_tpv.modulos.produccion.ui.subvistas.produccion_diseno_nuevo import DisenoNuevoView
			try:
				for w in list(self.central_area.winfo_children()):
					w.destroy()
				self._diseno_view = DisenoNuevoView(
						self.central_area,
						db=self.db,
						on_cerrar=self._on_diseno_guardado,
					)
				try:
					self.actualizar_ruta('PRODUCCIÓN / NUEVO DISEÑO')
				except Exception:
					pass
				logging.info('Abriendo nuevo diseño...')
			except Exception:
				logging.exception('Error instanciando DisenoNuevoView en show_diseno_nuevo')
		except Exception:
			logging.exception('Error abriendo show_diseno_nuevo en ProduccionView')

	def _on_diseno_guardado(self, diseno=None):
		"""Tras guardar un diseno desde DISENO +: limpiar formulario y refrescar lista."""
		try:
			if hasattr(self, '_diseno_view') and self._diseno_view:
				self._diseno_view._limpiar_formulario()
		except Exception:
			logging.exception('Error limpiando formulario tras guardar diseno')

	def show_config(self):
		"""Abrir vista de configuración del taller (Backoffice)."""
		try:
			from kool_tpv.modulos.produccion.ui.subvistas.produccion_config import ProduccionConfigView
			for w in list(self.central_area.winfo_children()):
				w.destroy()
			
			view = ProduccionConfigView(
				self.central_area,
				db=self.db,
				on_cerrar=self._on_flow_cerrar
			)
			self.actualizar_ruta('PRODUCCIÓN / CONFIG')
			logging.info('Abriendo panel de configuración de producción...')
		except ImportError:
			# Si aún no existe el archivo, mostramos un aviso
			from kool_tpv.utils.widgets.notificaciones.toast_widget import ToastWidget
			ToastWidget.show(self.parent, "Módulo de configuración en desarrollo", tipo="info")
			logging.info('CONFIG - Gestión de configuración (Próximamente)')
		except Exception:
			logging.exception('Error abriendo show_config en ProduccionView')

	def show_proveedores(self, proveedor_id=None):
		"""Mostrar vista de proveedores del módulo de producción."""
		try:
			from kool_tpv.modulos.produccion.ui.subvistas.proveedores.produccion_proveedores_view import ProduccionProveedoresView
			for w in list(self.central_area.winfo_children()):
				w.destroy()
			
			view = ProduccionProveedoresView(
				self.central_area,
				db=self.db,
				owner=self
			)
			view.get_widget().pack(fill='both', expand=True)
			if proveedor_id:
				view.cargar_proveedor(proveedor_id)
			self.actualizar_ruta('PRODUCCIÓN / PROVEEDORES')
			logging.info('Abriendo gestión de proveedores...')
		except Exception:
			logging.exception('Error abriendo show_proveedores en ProduccionView')

	def show_configurar_mapeos(self, proveedor_id, proveedor_nombre='', tab_inicial='CSV'):
		"""Mostrar configurador unificado de mapeos para un proveedor."""
		try:
			from kool_tpv.modulos.produccion.ui.subvistas.proveedores.produccion_proveedores_configurador import ProduccionProveedoresConfigurador
			for w in list(self.central_area.winfo_children()):
				w.destroy()
			
			config_ui = ProduccionProveedoresConfigurador(
				self.central_area,
				db=self.db,
				proveedor_id=proveedor_id,
				proveedor_nombre=proveedor_nombre,
				owner=self,
				tab_inicial=tab_inicial
			)
			config_ui.get_widget().pack(fill='both', expand=True)
			self.actualizar_ruta(f'PRODUCCIÓN / PROVEEDORES / CONFIGURAR MAPEOS ({tab_inicial})')
			logging.info(f'Abriendo configurador de mapeos para proveedor {proveedor_id}...')
		except Exception:
			logging.exception('Error abriendo configurador de mapeos en ProduccionView')

	def show_mapeo_csv(self, proveedor_id, proveedor_nombre=''):
		"""Mostrar configurador unificado en la pestaña CSV."""
		self.show_configurar_mapeos(proveedor_id, proveedor_nombre, tab_inicial='CSV')

	def show_mapeo_colores(self, proveedor_id, proveedor_nombre=''):
		"""Mostrar configurador unificado en la pestaña COLORES."""
		self.show_configurar_mapeos(proveedor_id, proveedor_nombre, tab_inicial='COLORES')

	def show_importar_albaran(self, proveedor_id=None, proveedor_nombre=''):
		"""Mostrar importador de albarán para producción."""
		try:
			from kool_tpv.modulos.produccion.ui.subvistas.proveedores.produccion_importar_albaran import ProduccionImportarAlbaran
			for w in list(self.central_area.winfo_children()):
				w.destroy()
			
			importar_ui = ProduccionImportarAlbaran(
				self.central_area,
				db=self.db,
				proveedor_id=proveedor_id,
				proveedor_nombre=proveedor_nombre,
				owner=self
			)
			importar_ui.get_widget().pack(fill='both', expand=True)
			self.actualizar_ruta('PRODUCCIÓN / PROVEEDORES / IMPORTAR ALBARÁN')
			logging.info(f'Abriendo importador de albarán (proveedor {proveedor_id})...')
		except Exception:
			logging.exception('Error abriendo importador de albarán en ProduccionView')

	def show_proveedores_with_id(self, proveedor_id=None):
		"""Volver a la vista de proveedores seleccionando uno concreto."""
		try:
			from kool_tpv.modulos.produccion.ui.subvistas.proveedores.produccion_proveedores_view import ProduccionProveedoresView
			for w in list(self.central_area.winfo_children()):
				w.destroy()
			
			view = ProduccionProveedoresView(
				self.central_area,
				db=self.db,
				owner=self
			)
			view.get_widget().pack(fill='both', expand=True)
			if proveedor_id:
				view.cargar_proveedor(proveedor_id)
			self.actualizar_ruta('PRODUCCIÓN / PROVEEDORES')
		except Exception:
			logging.exception('Error volviendo a proveedores')

	def show_stock(self):
		"""Mostrar vista de gestión de stock base (material en blanco)."""
		try:
			from kool_tpv.modulos.produccion.ui.subvistas.produccion_stock_base_view import ProduccionStockBaseView
			for w in list(self.central_area.winfo_children()):
				w.destroy()
			
			view = ProduccionStockBaseView(
				self.central_area,
				db=self.db,
				on_cerrar=self._on_flow_cerrar
			)
			self.actualizar_ruta('PRODUCCIÓN / STOCK BASES')
			logging.info('Abriendo gestión de stock de bases...')
		except Exception:
			logging.exception('Error abriendo show_stock en ProduccionView')

	def show_informes(self):
		"""Mostrar vista de informes del módulo de producción."""
		try:
			from kool_tpv.modulos.produccion.ui.subvistas.produccion_informes_view import ProduccionInformesView
			for w in list(self.central_area.winfo_children()):
				w.destroy()
			
			view = ProduccionInformesView(
				self.central_area,
				db=self.db,
				km=self.keyboard_mgr
			)
			self.actualizar_ruta('PRODUCCIÓN / INFORMES')
			logging.info('Abriendo informes de producción...')
		except Exception:
			logging.exception('Error abriendo show_informes en ProduccionView')
