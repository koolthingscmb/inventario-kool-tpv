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
		self._ruta_actual = 'PRODUCCIÓN'
		self._ruta_anterior = ''

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
			'show_entrada_manual_produccion': self.show_entrada_manual_produccion,
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
					if hasattr(widget, '_volver'):
						widget._volver()
						return True
					widget.destroy()
				try:
					self.actualizar_ruta('PRODUCCIÓN')
				except Exception:
					pass
				return True
			# No hay subvista → cerrar módulo (mantener cajero para sesiones futuras)
			return False
		except Exception:
			logging.exception('Error en _on_power de ProduccionView')
			return False

	def actualizar_ruta(self, sub_seccion: str = None, callbacks: dict = None):
		"""Sobrescribir para trackear la ruta anterior y permitir navegación inteligente."""
		try:
			# Trackear historia para el "Volver" inteligente
			if hasattr(self, '_ruta_actual'):
				self._ruta_anterior = self._ruta_actual
			self._ruta_actual = sub_seccion or 'PRODUCCIÓN'
			
			# Llamar al original de BaseModuleView
			super().actualizar_ruta(sub_seccion, callbacks)
		except Exception:
			logging.exception("Error en actualizar_ruta de ProduccionView")

	def show_nuevo(self):
		"""Abrir flujo de nueva producción."""
		try:
			self._iniciar_flow()
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

	def _on_cajero_auth_from_flow(self, usuario_id: int, usuario_nombre: str):
		"""Cajero autenticado dentro del flow → solo guardar credenciales."""
		self._cajero_id = usuario_id
		self._cajero_nombre = usuario_nombre

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
				on_cajero_auth=self._on_cajero_auth_from_flow,
				on_historial=self.show_historial_lineas,
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
						owner=self
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
			if diseno is None:
				# Si es cancelación o Esc, cerramos la vista completa
				self._on_flow_cerrar()
				return

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
			widget = config_ui.get_widget()
			widget._volver = config_ui._on_volver
			widget.pack(fill='both', expand=True)
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
			widget = importar_ui.get_widget()
			widget._volver = importar_ui._on_volver_click
			widget.pack(fill='both', expand=True)
			self.actualizar_ruta('PRODUCCIÓN / PROVEEDORES / IMPORTAR ALBARÁN')
			logging.info(f'Abriendo importador de albarán (proveedor {proveedor_id})...')
		except Exception:
			logging.exception('Error abriendo importador de albarán en ProduccionView')

	def show_entrada_manual_produccion(self, proveedor_id=None, proveedor_nombre='', albaran_id=None):
		"""Mostrar entrada manual de albarán para producción."""
		try:
			from kool_tpv.modulos.produccion.ui.subvistas.proveedores.produccion_entrada_manual import ProduccionEntradaManualUI
			for w in list(self.central_area.winfo_children()):
				w.destroy()
			
			entrada_ui = ProduccionEntradaManualUI(
				self.central_area,
				db=self.db,
				proveedor_id=proveedor_id,
				proveedor_nombre=proveedor_nombre,
				owner=self,
				albaran_id=albaran_id
			)
			widget = entrada_ui.get_widget()
			widget._volver = entrada_ui._on_volver_click
			widget.pack(fill='both', expand=True)
			
			ruta = 'PRODUCCIÓN / PROVEEDORES / ENTRADA MANUAL'
			if albaran_id:
				ruta = f'PRODUCCIÓN / PROVEEDORES / EDITAR ALBARÁN {albaran_id}'
			self.actualizar_ruta(ruta)
			
			logging.info(f'Abriendo entrada manual de albarán (proveedor {proveedor_id}, albaran {albaran_id})...')
		except Exception:
			logging.exception('Error abriendo entrada manual de albarán en ProduccionView')

	def show_consultar_albaranes(self, proveedor_id, proveedor_nombre):
		"""Mostrar listado de albaranes de un proveedor."""
		try:
			from kool_tpv.modulos.produccion.ui.subvistas.proveedores.produccion_consultar_albaranes import ProduccionConsultarAlbaranesUI
			for w in list(self.central_area.winfo_children()):
				w.destroy()
			
			consultar_ui = ProduccionConsultarAlbaranesUI(
				self.central_area,
				db=self.db,
				proveedor_id=proveedor_id,
				proveedor_nombre=proveedor_nombre,
				owner=self
			)
			widget = consultar_ui.get_widget()
			widget.pack(fill='both', expand=True)
			self.actualizar_ruta(f'PRODUCCIÓN / PROVEEDORES / ALBARANES: {proveedor_nombre}')
			logging.info(f'Consultando albaranes de proveedor {proveedor_id} ({proveedor_nombre})...')
		except Exception:
			logging.exception('Error abriendo consulta de albaranes en ProduccionView')

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
				on_cerrar=self._on_flow_cerrar,
				owner=self
			)
			self.actualizar_ruta('PRODUCCIÓN / STOCK BASES')
			logging.info('Abriendo gestión de stock de bases...')
		except Exception:
			logging.exception('Error abriendo show_stock en ProduccionView')

	def show_informes(self, state_to_restore: Optional[dict] = None):
		"""Mostrar vista de informes del módulo de producción."""
		try:
			from kool_tpv.modulos.produccion.ui.subvistas.produccion_informes_view import ProduccionInformesView
			for w in list(self.central_area.winfo_children()):
				w.destroy()
			
			view = ProduccionInformesView(
				self.central_area,
				db=self.db,
				km=self.keyboard_mgr,
				owner=self
			)
			self.actualizar_ruta('PRODUCCIÓN / INFORMES')
			
			if state_to_restore:
				# Dar un pequeño margen para que la UI se asiente
				self.central_area.after(100, lambda: view.restore_state(state_to_restore))
				
			logging.info('Abriendo informes de producción...')
		except Exception:
			logging.exception('Error abriendo show_informes en ProduccionView')

	def show_editar_linea(self, linea_id: int, state_informe: Optional[dict] = None):
		"""Mostrar subvista de edición para una línea de producción."""
		try:
			from kool_tpv.modulos.produccion.ui.subvistas.produccion_edicion_linea_view import ProduccionEdicionLineaView
			for w in list(self.central_area.winfo_children()):
				w.destroy()
			
			# Determinar a dónde volver
			if state_informe:
				on_volver = lambda: self.show_informes(state_informe)
			elif self._ruta_anterior == 'PRODUCCIÓN / HISTORIAL LÍNEAS':
				on_volver = self.show_historial_lineas
			else:
				on_volver = self.show_nuevo

			view = ProduccionEdicionLineaView(
				self.central_area,
				db=self.db,
				linea_id=linea_id,
				on_volver=on_volver
			)
			self.actualizar_ruta(f'PRODUCCIÓN / EDITAR LÍNEA {linea_id}')
			logging.info(f'Editando línea de producción {linea_id}...')
		except Exception:
			logging.exception('Error abriendo show_editar_linea en ProduccionView')

	def show_historial_lineas(self):
		"""Mostrar vista de historial de líneas de producción."""
		try:
			from kool_tpv.modulos.produccion.ui.subvistas.produccion_historial_lineas_view import ProduccionHistorialLineasView
			for w in list(self.central_area.winfo_children()):
				w.destroy()
			
			view = ProduccionHistorialLineasView(
				self.central_area,
				db=self.db,
				on_volver=self.show_nuevo,
				keyboard_manager=self.keyboard_mgr,
				owner=self
			)
			self.actualizar_ruta('PRODUCCIÓN / HISTORIAL LÍNEAS')
			logging.info('Abriendo historial de líneas de producción...')
		except Exception:
			logging.exception('Error abriendo show_historial_lineas en ProduccionView')
