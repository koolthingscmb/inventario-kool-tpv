"""
Tickets UI (overlay) — dual-mode entry point.

Implements the main overlay that will switch between the
initial tickets view and the histórico/hitsory view via a handler.
Placeholder file — no implementation yet.
"""
import logging
from typing import Optional, List, Dict, Any

import customtkinter as ctk

from .tickets_base_ui import TicketsBaseUI
from kool_tpv.utils.templates.selection_overlay_visor import SelectionOverlayVisor
from kool_tpv.modulos.tpv.ui.visor_negro import VisorNegro
from .tickets_handler import TicketsHandler


class TicketsUI(TicketsBaseUI):
	"""Overlay UI for managing Tickets (dual-mode).

	Responsibilities (skeleton):
	- Mantener `self.modo` ('tickets' | 'historico')
	- Configurar columnas para cada modo
	- Crear/mostrar `VisorNegro` al abrir y mantenerlo hasta cerrar
	- Crear header con botones: Imprimir (blanco/negro), Crear Factura, Consultar Tickets
	- Delegar modo histórico a `TicketsHandler`
	"""

	def __init__(self, view_or_action_panel, db, on_selection_callback: Optional[callable] = None):
		ui_cfg = {'page_size': 30}
		super().__init__(view_or_action_panel, db=db, on_selection_callback=on_selection_callback, ui_config=ui_cfg)

		self.db = db
		self.modo = 'tickets'  # 'tickets' o 'historico'

		# Handler para modo histórico
		try:
			self._handler = TicketsHandler(self)
		except Exception:
			self._handler = None
			logging.exception('Error instanciando TicketsHandler')

		# Title
		self.title_text = 'TICKETS'
		try:
			if hasattr(self, 'header_label') and self.header_label is not None:
				self.header_label.configure(text=self.title_text)
		except Exception:
			pass

		# Column configs
		self.columns_config_tickets = [
			("id", "ID ticket", 80, "center"),
			("created_at", "Día / Hora", 180, "center"),
			("total", "TOTAL", 120, "e"),
			("cajero", "Cajero", 140, "center"),
			("cliente", "Cliente", 180, "w"),
		]

		self.columns_config_historico = [
			("page_id", "Página", 100, "center"),
			("range", "Rango tickets", 260, "w"),
			("num_tickets", "Tickets", 80, "center"),
			("total", "Total €", 120, "e"),
		]

		# Apply initial columns
		try:
			self.columns_config = self.columns_config_tickets
			self._aplicar_config_columnas(self.columns_config)
		except Exception:
			logging.exception('Error aplicando columnas en TicketsUI')

		# Remove search box and accept/add buttons (not needed in Tickets overlay): destroy to remove DOM
		try:
			if hasattr(self, 'search_entry') and getattr(self, 'search_entry', None) is not None:
				try:
					self.search_entry.destroy()
				except Exception:
					pass
			if hasattr(self, 'search_controls_frame') and getattr(self, 'search_controls_frame', None) is not None:
				try:
					self.search_controls_frame.destroy()
				except Exception:
					pass
			# Destroy accept/add buttons if present
			if hasattr(self, 'aceptar_btn') and getattr(self, 'aceptar_btn', None) is not None:
				try:
					self.aceptar_btn.destroy()
				except Exception:
					pass
			if hasattr(self, 'anadir_btn') and getattr(self, 'anadir_btn', None) is not None:
				try:
					self.anadir_btn.destroy()
				except Exception:
					pass
		except Exception:
			logging.exception('Error destruyendo search/accept/add en TicketsUI')

		# VisorNegro — mantener activo mientras el overlay esté visible
		try:
			# Prefer `view.cart_view` when available (same as cierre_ui)
			view = getattr(self, 'view', None)
			parent_widget = None
			if view is not None and getattr(view, 'cart_view', None) is not None:
				parent_widget = view.cart_view
			else:
				parent_widget = getattr(self, 'overlay', None)
			if parent_widget is not None:
				self._visor_negro = VisorNegro(parent_widget)
				self._visor_negro.set_text('')
				# Configure and show VisorNegro immediately when opening Tickets UI
				try:
					self._visor_negro.set_text_color('#00FF00')
				except Exception:
					pass
				try:
					self._visor_negro.set_font_size(13)
				except Exception:
					pass
				try:
					self._visor_negro.show()
				except Exception:
					pass
		except Exception:
			logging.exception('Error creando VisorNegro en TicketsUI')

		# Header buttons (skeleton)
		self._add_header_controls()

		# Configure footer pagination buttons to use TicketsUI handlers
		try:
			if hasattr(self, 'prev_btn'):
				try:
					self.prev_btn.configure(command=self._on_prev_page)
				except Exception:
					pass
			if hasattr(self, 'next_btn'):
				try:
					self.next_btn.configure(command=self._on_next_page)
				except Exception:
					pass
			# Ensure footer page_label available for updates
			try:
				if hasattr(self, 'page_label'):
					try:
						self.page_label.configure(text='Página 0')
					except Exception:
						pass
			except Exception:
				pass
		except Exception:
			pass

		# Remove footer filters (right-side) as requested
		try:
			if hasattr(self, 'filters_frame') and getattr(self, 'filters_frame', None) is not None:
				try:
					self.filters_frame.destroy()
				except Exception:
					pass
		except Exception:
			pass

		# Items placeholder
		self._items: List[Dict[str, Any]] = []

	def _add_header_controls(self):
		"""Crear los botones solicitados (estilo y comandos a implementar).

		- `Imprimir`: fg_color blanco, text_color negro
		- `Crear Factura`
		- `Consultar Tickets`
		"""
		try:
			container = getattr(self, 'top_buttons', None) or getattr(self, 'overlay', None)
			self._header_buttons_row = ctk.CTkFrame(container, fg_color='transparent')
			self._header_buttons_row.pack(side='top', fill='x', pady=(6, 4))

			self.imprimir_btn = ctk.CTkButton(self._header_buttons_row, text='IMPRIMIR', fg_color='#FFFFFF', text_color='#000000', width=140, command=lambda: None)
			self.crear_factura_btn = ctk.CTkButton(self._header_buttons_row, text='Crear Factura', width=140, command=lambda: None)
			self.consultar_btn = ctk.CTkButton(self._header_buttons_row, text='Consultar Tickets', width=160, command=lambda: None)

			self.imprimir_btn.pack(side='left', padx=5)
			self.crear_factura_btn.pack(side='left', padx=5)
			self.consultar_btn.pack(side='left', padx=5)
		except Exception:
			logging.exception('Error creando header buttons en TicketsUI')

	# Note: use footer pagination controls from SelectionOverlayTemplate (prev_btn/next_btn/page_label)

	# Load and render implementation: handles open tickets (page 0) and closure pages (>0)
	def _load_and_render(self, termino: str = ''):
		"""Cargar tickets según modo actual y renderizar."""
		try:
			# We implement pagination within the tickets view.
			# page_index: 0 = open tickets (no cierre), >0 = closure pages list index (1 => latest cierre)
			self._page_index = getattr(self, '_page_index', 0)
			if self.modo == 'tickets':
				if self._page_index == 0:
					# open tickets without cierre
					try:
						limit = int(getattr(self, 'ui_config', {}).get('page_size', 30))
					except Exception:
						limit = 30
					sql = "SELECT id, created_at, total, cajero, cliente FROM tickets WHERE cierre_id IS NULL OR cierre_id=0 ORDER BY created_at DESC LIMIT ?"
					rows = self.db.fetch_all(sql, (limit,)) if self.db is not None else []
					items = []
					for r in rows or []:
						try:
							created = r[1]
							# Format created date to DD-MM-AA / HH:MM if possible
							try:
								from datetime import datetime
								dt = datetime.fromisoformat(str(created))
								created_str = dt.strftime('%d-%m-%y / %H:%M')
							except Exception:
								created_str = str(created)
							items.append({
								'id': r[0],
								'created_at': created_str,
								'total': float(r[2] or 0.0),
								'cajero': r[3] or '',
								'cliente': r[4] or '',
							})
						except Exception:
							logging.exception('Error normalizando fila de ticket')
					self._items = items
					self._render_items(self._items)
				else:
					# page_index > 0 -> load closures list and render selected page tickets
					try:
						# get list of cierres
						pages = self._handler.load_historico('') if self._handler is not None else []
					except Exception:
						pages = []
					self._historico_pages = pages
					# clamp index
					idx = self._page_index - 1
					if idx < 0 or idx >= len(pages):
						# nothing to show
						self._items = []
						self._render_items(self._items)
						return
					cierre_id = pages[idx].get('page_id')
					# fetch tickets for this cierre
					try:
						sql = "SELECT id, created_at, total, cajero, cliente FROM tickets WHERE cierre_id = ? ORDER BY created_at DESC"
						rows = self.db.fetch_all(sql, (cierre_id,)) if self.db is not None else []
					except Exception:
						rows = []
					items = []
					for r in rows or []:
						try:
							from datetime import datetime
							created = r[1]
							try:
								dt = datetime.fromisoformat(str(created))
								created_str = dt.strftime('%d-%m-%y / %H:%M')
							except Exception:
								created_str = str(created)
							items.append({
								'id': r[0],
								'created_at': created_str,
								'total': float(r[2] or 0.0),
								'cajero': r[3] or '',
								'cliente': r[4] or '',
							})
						except Exception:
							logging.exception('Error normalizando fila de ticket (cierre)')
					self._items = items
					# show page label
					try:
						self.page_label.configure(text=f"Página {cierre_id}")
					except Exception:
						pass
					self._render_items(self._items)
			elif self.modo == 'historico':
				# Delegate to handler to load and render pages (list of closures)
				try:
					items = self._handler.load_historico(termino) if self._handler is not None else []
					self._historico_pages = items
					self._handler.render_historico(items)
				except Exception:
					logging.exception('Error cargando historico desde handler')
		except Exception:
			logging.exception('Error en _load_and_render de TicketsUI')

	def _render_items(self, items):
		"""Render ticket rows into the parent's treeview."""
		try:
			tree = getattr(self, 'tree', None)
			if tree is None:
				return
			# clear
			for iid in list(tree.get_children()):
				try:
					tree.delete(iid)
				except Exception:
					pass
			# insert
			for it in items:
				try:
					iid = str(it.get('id') or '')
					vals = tuple(it.get(col[0]) for col in self.columns_config)
					tree.insert('', 'end', iid=iid, values=vals)
				except Exception:
					logging.exception('Error insertando fila ticket (TicketsUI)')
		except Exception:
			logging.exception('Error en _render_items (TicketsUI)')

	def _on_prev_page(self):
		try:
			# move to older page (increase index). Max index depends on number of cierres available
			self._page_index = getattr(self, '_page_index', 0) + 1
			# reload
			self._load_and_render('')
		except Exception:
			logging.exception('Error en _on_prev_page')

	def _on_next_page(self):
		try:
			self._page_index = max(0, getattr(self, '_page_index', 0) - 1)
			# reload
			if self._page_index == 0:
				try:
					self.page_label.configure(text='Página 0')
				except Exception:
					pass
			self._load_and_render('')
		except Exception:
			logging.exception('Error en _on_next_page')

	def _cambiar_modo(self, nuevo_modo: str):
		"""Cambiar entre modos 'tickets' y 'historico'."""
		try:
			self.modo = nuevo_modo

			if self.modo == 'tickets':
				self._configurar_tickets()
			elif self.modo == 'historico':
				if self._handler is not None:
					try:
						self._handler.configurar_modo_historico()
					except Exception:
						logging.exception('Error instanciando modo historico (TicketsUI)')

			# Recargar datos para el modo
			try:
				self._load_and_render('')
			except Exception:
				logging.exception('Error recargando datos tras _cambiar_modo (TicketsUI)')

		except Exception:
			logging.exception('Error en _cambiar_modo (TicketsUI)')

	def _configurar_tickets(self):
		"""Restaurar UI al modo tickets (ocultar/imprimir teardown)."""
		try:
			self.title_text = 'TICKETS'
			try:
				if hasattr(self, 'header_label') and self.header_label is not None:
					self.header_label.configure(text=self.title_text)
			except Exception:
				pass

			# aplicar columnas de tickets
			try:
				self._aplicar_config_columnas(self.columns_config_tickets)
			except Exception:
				pass

			# ocultar imprimir en header si existe
			try:
				if hasattr(self, 'imprimir_btn'):
					self.imprimir_btn.pack_forget()
			except Exception:
				pass

			# destruir VisorNegro si existe
			try:
				if getattr(self, '_visor_negro', None):
					try:
						self._visor_negro.destroy()
					except Exception:
						pass
					self._visor_negro = None
			except Exception:
				pass

			# notify handler to teardown bindings if needed
			try:
				if self._handler is not None:
					try:
						self._handler.teardown_historico()
					except Exception:
						pass
			except Exception:
				pass

		except Exception:
			logging.exception('Error en _configurar_tickets (TicketsUI)')

	def hide(self):
		"""Override hide: if estamos en histórico, volver a modo tickets en vez de cerrar."""
		try:
			if getattr(self, 'modo', None) == 'historico':
				# cambiar a modo tickets, no cerrar overlay
				self._cambiar_modo('tickets')
				return
			# else: proceder a ocultar/limpiar
			if getattr(self, '_visor_negro', None):
				try:
					self._visor_negro.hide()
				except Exception:
					pass
				try:
					self._visor_negro.destroy()
				except Exception:
					pass
				self._visor_negro = None
			super().hide()
		except Exception:
			logging.exception('Error en hide() (TicketsUI)')
			super().hide()

	def show(self) -> None:
		"""Mostrar overlay y asegurarse de que el VisorNegro esté visible."""
		try:
			super().show()
			# recreate/show VisorNegro every time the overlay is shown
			try:
				view = getattr(self, 'view', None)
				parent_widget = None
				if view is not None and getattr(view, 'cart_view', None) is not None:
					parent_widget = view.cart_view
				else:
					parent_widget = getattr(self, 'overlay', None)
				if parent_widget is not None:
					if getattr(self, '_visor_negro', None) is None:
						self._visor_negro = VisorNegro(parent_widget)
					try:
						self._visor_negro.set_text('')
					except Exception:
						pass
					try:
						self._visor_negro.set_text_color('#00FF00')
					except Exception:
						pass
					try:
						self._visor_negro.set_font_size(13)
					except Exception:
						pass
					try:
						self._visor_negro.show()
					except Exception:
						pass
			except Exception:
				logging.exception('Error asegurando VisorNegro en show() (TicketsUI)')
		except Exception:
			logging.exception('Error mostrando TicketsUI')

