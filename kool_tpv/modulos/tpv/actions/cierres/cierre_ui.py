"""UI action para gestión de cierres de caja.

Usa `SelectionOverlayTemplate` como base y `SelectionOverlayVisor` para
mostrar/imprimir tickets. Implementación inicial: header con título y
botones solicitados; lista muestra tickets con `cierre_id IS NULL`.
"""
import logging
from typing import Optional

import customtkinter as ctk

from kool_tpv.utils.templates.template_selection_overlay import SelectionOverlayTemplate
from kool_tpv.utils.templates.selection_overlay_visor import SelectionOverlayVisor
from kool_tpv.modulos.tpv.actions.cierres.cierre_controller import CierreController
from kool_tpv.modulos.impresion.cierre_ticket_generator import CierreTicketGenerator
from kool_tpv.base_datos.cierre_service import CierreService
from datetime import datetime


class CierreUI(SelectionOverlayTemplate):
    def __init__(self, view_or_action_panel, db, on_selection_callback: Optional[callable] = None):
        ui_cfg = {
            'page_size': 25,
        }
        super().__init__(view_or_action_panel, db=db, on_selection_callback=on_selection_callback, ui_config=ui_cfg)

        self.db = db
        self.controller = CierreController(db)

        # Title
        self.title_text = "CIERRES"
        try:
            if hasattr(self, 'header_label') and self.header_label is not None:
                self.header_label.configure(text=self.title_text)
        except Exception:
            pass

        # Columns for tickets list (as requested)
        self.columns_config = [
            ("id", "ID ticket", 100, "center"),
            ("created_at", "Fecha ticket", 180, "center"),
            ("num_ventas", "Nº de ventas", 120, "center"),
            ("total", "Total €", 120, "e"),
        ]
        try:
            self._aplicar_config_columnas(self.columns_config)
        except Exception:
            logging.exception('Error aplicando columnas en CierreUI')

        # Instantiate visor helper
        try:
            self.visor_helper = SelectionOverlayVisor(self)
        except Exception:
            logging.exception('Error instanciando SelectionOverlayVisor en CierreUI')

        # Note: do not call `configure_vis_mode` here — keep title as 'CIERRES'

        # Remove search box under title for Cierres (no search entry visible)
        try:
            if hasattr(self, 'search_entry') and self.search_entry is not None:
                try:
                    self.search_entry.pack_forget()
                except Exception:
                    pass
            if hasattr(self, 'search_controls_frame') and self.search_controls_frame is not None:
                try:
                    self.search_controls_frame.pack_forget()
                except Exception:
                    pass
        except Exception:
            logging.exception('Error ocultando search entry en CierreUI')

        # Add header controls requested: Tickets Cierre, Histórico, Cierre Z and checkboxes
        self._add_header_controls()

        # Load initial items (tickets sin cierre)
        self._items = []
        self._load_and_render('')

    def _add_header_controls(self):
        try:
            # Create a dedicated header area under the title for two rows:
            # first row: buttons; second row: checkboxes
            try:
                # ensure top_buttons exists (from template)
                container = getattr(self, 'top_buttons', None) or getattr(self, 'overlay', None)
                self._header_buttons_row = ctk.CTkFrame(self.top_buttons if hasattr(self, 'top_buttons') else container, fg_color='transparent')
                self._header_buttons_row.pack(side='top', fill='x', pady=(6, 4))

                self.tickets_cierre_btn = ctk.CTkButton(self._header_buttons_row, text="Tickets Cierre", width=140, command=self._on_refresh)
                self.historico_btn = ctk.CTkButton(self._header_buttons_row, text="Histórico", width=140, command=self._on_historico)
                self.cierre_z_btn = ctk.CTkButton(self._header_buttons_row, text="Cierre Z", width=140, fg_color='#FF4444', text_color='black', command=self._on_cierre_z)
                # Mostrar button (blanco fondo, texto negro) a la derecha de Cierre Z
                self.mostrar_btn = ctk.CTkButton(self._header_buttons_row, text="Mostrar", width=140, fg_color='#FFFFFF', text_color='black', command=self._on_mostrar)
                self.tickets_cierre_btn.pack(side="left", padx=5)
                self.historico_btn.pack(side="left", padx=5)
                self.cierre_z_btn.pack(side="left", padx=5)
                self.mostrar_btn.pack(side="left", padx=5)
            except Exception:
                logging.exception('Error creando header buttons en CierreUI')

            # Second row: checkboxes
            try:
                self._header_checks_row = ctk.CTkFrame(self.top_buttons if hasattr(self, 'top_buttons') else container, fg_color="transparent")
                self._header_checks_row.pack(side='top', fill='x', pady=(2, 6))
                self.chk_tipos_var = ctk.BooleanVar(value=False)
                self.chk_cats_var = ctk.BooleanVar(value=False)
                self.chk_prods_var = ctk.BooleanVar(value=False)
                self.chk_fidel_var = ctk.BooleanVar(value=False)
                self.chk_tipos = ctk.CTkCheckBox(self._header_checks_row, text="Tipos", variable=self.chk_tipos_var, command=self._on_filter_change)
                self.chk_cats = ctk.CTkCheckBox(self._header_checks_row, text="Categorías", variable=self.chk_cats_var, command=self._on_filter_change)
                self.chk_prods = ctk.CTkCheckBox(self._header_checks_row, text="Productos", variable=self.chk_prods_var, command=self._on_filter_change)
                self.chk_fidel = ctk.CTkCheckBox(self._header_checks_row, text="Fidelización", variable=self.chk_fidel_var, command=self._on_filter_change)
                self.chk_tipos.pack(side="left", padx=6)
                self.chk_cats.pack(side="left", padx=6)
                self.chk_prods.pack(side="left", padx=6)
                self.chk_fidel.pack(side="left", padx=6)
            except Exception:
                logging.exception('Error creando checkboxes en CierreUI')
        except Exception:
            logging.exception('Error añadiendo controles al header en CierreUI')

    def _load_and_render(self, termino: str = ''):
        try:
            # Load tickets without cierre (always show all pending tickets).
            items = self.controller.fetch_tickets_without_cierre(limit=1000, offset=0)
            # Prefer visor helper to render items directly (no search entry)
            try:
                if getattr(self, 'visor_helper', None) is not None:
                    self.visor_helper.render_items(items)
                else:
                    self._items = items
                    self._current_page = 0
                    self._render_clients_page()
            except Exception:
                logging.exception('Error usando visor_helper para render_items en CierreUI')
        except Exception:
            logging.exception('Error _load_and_render en CierreUI')

    def _on_refresh(self):
        self._load_and_render('')

    def _on_historico(self):
        # Placeholder: open cierre_historico_ui (to be implemented)
        try:
            from .cierre_historico_ui import CierreHistoricoUI
            ui = CierreHistoricoUI(self.action_panel if hasattr(self, 'action_panel') else self.view, self.db)
            ui.show()
        except Exception:
            logging.exception('Error abriendo cierre_historico_ui')

    def _on_cierre_z(self):
        try:
            sel = list(self.tree.selection() or [])
            if not sel:
                logging.info('No hay tickets seleccionados para Cierre Z')
                return
            try:
                ids = [int(i) for i in sel]
            except Exception:
                logging.info('IDs seleccionados inválidos para Cierre Z')
                return

            # Confirm dialog using custom_dialog.show_info (OK/Cancelar)
            try:
                from kool_tpv.utils.custom_dialog import show_info
                root = self.overlay.winfo_toplevel() if hasattr(self, 'overlay') else None
                prompt = '¿Quieres realizar el cierre del día? (Se imprimirá Ticket de cierre)'
                # show_info returns True if accepted, False if cancelled
                answer = show_info(root, 'Confirmar Cierre', prompt, confirm=True)
            except Exception:
                logging.exception('Error mostrando diálogo de confirmación con show_info; asumiendo OK')
                answer = True

            if not answer:
                logging.info('Usuario canceló Cierre Z')
                return

            # Build full snapshot (always include productos, categorias, tipos, fidelizacion)
            try:
                # load tickets rows
                placeholders = ','.join(['?'] * len(ids))
                q = f"SELECT id, num_ventas, total, importe_efectivo, importe_tarjeta, forma_pago, descuento_euros, cajero, created_at FROM tickets WHERE id IN ({placeholders})"
                rows = self.db.fetch_all(q, tuple(ids))
                tickets = []
                for r in rows:
                    tickets.append({
                        'id': r[0],
                        'num_ventas': int(r[1] or 0),
                        'total': float(r[2] or 0.0),
                        'importe_efectivo': float(r[3] or 0.0),
                        'importe_tarjeta': float(r[4] or 0.0),
                        'forma_pago': r[5],
                        'descuento_euros': float(r[6] or 0.0),
                        'cajero': r[7],
                        'created_at': r[8],
                    })
            except Exception:
                logging.exception('Error cargando tickets para Cierre Z')
                tickets = []

            # compute totals (IVA etc)
            cierre_svc = CierreService(self.db)
            totals = cierre_svc.compute_totals_for_ticket_ids(ids)

            # products
            try:
                qp = f"SELECT p.nombre, COUNT(DISTINCT tl.ticket_id) as tickets, COALESCE(SUM(tl.cantidad),0) as uds, COALESCE(SUM(tl.precio * tl.cantidad),0) as total FROM ticket_lines tl JOIN productos p ON p.id = tl.producto_id WHERE tl.ticket_id IN ({placeholders}) GROUP BY p.id ORDER BY total DESC LIMIT 500"
                prod_rows = self.db.fetch_all(qp, tuple(ids))
                if totals is None:
                    totals = {}
                totals['productos'] = prod_rows
            except Exception:
                logging.exception('Error cargando productos para snapshot')

            # categorias
            try:
                qc = f"SELECT c.nombre, COUNT(DISTINCT tl.ticket_id) as tickets, COALESCE(SUM(tl.cantidad),0) as uds, COALESCE(SUM(tl.precio * tl.cantidad),0) as total FROM ticket_lines tl JOIN productos p ON p.id = tl.producto_id JOIN categorias c ON c.id = p.categoria WHERE tl.ticket_id IN ({placeholders}) GROUP BY c.id ORDER BY total DESC"
                cat_rows = self.db.fetch_all(qc, tuple(ids))
                totals['categorias'] = cat_rows
            except Exception:
                logging.exception('Error cargando categorias para snapshot')

            # tipos
            try:
                qt = f"SELECT t.nombre, COUNT(DISTINCT tl.ticket_id) as tickets, COALESCE(SUM(tl.cantidad),0) as uds, COALESCE(SUM(tl.precio * tl.cantidad),0) as total FROM ticket_lines tl JOIN productos p ON p.id = tl.producto_id JOIN tipos t ON t.id = p.tipo WHERE tl.ticket_id IN ({placeholders}) GROUP BY t.id ORDER BY total DESC"
                tipo_rows = self.db.fetch_all(qt, tuple(ids))
                totals['tipos'] = tipo_rows
            except Exception:
                logging.exception('Error cargando tipos para snapshot')

            # fidelizacion (detailed: sums and ticket counts)
            try:
                qf = f"SELECT COALESCE(SUM(CASE WHEN puntos>0 THEN puntos ELSE 0 END),0) AS otorgado_sum, COALESCE(SUM(CASE WHEN puntos<0 THEN -puntos ELSE 0 END),0) AS gastado_sum, COALESCE(COUNT(DISTINCT CASE WHEN puntos>0 THEN ticket_id END),0) AS otorgado_tickets, COALESCE(COUNT(DISTINCT CASE WHEN puntos<0 THEN ticket_id END),0) AS gastado_tickets FROM points_movements WHERE ticket_id IN ({placeholders})"
                row = self.db.fetch_one(qf, tuple(ids))
                otorgado_sum = float(row[0] or 0)
                gastado_sum = float(row[1] or 0)
                otorgado_tickets = int(row[2] or 0)
                gastado_tickets = int(row[3] or 0)
            except Exception:
                logging.exception('Error cargando fidelizacion para snapshot')
                otorgado_sum = gastado_sum = 0.0
                otorgado_tickets = gastado_tickets = 0

            # Build snapshot text (full) using generator and appending fidelizacion block
            try:
                cfg = {'nombre_negocio': 'KOOL TPV', 'direccion': '', 'nif': '', 'pie_texto': ''}
                gen = CierreTicketGenerator()
                cierre_data = {
                    'fecha': datetime.now().strftime('%d/%m/%Y'),
                    'hora': datetime.now().strftime('%H:%M'),
                    'usuario': tickets[0].get('cajero') if tickets else '',
                    'cierre_id': ''
                }
                cierre_data['cierre_id'] = f"Z-PREV-{int(datetime.now().timestamp())}"
                # Defensive: ensure `tickets` is a list of dicts as the generator expects
                try:
                    if tickets and not isinstance(tickets[0], dict):
                        normalized = []
                        for r in tickets:
                            try:
                                normalized.append({
                                    'id': r[0],
                                    'num_ventas': int(r[1] or 0),
                                    'total': float(r[2] or 0.0),
                                    'importe_efectivo': float(r[3] or 0.0),
                                    'importe_tarjeta': float(r[4] or 0.0),
                                    'forma_pago': r[5],
                                    'descuento_euros': float(r[6] or 0.0),
                                    'cajero': r[7],
                                    'created_at': r[8],
                                })
                            except Exception:
                                # Best-effort fallback for unexpected row shape
                                try:
                                    normalized.append({'id': int(r[0])})
                                except Exception:
                                    normalized.append({'id': None})
                        tickets = normalized
                except Exception:
                    pass
                snapshot = gen.generate(cfg, cierre_data, tickets, totals=totals)
                # append fidelizacion block (always included in snapshot)
                try:
                    tmp = CierreTicketGenerator()
                    block = []
                    block.append(tmp.DOUBLE_DIVIDER)
                    block.append('TESORO (Fidelización)'.center(tmp.WIDTH))
                    block.append(tmp.DIVIDER)
                    block.append(f"Tesoro otorgado: {otorgado_tickets} tickets ({tmp._format_currency(otorgado_sum)})")
                    block.append(f"Tesoro gastado: {gastado_tickets} tickets ({tmp._format_currency(gastado_sum)})")
                    block.append(tmp.DOUBLE_DIVIDER)
                    snapshot = snapshot + '\n' + '\n'.join(block)
                except Exception:
                    pass
            except Exception:
                logging.exception('Error generando snapshot de cierre')
                snapshot = f"Cierre snapshot - tickets: {len(ids)}"

            # Persistir cierre atómico con snapshot_text
            try:
                # intentar obtener usuario_id (cajero) desde DB wrapper si está disponible
                usuario_id = None
                try:
                    getter = getattr(self.db, 'get_active_cashier', None)
                    if callable(getter):
                        active = getter()
                        if isinstance(active, dict):
                            usuario_id = active.get('id') or active.get('usuario_id') or active.get('cajero_id')
                        elif isinstance(active, int):
                            usuario_id = active
                except Exception:
                    usuario_id = None

                cierre_id = cierre_svc.create_cierre_atomic(ids, usuario_id, tickets[0].get('cajero') if tickets else None, cierre_text=snapshot)
                if cierre_id is None:
                    logging.error('Fallo al crear cierre atómico')
                    return
            except Exception:
                logging.exception('Error llamando create_cierre_atomic')
                return

            # Imprimir snapshot (terminal / impresora) - por ahora imprimir en stdout
            try:
                print(snapshot)
            except Exception:
                logging.exception('Error imprimiendo snapshot en terminal')

            # Limpiar VisorNegro tras impresión
            try:
                if getattr(self, '_visor_negro', None):
                    try:
                        self._visor_negro.set_text('')
                        self._visor_negro.hide()
                    except Exception:
                        pass
            except Exception:
                logging.exception('Error limpiando VisorNegro tras impresión')

            # Recargar lista de tickets disponibles para cerrar
            try:
                self._load_and_render('')
            except Exception:
                logging.exception('Error recargando UI tras Cierre Z')

        except Exception:
            logging.exception('Error en _on_cierre_z')

    def _on_mostrar(self):
        """Mostrar el ticket seleccionado en el VisorNegro (si existe)."""
        try:
            sel = list(self.tree.selection() or [])
            if not sel:
                logging.info('No hay tickets seleccionados para Mostrar')
                return

            # convertir a enteros
            try:
                ids = [int(i) for i in sel]
            except Exception:
                ids = []
            if not ids:
                logging.info('IDs seleccionados inválidos')
                return

            # Cargar tickets básicos desde BD
            placeholders = ','.join(['?'] * len(ids))
            q = f"SELECT id, num_ventas, total, importe_efectivo, importe_tarjeta, forma_pago, descuento_euros, cajero, created_at FROM tickets WHERE id IN ({placeholders})"
            rows = self.db.fetch_all(q, tuple(ids))
            tickets = []
            for r in rows:
                tickets.append({
                    'id': r[0],
                    'num_ventas': int(r[1] or 0),
                    'total': float(r[2] or 0.0),
                    'importe_efectivo': float(r[3] or 0.0),
                    'importe_tarjeta': float(r[4] or 0.0),
                    'forma_pago': r[5],
                    'descuento_euros': float(r[6] or 0.0),
                    'cajero': r[7],
                    'created_at': r[8],
                })

            # generar datos de cierre básicos
            cierre_data = {
                'fecha': datetime.now().strftime('%d/%m/%Y'),
                'hora': datetime.now().strftime('%H:%M'),
                'usuario': tickets[0].get('cajero') if tickets else '',
                'cierre_id': '',
            }

            # Calcular totales y desglose IVA (sin crear cierre en BD)
            try:
                cierre_svc = CierreService(self.db)
                totals = cierre_svc.compute_totals_for_ticket_ids(ids)
            except Exception:
                totals = None

            # Cargar totales básicos (IVA, formas de pago, etc.)
            # Los detalles por productos/categorías/tipos se cargan solo
            # si el usuario tiene marcados los checkboxes (más abajo).

            # Preparar configuración para generar texto (se generará tras cargar detalles condicionales)
            cfg = {'nombre_negocio': 'KOOL TPV', 'direccion': '', 'nif': '', 'pie_texto': ''}
            gen = CierreTicketGenerator()
            cierre_data['cierre_id'] = f"PREV-{int(datetime.now().timestamp())}"

            # Añadir extras según checkboxes
            extras = []
            # Fidelización
            if getattr(self, 'chk_fidel_var', None) and self.chk_fidel_var.get():
                try:
                    # Obtener sumas y recuento de tickets que otorgaron/gastaron puntos
                    qf = f"SELECT COALESCE(SUM(CASE WHEN puntos>0 THEN puntos ELSE 0 END),0) AS otorgado_sum, COALESCE(SUM(CASE WHEN puntos<0 THEN -puntos ELSE 0 END),0) AS gastado_sum, COALESCE(COUNT(DISTINCT CASE WHEN puntos>0 THEN ticket_id END),0) AS otorgado_tickets, COALESCE(COUNT(DISTINCT CASE WHEN puntos<0 THEN ticket_id END),0) AS gastado_tickets FROM points_movements WHERE ticket_id IN ({placeholders})"
                    row = self.db.fetch_one(qf, tuple(ids))
                    otorgado_sum = float(row[0] or 0)
                    gastado_sum = float(row[1] or 0)
                    otorgado_tickets = int(row[2] or 0)
                    gastado_tickets = int(row[3] or 0)
                except Exception:
                    logging.exception('Error consultando fidelizacion en Mostrar')
                    otorgado_sum = 0.0
                    gastado_sum = 0.0
                    otorgado_tickets = 0
                    gastado_tickets = 0

                # Formatear bloque de TESORO usando divisores del generador para mantener estilo
                try:
                    gen_tmp = CierreTicketGenerator()
                    block = []
                    block.append(gen_tmp.DOUBLE_DIVIDER)
                    block.append('TESORO (Fidelización)'.center(gen_tmp.WIDTH))
                    block.append(gen_tmp.DIVIDER)
                    line_ot = f"Tesoro otorgado: {otorgado_tickets} tickets ({gen_tmp._format_currency(otorgado_sum)})"
                    line_ga = f"Tesoro gastado: {gastado_tickets} tickets ({gen_tmp._format_currency(gastado_sum)})"
                    block.append(line_ot)
                    block.append(line_ga)
                    block.append(gen_tmp.DOUBLE_DIVIDER)
                    extras.append('\n' + '\n'.join(block))
                except Exception:
                    # Fallback simple
                    extras.append('\nTESORO:')
                    extras.append(f'Tesoro otorgado: {otorgado_tickets} ({otorgado_sum})')
                    extras.append(f'Tesoro gastado: {gastado_tickets} ({gastado_sum})')

            # Categorías
            if getattr(self, 'chk_cats_var', None) and self.chk_cats_var.get():
                # Obtener: nombre categoria, tickets distintos, uds totales, total importe
                qc = f"SELECT c.nombre, COUNT(DISTINCT tl.ticket_id) as tickets, COALESCE(SUM(tl.cantidad),0) as uds, COALESCE(SUM(tl.precio * tl.cantidad),0) as total FROM ticket_lines tl JOIN productos p ON p.id = tl.producto_id JOIN categorias c ON c.id = p.categoria WHERE tl.ticket_id IN ({placeholders}) GROUP BY c.id ORDER BY total DESC"
                cat_rows = self.db.fetch_all(qc, tuple(ids))
                if totals is None:
                    totals = {}
                totals['categorias'] = cat_rows

            # Productos
            if getattr(self, 'chk_prods_var', None) and self.chk_prods_var.get():
                try:
                    qp = f"SELECT p.nombre, COUNT(DISTINCT tl.ticket_id) as tickets, COALESCE(SUM(tl.cantidad),0) as uds, COALESCE(SUM(tl.precio * tl.cantidad),0) as total FROM ticket_lines tl JOIN productos p ON p.id = tl.producto_id WHERE tl.ticket_id IN ({placeholders}) GROUP BY p.id ORDER BY total DESC LIMIT 50"
                    prod_rows = self.db.fetch_all(qp, tuple(ids))
                    if totals is None:
                        totals = {}
                    totals['productos'] = prod_rows
                except Exception:
                    logging.exception('Error cargando detalle de productos en Mostrar')

            # Tipos
            if getattr(self, 'chk_tipos_var', None) and self.chk_tipos_var.get():
                # Obtener: nombre tipo, tickets distintos, uds totales, total importe
                qt = f"SELECT t.nombre, COUNT(DISTINCT tl.ticket_id) as tickets, COALESCE(SUM(tl.cantidad),0) as uds, COALESCE(SUM(tl.precio * tl.cantidad),0) as total FROM ticket_lines tl JOIN productos p ON p.id = tl.producto_id JOIN tipos t ON t.id = p.tipo WHERE tl.ticket_id IN ({placeholders}) GROUP BY t.id ORDER BY total DESC"
                tipo_rows = self.db.fetch_all(qt, tuple(ids))
                if totals is None:
                    totals = {}
                totals['tipos'] = tipo_rows

            # (El detalle de productos/categorías/tipos se incorpora a `totals` cuando esté seleccionado)
            # Generar texto base ahora que `totals` contiene los detalles solicitados
            try:
                # Defensive: ensure `tickets` entries are dict-like for the generator
                try:
                    if tickets and not isinstance(tickets[0], dict):
                        normalized = []
                        for r in tickets:
                            try:
                                normalized.append({
                                    'id': r[0],
                                    'num_ventas': int(r[1] or 0),
                                    'total': float(r[2] or 0.0),
                                    'importe_efectivo': float(r[3] or 0.0),
                                    'importe_tarjeta': float(r[4] or 0.0),
                                    'forma_pago': r[5],
                                    'descuento_euros': float(r[6] or 0.0),
                                    'cajero': r[7],
                                    'created_at': r[8],
                                })
                            except Exception:
                                try:
                                    normalized.append({'id': int(r[0])})
                                except Exception:
                                    normalized.append({'id': None})
                        tickets = normalized
                except Exception:
                    pass
                texto = gen.generate(cfg, cierre_data, tickets, totals=totals)
            except Exception:
                logging.exception('Error generando texto de preview con CierreTicketGenerator')

            # Combinar texto y extras
            if extras:
                texto = texto + '\n' + '\n'.join(extras)

            # Mostrar en VisorNegro (intento crear visor; fallback a self.overlay si no hay view.cart_view)
            try:
                view = getattr(self, 'view', None)
                parent_widget = None
                if view is not None and getattr(view, 'cart_view', None) is not None:
                    parent_widget = view.cart_view
                    logging.info('Usando view.cart_view como parent para VisorNegro')
                else:
                    # fallback: usar el overlay del propio template
                    if getattr(self, 'overlay', None) is not None:
                        parent_widget = self.overlay
                        logging.info('Usando self.overlay como parent para VisorNegro (fallback)')
                    else:
                        logging.warning('No se encontró parent para VisorNegro (ni view.cart_view ni self.overlay)')

                if parent_widget is not None:
                    if getattr(self, '_visor_negro', None) is None:
                        from kool_tpv.modulos.tpv.ui.visor_negro import VisorNegro
                        try:
                            self._visor_negro = VisorNegro(parent_widget)
                        except Exception:
                            logging.exception('Error instanciando VisorNegro en Mostrar')
                    try:
                        logging.info('Seteando texto en VisorNegro (len=%d)', len(texto) if texto else 0)
                        try:
                            self._visor_negro.set_text_color('#00FF00')
                        except Exception:
                            pass
                        try:
                            self._visor_negro.set_text(texto)
                        except Exception:
                            self._visor_negro.set_text(str(texto))
                        try:
                            self._visor_negro.show()
                        except Exception:
                            pass
                    except Exception:
                        logging.exception('Error manipulando VisorNegro desde Mostrar')
            except Exception:
                logging.exception('Error mostrando texto en VisorNegro desde Mostrar')

        except Exception:
            logging.exception('Error en _on_mostrar')

    def _on_filter_change(self):
        # Checkboxes only affect report detail; do not reload the tickets list here.
        return

    def show(self):
        """Mostrar overlay y asegurar que el VisorNegro esté activo sin cambiar el título."""
        try:
            try:
                super().show()
            except Exception:
                logging.exception('Error mostrando CierreUI via super().show()')

            # Activar modo visor (VisorNegro) para CIERRES
            try:
                if getattr(self, 'visor_helper', None) is not None:
                    try:
                        self.visor_helper.configure_vis_mode()
                    except Exception:
                        logging.exception('Error configurando modo visor en CierreUI')
            except Exception:
                logging.exception('Error invocando visor_helper en CierreUI.show')

            # Restaurar el título específico de CIERRES (configure_vis_mode puede cambiarlo)
            try:
                self.title_text = "CIERRES"
                if hasattr(self, 'header_label') and self.header_label is not None:
                    try:
                        self.header_label.configure(text=self.title_text)
                    except Exception:
                        pass
            except Exception:
                pass
        except Exception:
            logging.exception('Error en CierreUI.show()')

    def hide(self) -> None:
        """Oculta el overlay y asegura que el VisorNegro quede desactivado.

        Limpia el texto del visor y lo oculta si existe, luego delega
        en la implementación base para ocultar el overlay.
        """
        try:
            if getattr(self, '_visor_negro', None):
                try:
                    self._visor_negro.set_text('')
                except Exception:
                    pass
                try:
                    self._visor_negro.hide()
                except Exception:
                    pass
        except Exception:
            logging.exception('Error limpiando VisorNegro en CierreUI.hide')

        try:
            super().hide()
        except Exception:
            logging.exception('Error llamando SelectionOverlayTemplate.hide en CierreUI.hide')
