"""
Tickets UI (overlay) — dual-mode entry point.

Implements the main overlay that will switch between the
initial tickets view and the histórico/hitsory view via a handler.
Placeholder file — no implementation yet.
"""
import logging
from typing import Optional, List, Dict, Any

import customtkinter as ctk
import tkinter as tk

from .tickets_base_ui import TicketsBaseUI
from kool_tpv.utils.templates.selection_overlay_visor import SelectionOverlayVisor
from kool_tpv.modulos.tpv.ui.visor_negro import VisorNegro
from .tickets_handler import TicketsHandler
from kool_tpv.modulos.impresion.impresora_service import ImpresoraService


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
				# Do NOT show the VisorNegro here automatically; it should only be
				# displayed when explicitly requested by the handler or user action.
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

			self.imprimir_btn = ctk.CTkButton(self._header_buttons_row, text='IMPRIMIR', fg_color='#FFFFFF', text_color='#000000', width=140, command=self._on_imprimir)
			self.mostrar_btn = ctk.CTkButton(self._header_buttons_row, text='Mostrar', width=120, command=self._on_mostrar)
			self.crear_factura_btn = ctk.CTkButton(self._header_buttons_row, text='Crear Factura', width=140, command=lambda: None)
			self.imprimir_btn.pack(side='left', padx=5)
			self.mostrar_btn.pack(side='left', padx=5)
			self.crear_factura_btn.pack(side='left', padx=5)
			# Search container (entry + clear button)
			try:
				self._search_container = ctk.CTkFrame(self._header_buttons_row, fg_color='transparent')
				self._search_container.pack(side='left', padx=5)
				self.search_entry = ctk.CTkEntry(self._search_container, placeholder_text='Buscar ticket, cliente...', width=240)
				self.search_entry.pack(side='left', fill='x', expand=True)
				self.clear_search_btn = ctk.CTkButton(self._search_container, text='Reset', width=60, height=28, command=self._on_limpiar_busqueda)
				self.clear_search_btn.pack(side='left', padx=(6, 0))
				# Bind Enter to search
				try:
					self.search_entry.bind('<Return>', lambda e: self._on_buscar())
				except Exception:
					pass
			except Exception:
				logging.exception('Error creando search controls en header (TicketsUI)')

			# Search filter checkboxes (below header buttons)
			try:
				parent_for_checks = container if container is not None else getattr(self, 'overlay', None)
				self._search_checkboxes_frame = ctk.CTkFrame(parent_for_checks, fg_color='transparent')
				self._search_checkboxes_frame.pack(side='top', fill='x', pady=(6, 0))
				# BooleanVars for checkbox states (default: unchecked)
				self.chk_fecha_var = tk.BooleanVar(value=False)
				self.chk_ticket_var = tk.BooleanVar(value=False)
				self.chk_cajero_var = tk.BooleanVar(value=False)
				self.chk_cliente_var = tk.BooleanVar(value=False)
				# Create checkboxes
				self.chk_fecha = ctk.CTkCheckBox(self._search_checkboxes_frame, text='Fecha', variable=self.chk_fecha_var)
				self.chk_ticket = ctk.CTkCheckBox(self._search_checkboxes_frame, text='Ticket', variable=self.chk_ticket_var)
				self.chk_cajero = ctk.CTkCheckBox(self._search_checkboxes_frame, text='Cajero', variable=self.chk_cajero_var)
				self.chk_cliente = ctk.CTkCheckBox(self._search_checkboxes_frame, text='Cliente', variable=self.chk_cliente_var)
				# Pack checkboxes compactly
				self.chk_fecha.pack(side='left', padx=(6, 4))
				self.chk_ticket.pack(side='left', padx=(4, 4))
				self.chk_cajero.pack(side='left', padx=(4, 4))
				self.chk_cliente.pack(side='left', padx=(4, 4))
			except Exception:
				logging.exception('Error creando checkboxes de búsqueda (TicketsUI)')
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
							# Format created date to full ISO-like string YYYY-MM-DD HH:MM:SS
							try:
								from datetime import datetime
								dt = datetime.fromisoformat(str(created))
								created_str = dt.strftime('%Y-%m-%d %H:%M:%S')
							except Exception:
								created_str = str(created)
							items.append({
								'id': r[0],
								'created_at': created_str,
								'total': f"{(float(r[2] or 0.0)):.2f}",
								'cajero': r[3] or '',
								'cliente': r[4] or '',
							})
						except Exception:
							logging.exception('Error normalizando fila de ticket')
					self._items = items
					# determine if there are closure pages available and update pagination buttons
					try:
						pages = self._handler.load_historico('') if self._handler is not None else []
						self._historico_pages = pages
						total_pages = len(pages or [])
						if hasattr(self, 'prev_btn'):
							self.prev_btn.configure(state=('normal' if total_pages > 0 else 'disabled'))
						if hasattr(self, 'next_btn'):
							self.next_btn.configure(state='disabled')
					except Exception:
						pass
					self._render_items(self._items)
				else:
					# page_index > 0 -> load closures list and render selected page tickets
					try:
						# get list of cierres
						pages = self._handler.load_historico('') if self._handler is not None else []
					except Exception:
						pages = []
					self._historico_pages = pages
					# update pagination controls for cierre pages
					try:
						total_pages = len(pages or [])
						if hasattr(self, 'prev_btn'):
							self.prev_btn.configure(state=('normal' if getattr(self, '_page_index', 0) < total_pages else 'disabled'))
						if hasattr(self, 'next_btn'):
							self.next_btn.configure(state=('normal' if getattr(self, '_page_index', 0) > 0 else 'disabled'))
					except Exception:
						pass
					# clamp index
					idx = self._page_index - 1
					if idx < 0 or idx >= len(pages):
						# nothing to show
						self._items = []
						self._render_items(self._items)
						# update pagination controls when out of range
						try:
							if hasattr(self, 'prev_btn'):
								self.prev_btn.configure(state='disabled')
							if hasattr(self, 'next_btn'):
								self.next_btn.configure(state=('normal' if getattr(self, '_page_index', 0) > 0 else 'disabled'))
						except Exception:
							pass
						return
					cierre_id = pages[idx].get('page_id')
					# fetch cierre details to obtain ticket range
					cierres_rows = None
					cierre_row = None
					try:
						# prefer handler's cierre_svc when available
						cierre_svc = None
						if getattr(self, '_handler', None) is not None and getattr(self._handler, 'cierre_svc', None) is not None:
							cierre_svc = self._handler.cierre_svc
						if cierre_svc is not None:
							cierre_row = cierre_svc.obtener_cierre_por_id(cierre_id)
					except Exception:
						cierre_row = None
					# if cierre provides rango_inicio_ticket/rango_fin_ticket, use num_ticket range
					rows = []
					try:
						if cierre_row and cierre_row.get('rango_inicio_ticket') is not None and cierre_row.get('rango_fin_ticket') is not None:
							r0 = int(cierre_row.get('rango_inicio_ticket'))
							r1 = int(cierre_row.get('rango_fin_ticket'))
							sql = "SELECT id, created_at, total, cajero, cliente, num_ticket FROM tickets WHERE num_ticket BETWEEN ? AND ? ORDER BY created_at DESC"
							rows = self.db.fetch_all(sql, (r0, r1)) if self.db is not None else []
						else:
							# fallback: use cierre_id marker on tickets
							sql = "SELECT id, created_at, total, cajero, cliente, num_ticket FROM tickets WHERE cierre_id = ? ORDER BY created_at DESC"
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
								created_str = dt.strftime('%Y-%m-%d %H:%M:%S')
							except Exception:
								created_str = str(created)
							item = {
								'id': r[0],
								'created_at': created_str,
								'total': f"{(float(r[2] or 0.0)):.2f}",
								'cajero': r[3] or '',
								'cliente': r[4] or '',
							}
							# if num_ticket column present in select, include it
							try:
								if len(r) > 5 and r[5] is not None:
									item['num_ticket'] = r[5]
							except Exception:
								pass
							items.append(item)
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

		# After loading, ensure pagination buttons reflect current state
		except Exception:
			logging.exception('Error en _load_and_render de TicketsUI')
		finally:
			try:
				# Only manage prev/next for tickets mode
				if getattr(self, 'modo', None) == 'tickets':
					pages = getattr(self, '_historico_pages', None) or []
					total_pages = len(pages)
					pi = getattr(self, '_page_index', 0)
					# prev: go to older pages (enable if there are any closures beyond current)
					if hasattr(self, 'prev_btn'):
						try:
							self.prev_btn.configure(state=('normal' if (pi < total_pages and total_pages > 0) else 'disabled'))
						except Exception:
							pass
					# next: return toward page 0 (enable if we're beyond 0)
					if hasattr(self, 'next_btn'):
						try:
							self.next_btn.configure(state=('normal' if pi > 0 else 'disabled'))
						except Exception:
							pass
			except Exception:
				pass

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

	def _on_mostrar(self, event=None):
		"""Mostrar ticket seleccionado(s) en VisorNegro.
		- Si no hay selección: no hace nada.
		- Si hay >1 selección: mostrar diálogo de advertencia.
		- Si 1 selección: cargar `ticket_text` desde BD y mostrar en VisorNegro.
		"""
		try:
			tree = getattr(self, 'tree', None)
			if tree is None:
				return
			sel = list(tree.selection() or [])
			if not sel:
				return
			if len(sel) > 1:
				try:
					from kool_tpv.utils.custom_dialog import show_warning
					root = self.overlay.winfo_toplevel() if getattr(self, 'overlay', None) is not None else None
					show_warning(root, 'Selecciona únicamente un ticket', 'Selecciona únicamente un ticket')
				except Exception:
					logging.exception('Error mostrando warning seleccion multiple (TicketsUI)')
				return
			# single selection
			tid = None
			try:
				tid = int(sel[0])
			except Exception:
				return
			# fetch ticket_text
			ticket_text = ''
			try:
				if getattr(self, 'db', None) is not None:
					row = self.db.fetch_one('SELECT ticket_text FROM tickets WHERE id = ?', (tid,))
					if row and row[0]:
						ticket_text = row[0]
			except Exception:
				logging.exception('Error leyendo ticket_text desde BD (TicketsUI)')
			# ensure VisorNegro exists and show text
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
						self._visor_negro.set_text_color('#00FF00')
					except Exception:
						pass
					try:
						self._visor_negro.set_font_size(13)
					except Exception:
						pass
					try:
						self._visor_negro.set_text(ticket_text or '')
					except Exception:
						self._visor_negro.set_text(str(ticket_text))
					try:
						self._visor_negro.show()
					except Exception:
						pass
			except Exception:
				logging.exception('Error mostrando VisorNegro (TicketsUI)')
		except Exception:
			logging.exception('Error en _on_mostrar (TicketsUI)')

	def _on_buscar(self, event: object = None) -> None:
		"""Buscar tickets en toda la BD y renderizar resultados (limite 30)."""
		try:
			term = ''
			try:
				term = (getattr(self, 'search_entry', None).get() or '').strip()
			except Exception:
				term = ''
			if not term:
				# empty -> default behavior
				try:
					self._page_index = 0
				except Exception:
					pass
				self._load_and_render('')
				return
			# perform search across selected columns (checkboxes). If none selected -> all
			try:
				limit = int(getattr(self, 'ui_config', {}).get('page_size', 30))
			except Exception:
				limit = 30
			like = f"%{term}%"
			rows = []
			try:
				conds = []
				params = []
				# Determine which columns to search based on checkboxes (default: all if none)
				try:
					chk_ticket = bool(getattr(self, 'chk_ticket_var', tk.BooleanVar()).get())
				except Exception:
					chk_ticket = False
				try:
					chk_cliente = bool(getattr(self, 'chk_cliente_var', tk.BooleanVar()).get())
				except Exception:
					chk_cliente = False
				try:
					chk_cajero = bool(getattr(self, 'chk_cajero_var', tk.BooleanVar()).get())
				except Exception:
					chk_cajero = False
				try:
					chk_fecha = bool(getattr(self, 'chk_fecha_var', tk.BooleanVar()).get())
				except Exception:
					chk_fecha = False
				# If none explicitly selected, treat as all
				if not (chk_ticket or chk_cliente or chk_cajero or chk_fecha):
					chk_ticket = chk_cliente = chk_cajero = chk_fecha = True
				if chk_ticket:
					conds.append("CAST(num_ticket AS TEXT) LIKE ?")
					params.append(like)
				if chk_cliente:
					conds.append("cliente LIKE ?")
					params.append(like)
				if chk_cajero:
					conds.append("cajero LIKE ?")
					params.append(like)
				if chk_fecha:
					conds.append("created_at LIKE ?")
					params.append(like)
				where_clause = ' OR '.join(conds) if conds else '1=0'
				sql = f"SELECT id, created_at, total, cajero, cliente FROM tickets WHERE ({where_clause}) ORDER BY created_at DESC LIMIT ?"
				params.append(limit)
				rows = self.db.fetch_all(sql, tuple(params)) if getattr(self, 'db', None) is not None else []
			except Exception:
				logging.exception('Error ejecutando búsqueda en BD (TicketsUI)')
				rows = []
			items = []
			for r in rows or []:
				try:
					from datetime import datetime
					created = r[1]
					try:
						dt = datetime.fromisoformat(str(created))
						created_str = dt.strftime('%Y-%m-%d %H:%M:%S')
					except Exception:
						created_str = str(created)
					items.append({
						'id': r[0],
						'created_at': created_str,
						'total': f"{(float(r[2] or 0.0)):.2f}",
						'cajero': r[3] or '',
						'cliente': r[4] or '',
					})
				except Exception:
					logging.exception('Error normalizando fila resultado búsqueda (TicketsUI)')
			self._items = items
			try:
				self._render_items(self._items)
			except Exception:
				logging.exception('Error renderizando items tras búsqueda (TicketsUI)')
		except Exception:
			logging.exception('Error en _on_buscar (TicketsUI)')

	def _on_limpiar_busqueda(self, event: object = None) -> None:
		try:
			if getattr(self, 'search_entry', None) is not None:
				try:
					self.search_entry.delete(0, 'end')
				except Exception:
					try:
						self.search_entry.set('')
					except Exception:
						pass
			try:
				self._page_index = 0
			except Exception:
				pass
			try:
				self._load_and_render('')
			except Exception:
				logging.exception('Error recargando tickets tras limpiar búsqueda (TicketsUI)')
			try:
				if getattr(self, 'search_entry', None) is not None:
					self.search_entry.focus_set()
			except Exception:
				pass
		except Exception:
			logging.exception('Error en _on_limpiar_busqueda (TicketsUI)')

	def _on_row_double_click(self, event: object = None) -> None:
		"""Override double-click: mostrar ticket seleccionado en vez de confirmar selección."""
		try:
			self._on_mostrar(event)
		except Exception:
			logging.exception('Error en double click TicketsUI')

	def _render_clients_page(self):
		"""Override template pagination render to respect tickets columns and values."""
		try:
			tree = getattr(self, 'tree', None)
			if tree is None:
				return
			# clear
			for child in list(tree.get_children()):
				try:
					tree.delete(child)
				except Exception:
					pass
			start = getattr(self, '_current_page', 0) * getattr(self, '_page_size', 25)
			end = start + getattr(self, '_page_size', 25)
			page_items = (self._items or [])[start:end]
			for item in page_items:
				try:
					iid = str(item.get('id') or '')
					vals = tuple(item.get(col[0]) for col in self.columns_config)
					tree.insert('', 'end', iid=iid, values=vals)
				except Exception:
					logging.exception('Error insertando fila en _render_clients_page (TicketsUI)')
			# update pagination controls only when not in tickets mode
			try:
				if getattr(self, 'modo', None) == 'tickets':
					# Tickets UI uses self._page_index for navigation between closures;
					# do not override prev/next button states here.
					import math
					total_pages = max(1, math.ceil(len(self._items or []) / max(1, getattr(self, '_page_size', 25))))
					self.page_label.configure(text=f"Página {getattr(self,'_current_page',0)+1} / {total_pages}")
					return
				import math
				total_pages = max(1, math.ceil(len(self._items or []) / max(1, getattr(self, '_page_size', 25))))
				self.page_label.configure(text=f"Página {getattr(self,'_current_page',0)+1} / {total_pages}")
				self.prev_btn.configure(state=('normal' if getattr(self,'_current_page',0)>0 else 'disabled'))
				self.next_btn.configure(state=('normal' if getattr(self,'_current_page',0) < total_pages-1 else 'disabled'))
			except Exception:
				pass
		except Exception:
			logging.exception('Error renderizando página en TicketsUI')

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
					# Do NOT call show() here; the VisorNegro will be shown explicitly
					# by handlers or user actions (e.g. TicketsHandler.on_mostrar).
					# Focus search entry when overlay opens
					try:
						if getattr(self, 'search_entry', None) is not None:
							self.search_entry.focus_set()
					except Exception:
						pass
			except Exception:
				logging.exception('Error asegurando VisorNegro en show() (TicketsUI)')
		except Exception:
			logging.exception('Error mostrando TicketsUI')

	def _on_imprimir(self, event: object = None) -> None:
		"""Imprimir (simulado): mostrar diálogo de confirmación y imprimir en consola.
		- Requiere una única selección; si >1 muestra warning.
		- Muestra diálogo con botones 'OK' (activo) y 'Regalo' (deshabilitado).
		- Al confirmar, genera texto de ticket (ImpresoraService.generar_ticket_desde_id)
		  y lo imprime en la consola (simulación).
		"""
		tree = getattr(self, 'tree', None)
		if tree is None:
			return
		sel = list(tree.selection() or [])
		if not sel:
			return
		if len(sel) > 1:
			try:
				from kool_tpv.utils.custom_dialog import show_warning
				root = self.overlay.winfo_toplevel() if getattr(self, 'overlay', None) is not None else None
				show_warning(root, 'Selecciona únicamente un ticket', 'Selecciona únicamente un ticket')
			except Exception:
				logging.exception('Error mostrando warning seleccion multiple (Imprimir)')
			return
		# single selection
		try:
			tid = int(sel[0])
		except Exception:
			return
		# confirmation via custom dialog
		try:
			from kool_tpv.utils.custom_dialog import show_info
			root = self.overlay.winfo_toplevel() if getattr(self, 'overlay', None) is not None else None
			confirmed = bool(show_info(root, 'Imprimir ticket', f'Se imprimirá el ticket {tid}', confirm=True))
		except Exception:
			logging.exception('Error mostrando diálogo show_info (Imprimir)')
			return
		if not confirmed:
			return
		# perform printing (simulate)
		try:
			imp = ImpresoraService(db=self.db, imprimir_en_consola=True)
			texto = None
			try:
				texto = imp.generar_ticket_desde_id(tid)
			except Exception:
				logging.exception('Error generando ticket desde id (ImpresoraService)')
			if not texto:
				try:
					row = self.db.fetch_one('SELECT ticket_text FROM tickets WHERE id = ?', (tid,)) if getattr(self, 'db', None) is not None else None
					texto = row[0] if row and row[0] else None
				except Exception:
					logging.exception('Error leyendo ticket_text fallback para imprimir')
			if texto:
				print('\n' + '='*50)
				print(' SIMULACIÓN IMPRESIÓN TICKET ')
				print('='*50 + '\n')
				print(texto)
				print('\n' + '='*50 + '\n')
			else:
				logging.info('No se encontró texto para imprimir del ticket id=%s', tid)
		except Exception:
			logging.exception('Error en proceso de impresión (TicketsUI)')

