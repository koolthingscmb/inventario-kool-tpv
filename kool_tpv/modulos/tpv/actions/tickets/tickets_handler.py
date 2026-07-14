"""
Handler for Tickets histórico mode.

Responsible for loading/rendering histórico data and managing
resources like the VisorNegro. Placeholder file — no implementation yet.
"""
from typing import List, Dict, Any, Optional
import logging

from kool_tpv.modulos.tpv.ui.visor_negro import VisorNegro
from kool_tpv.base_datos.cierre_service import CierreService


class TicketsHandler:
	"""Handler skeleton for Tickets historic mode.

	Will be instantiated with the parent `TicketsUI` and must provide:
	- `load_historico(termino)` -> list of items
	- `render_historico(items)` -> render into parent's tree
	- `configurar_modo_historico()` -> adjust parent UI and show VisorNegro
	- `on_imprimir()` / `on_consultar()` / `teardown_historico()`
	"""

	def __init__(self, parent):
		self.parent = parent
		self.db = getattr(parent, 'db', None)
		self.cierre_svc = CierreService(self.db) if self.db is not None else None
		self._prev_double_bind = None

	def load_historico(self, termino: str = '') -> List[Dict[str, Any]]:
		"""Return items for histórico view. (To implement)

		Expected to return list of dicts matching parent's `columns_config_historico`.
		"""
		# Return a list of closures (pages) ordered newest first.
		try:
			sql = (
				"SELECT id, fecha_hora, num_ventas, total_ingresos, rango_inicio_ticket, rango_fin_ticket "
				"FROM cierres ORDER BY fecha_hora DESC"
			)
			rows = self.db.fetch_all(sql) if self.db is not None else []
			items: List[Dict[str, Any]] = []
			for r in rows or []:
				cid = r[0]
				fecha = r[1]
				# num_ventas is the stored number of tickets for the cierre
				num_tickets = int(r[2] or 0) if len(r) > 2 else 0
				total = float(r[3] or 0.0) if len(r) > 3 else 0.0
				r_start = r[4] if len(r) > 4 else None
				r_end = r[5] if len(r) > 5 else None
				# Build a human-friendly range string when possible
				if r_start is not None and r_end is not None:
					range_str = f"{int(r_start)} - {int(r_end)} ({fecha})"
				else:
					range_str = f"Cierre {cid} - {fecha}"
				items.append({
					'page_id': cid,
					'range': range_str,
					'num_tickets': num_tickets,
					'total': total,
					'closed': True,
				})
			return items
		except Exception:
			logging.exception('Error cargando listado de cierres (handler)')
			return []

	def render_historico(self, items: List[Dict[str, Any]]):
		"""Render items into parent's treeview."""
		try:
			tree = getattr(self.parent, 'tree', None)
			if tree is None:
				return
			# clear
			for iid in list(tree.get_children()):
				try:
					tree.delete(iid)
				except Exception:
					pass
			# insert pages (each row represents a cierre/page)
			for it in items:
				try:
					iid = str(it.get('page_id') or '')
					vals = [it.get('page_id'), it.get('range'), it.get('num_tickets'), it.get('total')]
					# append lock icon in 'range' if closed
					if it.get('closed'):
						vals[1] = f"🔒 {vals[1]}"
					tree.insert('', 'end', iid=iid, values=tuple(vals))
				except Exception:
					logging.exception('Error insertando fila historico (TicketsHandler)')
		except Exception:
			logging.exception('Error render_historico (TicketsHandler)')

	def configurar_modo_historico(self):
		"""Configure parent for histórico mode and show VisorNegro."""
		try:
			parent = self.parent
			# set title and columns
			parent.title_text = 'HISTÓRICO TICKETS'
			try:
				parent._aplicar_config_columnas(parent.columns_config_historico)
			except Exception:
				pass

			# Ensure VisorNegro exists and is visible
			try:
				# Prefer view.cart_view if available (same behaviour as cierre handler)
				view = getattr(parent, 'view', None)
				parent_widget = None
				if view is not None and getattr(view, 'cart_view', None) is not None:
					parent_widget = view.cart_view
				else:
					parent_widget = getattr(parent, 'overlay', None)
				if parent_widget is not None:
					if getattr(parent, '_visor_negro', None) is None:
						parent._visor_negro = VisorNegro(parent_widget)
					# configure and show with the same appearance as other handlers
					parent._visor_negro.set_text('')
					try:
						parent._visor_negro.set_text_color('#00FF00')
					except Exception:
						pass
					try:
						parent._visor_negro.set_font_size(13)
					except Exception:
						pass
					parent._visor_negro.show()
			except Exception:
				logging.exception('Error mostrando VisorNegro (TicketsHandler)')

			# Bind doble clic on the tree to mostrar ticket in visor, saving previous binding
			try:
				tree = getattr(parent, 'tree', None)
				if tree is not None:
					try:
						# Save previous binding (if any) to restore later
						try:
							self._prev_double_bind = tree.bind('<Double-1>')
						except Exception:
							self._prev_double_bind = None
						# Bind our handler
						try:
							tree.bind('<Double-1>', lambda e: self.on_mostrar())
						except Exception:
							pass
					except Exception:
						pass
			except Exception:
				pass
		except Exception:
			logging.exception('Error configurando modo historico (TicketsHandler)')

	def on_imprimir(self):
		"""Print selected tickets/pages (to implement)."""
		raise NotImplementedError()

	def on_consultar(self):
		"""Consultar tickets action (to implement)."""
		raise NotImplementedError()

	def teardown_historico(self):
		"""Restore parent state when leaving histórico mode."""
		try:
			# restore previous bindings if any
			tree = getattr(self.parent, 'tree', None)
			if tree is not None and getattr(self, '_prev_double_bind', None):
				try:
					tree.bind('<Double-1>', self._prev_double_bind)
				except Exception:
					pass
		except Exception:
			logging.exception('Error en teardown_historico (TicketsHandler)')

	def on_mostrar(self):
		"""Mostrar el `ticket_text` del ticket seleccionado en el VisorNegro."""
		try:
			parent = self.parent
			tree = getattr(parent, 'tree', None)
			sel = list(tree.selection() or []) if tree is not None else []

			if not sel:
				logging.info('No hay selección para Mostrar (TicketsHandler)')
				return

			if len(sel) > 1:
				try:
					from kool_tpv.utils.widgets.notificaciones import ToastWidget
					root = parent.overlay.winfo_toplevel() if getattr(parent, 'overlay', None) is not None else None
					ToastWidget.show(root, 'SOLAMENTE SE PUEDE MOSTRAR UN TICKET A LA VEZ', tipo='error')
				except Exception:
					logging.exception('Error mostrando diálogo de selección múltiple en Mostrar')
				return

			try:
				tid = int(sel[0])
			except Exception:
				logging.info('ID seleccionado inválido para Mostrar')
				return

			# obtain ticket_text from DB if possible
			try:
				row = None
				if getattr(parent, 'db', None) is not None:
					try:
						row = parent.db.fetch_one("SELECT ticket_text FROM tickets WHERE id = ?", (tid,))
					except Exception:
						logging.exception('Error leyendo ticket_text desde BD (TicketsHandler)')
				ticket_text = row[0] if row and row[0] else ''
			except Exception:
				logging.exception('Error recuperando ticket para Mostrar')
				ticket_text = ''

			# ensure VisorNegro exists and show text
			try:
				view = getattr(parent, 'view', None)
				parent_widget = None
				if view is not None and getattr(view, 'cart_view', None) is not None:
					parent_widget = view.cart_view
				else:
					parent_widget = getattr(parent, 'overlay', None)

				if parent_widget is not None:
					if getattr(parent, '_visor_negro', None) is None:
						try:
							parent._visor_negro = VisorNegro(parent_widget)
						except Exception:
							logging.exception('Error creando VisorNegro (mostrar ticket)')
					try:
						parent._visor_negro.set_text_color('#00FF00')
					except Exception:
						pass
					try:
						parent._visor_negro.set_font_size(13)
					except Exception:
						pass
					clean_text = (ticket_text or '').replace('{{BOLD_ON}}', '').replace('{{BOLD_OFF}}', '').replace('{{BADGE}}', '')
					try:
						parent._visor_negro.set_text(clean_text)
					except Exception:
						parent._visor_negro.set_text(str(ticket_text))
					try:
						parent._visor_negro.show()
					except Exception:
						pass
			except Exception:
				logging.exception('Error configurando VisorNegro para Mostrar (TicketsHandler)')

		except Exception:
			logging.exception('Error en on_mostrar (TicketsHandler)')

