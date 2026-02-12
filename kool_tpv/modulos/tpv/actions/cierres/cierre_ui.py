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
            # Load tickets without cierre
            filters = {
                'tipos': bool(self.chk_tipos_var.get()) if hasattr(self, 'chk_tipos_var') else True,
                'categorias': bool(self.chk_cats_var.get()) if hasattr(self, 'chk_cats_var') else True,
                'productos': bool(self.chk_prods_var.get()) if hasattr(self, 'chk_prods_var') else True,
                'fidelizacion': bool(self.chk_fidel_var.get()) if hasattr(self, 'chk_fidel_var') else True,
            }
            items = self.controller.fetch_tickets_without_cierre(limit=1000, offset=0, filters=filters)
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
        # Placeholder: actual Cierre Z logic delegated to controller
        try:
            # Example flow: compute totals, insert cierre via CierreService, mark tickets
            logging.info('Cierre Z invoked (not yet implemented)')
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

            # Si se solicitó el detalle por productos, cargar y pasar al generador
            try:
                if getattr(self, 'chk_prods_var', None) and self.chk_prods_var.get():
                    qp = f"SELECT p.nombre, COUNT(DISTINCT tl.ticket_id) as tickets, COALESCE(SUM(tl.cantidad),0) as uds, COALESCE(SUM(tl.precio * tl.cantidad),0) as total FROM ticket_lines tl JOIN productos p ON p.id = tl.producto_id WHERE tl.ticket_id IN ({placeholders}) GROUP BY p.id ORDER BY total DESC LIMIT 50"
                    prod_rows = self.db.fetch_all(qp, tuple(ids))
                    if totals is None:
                        totals = {}
                    totals['productos'] = prod_rows
            except Exception:
                logging.exception('Error cargando detalle de productos en Mostrar')

            # Si se solicitó el detalle por categorías, cargar y pasar al generador
            try:
                if getattr(self, 'chk_cats_var', None) and self.chk_cats_var.get():
                    # Obtener: nombre categoria, tickets distintos, uds totales, total importe
                    qc = f"SELECT c.nombre, COUNT(DISTINCT tl.ticket_id) as tickets, COALESCE(SUM(tl.cantidad),0) as uds, COALESCE(SUM(tl.precio * tl.cantidad),0) as total FROM ticket_lines tl JOIN productos p ON p.id = tl.producto_id JOIN categorias c ON c.id = p.categoria WHERE tl.ticket_id IN ({placeholders}) GROUP BY c.id ORDER BY total DESC"
                    cat_rows = self.db.fetch_all(qc, tuple(ids))
                    if totals is None:
                        totals = {}
                    totals['categorias'] = cat_rows
            except Exception:
                logging.exception('Error cargando detalle de categorias en Mostrar')

            # Si se solicitó el detalle por tipos, cargar y pasar al generador
            try:
                if getattr(self, 'chk_tipos_var', None) and self.chk_tipos_var.get():
                    # Obtener: nombre tipo, tickets distintos, uds totales, total importe
                    qt = f"SELECT t.nombre, COUNT(DISTINCT tl.ticket_id) as tickets, COALESCE(SUM(tl.cantidad),0) as uds, COALESCE(SUM(tl.precio * tl.cantidad),0) as total FROM ticket_lines tl JOIN productos p ON p.id = tl.producto_id JOIN tipos t ON t.id = p.tipo WHERE tl.ticket_id IN ({placeholders}) GROUP BY t.id ORDER BY total DESC"
                    tipo_rows = self.db.fetch_all(qt, tuple(ids))
                    if totals is None:
                        totals = {}
                    totals['tipos'] = tipo_rows
            except Exception:
                logging.exception('Error cargando detalle de tipos en Mostrar')

            # Generar texto base con CierreTicketGenerator (pasando totals para desglose IVA)
            cfg = {'nombre_negocio': 'KOOL TPV', 'direccion': '', 'nif': '', 'pie_texto': ''}
            gen = CierreTicketGenerator()
            # usar id temporal para preview
            cierre_data['cierre_id'] = f"PREV-{int(datetime.now().timestamp())}"
            texto = gen.generate(cfg, cierre_data, tickets, totals=totals)

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

            # Tipos
            if getattr(self, 'chk_tipos_var', None) and self.chk_tipos_var.get():
                # Obtener: nombre tipo, tickets distintos, uds totales, total importe
                qt = f"SELECT t.nombre, COUNT(DISTINCT tl.ticket_id) as tickets, COALESCE(SUM(tl.cantidad),0) as uds, COALESCE(SUM(tl.precio * tl.cantidad),0) as total FROM ticket_lines tl JOIN productos p ON p.id = tl.producto_id JOIN tipos t ON t.id = p.tipo WHERE tl.ticket_id IN ({placeholders}) GROUP BY t.id ORDER BY total DESC"
                tipo_rows = self.db.fetch_all(qt, tuple(ids))
                if totals is None:
                    totals = {}
                totals['tipos'] = tipo_rows

            # (El detalle de productos se incorpora ahora a `totals` y lo renderiza el generador)

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
        self._load_and_render('')

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
