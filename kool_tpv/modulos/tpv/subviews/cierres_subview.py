from customtkinter import CTkFrame
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class CierresSubView(CTkFrame):

    def __init__(self, parent, db, view=None):
        super().__init__(parent)

        self.db = db
        self.view = view

        # In-memory cache for generated tickets (ticket_id -> content)
        self._ticket_cache = {}

        # Header (top, spans both columns)
        self.header_frame = CTkFrame(self)
        self.header_frame.grid(row=0, column=0, columnspan=2, sticky='ew', padx=20, pady=10)

        from kool_tpv.utils.factories.button_factory import ButtonFactory

        # 1. Botón para generar cierre (Cierre X)
        self.btn_generar_cierre = ButtonFactory.create_button(
            parent=self.header_frame,
            text="CIERRE Z",
            style_key="mini_action",
            command=self._show_pending_tickets,
            width=100
        )
        self.btn_generar_cierre.pack(side="left", padx=10)

        # 2. Date pickers para filtrar rango (desde / hasta)
        try:
            from kool_tpv.utils.widgets.date_picker_entry import DatePickerEntry
            self.date_from = DatePickerEntry(self.header_frame, module_name='cierres', width=90, allow_future=False, default_mode='first_day_of_month', command=lambda d=None: self._on_date_change())
            self.date_from.pack(side="left", padx=(10, 4))
            
            from customtkinter import CTkLabel
            self._date_range_label = CTkLabel(self.header_frame, text='a')
            self._date_range_label.pack(side='left')
            
            self.date_to = DatePickerEntry(self.header_frame, module_name='cierres', width=90, allow_future=False, default_mode='today', command=lambda d=None: self._on_date_change())
            self.date_to.pack(side="left", padx=(4, 6))
        except Exception:
            logger.exception("Error creando DatePickers en cierres")
            self.date_from = None
            self.date_to = None

        # 3. Buscador (espera Enter)
        from customtkinter import CTkEntry
        self.search_entry = CTkEntry(
            self.header_frame,
            placeholder_text="Introduce cajero o nº para filtrar cierres",
            width=350,
        )
        self.search_entry.pack(side="left", padx=10)
        
        # Bind Enter on search entry
        self.search_entry.bind("<Return>", lambda e: self.search_list.set_search_text(self.search_entry.get()))
        self.search_entry.bind("<KP_Enter>", lambda e: self.search_list.set_search_text(self.search_entry.get()))

        # 4. Botón Imprimir (a la derecha)
        self.btn_imprimir = ButtonFactory.create_button(
            parent=self.header_frame,
            text="IMPRIMIR",
            style_key="mini_outline_clientes",
            command=self._on_imprimir_cierre
        )
        self.btn_imprimir.pack(side="right", padx=10)

        # Content area: left = list, right = ticket display
        self.list_frame = CTkFrame(self)
        self.list_frame.grid(row=1, column=0, sticky='nsew', padx=(20, 6), pady=10)

        # We don't instantiate a local TicketDisplay here; the controller
        # provides a global overlayvisor so the NavList can use the full width.
        try:
            self.grid_columnconfigure(0, weight=1)
            self.grid_rowconfigure(1, weight=1)
        except Exception:
            pass

        # Service for cierres
        try:
            from kool_tpv.base_datos.cierre_service import CierreService
            self.service = CierreService(self.db)
        except Exception:
            self.service = None

        # Keyboard manager
        root = self.winfo_toplevel()
        from kool_tpv.utils.keyboard_manager import KeyboardManager

        if not hasattr(root, "keyboard_manager") or root.keyboard_manager is None:
            root.keyboard_manager = KeyboardManager(root)

        self.keyboard_manager = root.keyboard_manager

        # NOTE: Power handler registration removed from __init__
        # TpvView already handles power button for subviews via pop_subview()
        # No need for individual subviews to register their own handlers

        columns = [
            ("cierre_num", 80, "Nº"),
            ("created_at", 180, "Fecha / Hora"),
            ("total_ingresos", 120, "Total"),
            ("num_ventas", 80, "Ventas"),
            ("cajero", 140, "Cajero"),
            ("printed", 80, "Impreso"),
        ]

        from kool_tpv.utils.widgets.searchable_paginated_navlist import SearchablePaginatedNavList

        # layout config (optional)
        try:
            from kool_tpv.utils.config_loader import load_layout_config
            layout_config = load_layout_config()
        except Exception:
            layout_config = None

        self.search_list = SearchablePaginatedNavList(
            parent=self.list_frame,
            columns=columns,
            search_function=self._buscar_cierres,
            map_function=self._map_cierre,
            module_name="tpv",
            page_limit=50,
            on_double_click=None,
            keyboard_manager=self.keyboard_manager,
            layout_config=layout_config,
        )

        try:
            if getattr(self, 'keyboard_manager', None) and getattr(self.search_list, 'nav_list', None):
                self.keyboard_manager.set_active_list(self.search_list.nav_list)
        except Exception:
            pass

        self.search_list.pack(fill="both", expand=True)

        # Connect NavList selection to visor handler
        try:
            nav = getattr(self.search_list, 'nav_list', None)
            if nav is not None:
                nav.on_select_callback = self._on_nav_select
        except Exception:
            logger.exception('Error conectando on_select del nav_list')

        # No search entry to bind for cierres

    def _buscar_cierres(self, texto):
        try:
            if not self.service:
                return []
            
            # Obtener fechas desde los pickers
            fecha_from = self.date_from.get() if self.date_from else None
            fecha_to = self.date_to.get() if self.date_to else None
            
            # Llamar al servicio profesional con los filtros
            return self.service.listar_cierres(
                termino=texto or '',
                fecha_from=fecha_from,
                fecha_to=fecha_to,
                limit=1000, 
                offset=0
            )
        except Exception:
            logger.exception('Error buscando cierres')
            return []

    def _on_date_change(self):
        """Refrescar lista al cambiar fechas."""
        try:
            self.search_list.set_search_text(self.search_entry.get())
        except Exception:
            pass

    def _on_imprimir_cierre(self):
        """Imprimir el cierre seleccionado."""
        try:
            nav = getattr(self.search_list, 'nav_list', None)
            if nav is None: return
            
            sel = nav.get_selected_data()
            if not sel:
                from kool_tpv.utils.widgets.notificaciones import show_warning
                show_warning(self.winfo_toplevel(), 'Selecciona un cierre para imprimir')
                return
            
            cierre_id = sel.get('cierre_id') or sel.get('id')
            if not cierre_id: return

            from kool_tpv.utils.custom_dialog import show_info
            show_info(
                self.winfo_toplevel(),
                'Imprimir cierre',
                f'Se imprimirá el cierre nº {sel.get("cierre_num")}. Continuar?',
                confirm=True,
                callback=lambda: self._ejecutar_impresion_cierre(cierre_id)
            )
        except Exception:
            logger.exception('Error en _on_imprimir_cierre')

    def _ejecutar_impresion_cierre(self, cierre_id):
        try:
            if not self.view or not self.view.controller: return
            
            # Usar el controller para generar el texto del cierre
            from kool_tpv.modulos.impresion.impresora_service import ImpresoraService
            imp = ImpresoraService(db=self.db)
            texto = imp.generar_cierre_desde_id(cierre_id)
            
            if texto:
                # Usar la rutina de impresión común
                imp._imprimir_texto_generico(texto, {'num_ticket': f"CIERRE_{cierre_id}"})
                from kool_tpv.utils.widgets.notificaciones import ToastWidget
                ToastWidget.show(self.winfo_toplevel(), f'Cierre {cierre_id} enviado a imprimir', tipo='success')
        except Exception:
            logger.exception('Error imprimiendo cierre')

    def _map_cierre(self, detalle):
        try:
            created = detalle.get('created_at')
            created_str = created
            try:
                from kool_tpv.utils.time_utils import utc_str_to_local_str
                if created:
                    created_str = utc_str_to_local_str(created, out_fmt='%d/%m/%Y %H:%M')
            except Exception:
                try:
                    if isinstance(created, datetime):
                        created_str = created.strftime('%d/%m/%Y %H:%M')
                except Exception:
                    created_str = str(created)

            total = detalle.get('total_ingresos')
            try:
                from kool_tpv.base_datos.money_adapter import read_from_db
                total_decimal = read_from_db(int(total))
                total_str = f"{total_decimal:.2f}"
            except Exception:
                total_str = str(total)

            printed = detalle.get('printed')
            printed_str = 'Sí' if printed else 'No'

            return {
                'id': detalle.get('id'),
                'cierre_id': detalle.get('id'),
                'cierre_num': detalle.get('cierre_num'),
                'created_at': created_str,
                'total_ingresos': total_str,
                'num_ventas': detalle.get('num_ventas') or 0,
                'cajero': detalle.get('cajero') or '',
                'printed': printed_str,
            }
        except Exception:
            logger.exception('Error mapeando cierre')
            return {}

    def _on_nav_select(self, data):
        try:
            cierre_id = None
            if isinstance(data, dict):
                cierre_id = data.get('cierre_id') or data.get('id')
            if not cierre_id:
                return
            try:
                if getattr(self, 'view', None) and getattr(self.view, 'controller', None):
                    try:
                        if hasattr(self.view.controller, 'show_cierre'):
                            self.view.controller.show_cierre(cierre_id)
                            return
                    except Exception:
                        logger.exception('Error pidiendo visor de cierre al controller')
            except Exception:
                logger.exception('Error delegando show_cierre al controller')

        except Exception:
            logger.exception('Error en _on_nav_select (cierres)')

    # NOTE: _handle_power removed - TpvView handles power button via pop_subview()
    # Individual subviews don't need their own power handlers
        return False

    def _on_cerrar(self):
        try:
            # Confirmación
            try:
                from kool_tpv.utils.custom_dialog import show_info
                root = self.winfo_toplevel()
                confirmed = bool(show_info(root, 'Cerrar caja', 'Se generará un cierre con los tickets pendientes. Continuar?', confirm=True))
            except Exception:
                confirmed = True

            if not confirmed:
                return

            # Ejecutar processor
            try:
                from kool_tpv.modulos.ticket.cierre_caja_processor import CierreCajaProcessor
                proc = CierreCajaProcessor(db=self.db)
                res = proc.process()
            except Exception:
                logger.exception('Error ejecutando CierreCajaProcessor')
                res = {'success': False}

            if not res or not res.get('success'):
                try:
                    from kool_tpv.utils.widgets.notificaciones import show_warning
                    root = self.winfo_toplevel()
                    show_warning(root, 'No se pudo crear el cierre')
                except Exception:
                    logger.info('No se pudo crear el cierre')
                return

            # Impresión delegada: la impresión se realiza ahora desde CierreCajaProcessor
            # (si se solicitó). Aquí solo se muestra feedback al usuario.
            try:
                cierre_id = res.get('cierre_id') if res else None
                printed = res.get('printed') if res else False
                if printed:
                    logger.info('Cierre marcado como impreso por el processor: cierre_id=%s', cierre_id)
                else:
                    logger.info('Cierre creado pero no impreso automáticamente: cierre_id=%s', cierre_id)
            except Exception:
                logger.exception('Error procesando estado de impresión del cierre')

            # Refrescar lista
            try:
                # SearchablePaginatedNavList has no explicit refresh method; re-trigger search
                try:
                    self.search_list._on_search()
                except Exception:
                    pass
            except Exception:
                pass

        except Exception:
            logger.exception('Error en _on_cerrar')

    def _show_pending_tickets(self):
        try:
            # Create or reuse a TicketsSubView configured to show pending tickets
            try:
                exists = False
                pending_ui = getattr(self.view, '_pending_tickets_subview', None)
                if pending_ui and getattr(pending_ui, 'winfo_exists', None):
                    exists = bool(pending_ui.winfo_exists())
            except Exception:
                exists = False

            if not pending_ui or not exists:
                try:
                    from kool_tpv.modulos.tpv.subviews.tickets_subview import TicketsSubView
                    parent = getattr(self.view, 'center_area', self.view)
                    pending_ui = TicketsSubView(parent=parent, db=self.db, view=self.view, pending_only=True)
                    try:
                        self.view._pending_tickets_subview = pending_ui
                        if getattr(self.view, 'controller', None):
                            try:
                                self.view.controller._pending_tickets_subview = pending_ui
                            except Exception:
                                pass
                    except Exception:
                        pass
                except Exception:
                    logger.exception('Error creando TicketsSubView(pending_only=True)')
                    return

            try:
                self.view.push_subview(pending_ui, "TICKETS PENDIENTES")
            except Exception:
                logger.exception('Error mostrando TicketsSubView(pending)')
        except Exception:
            logger.exception('Error en _show_pending_tickets')

    def _on_imprimir(self):
        """Handler del botón IMPRIMIR en la subvista Tickets.

        Pide confirmación, genera el texto del ticket mediante ImpresoraService
        y envía a la rutina de impresión (simulada o real según configuración).
        """
        try:
            # Obtener selección actual
            nav = getattr(self.search_list, 'nav_list', None)
            if nav is None:
                return

            sel = None
            try:
                sel = nav.get_selected_data()
            except Exception:
                sel = None

            if not sel:
                try:
                    from kool_tpv.utils.widgets.notificaciones import show_warning
                    root = self.winfo_toplevel()
                    show_warning(root, 'Selecciona un ticket para imprimir')
                except Exception:
                    logger.info('No hay selección para imprimir')
                return

            ticket_id = sel.get('ticket_id') or sel.get('id')
            try:
                ticket_id = int(ticket_id)
            except Exception:
                return

            # Confirmación
            try:
                from kool_tpv.utils.custom_dialog import show_info
                root = self.winfo_toplevel()
                confirmed = bool(show_info(root, 'Imprimir ticket', f'Se imprimirá el ticket {ticket_id}', confirm=True))
            except Exception:
                confirmed = True

            if not confirmed:
                return

            # Generar e imprimir (usar ImpresoraService)
            try:
                from kool_tpv.modulos.impresion.impresora_service import ImpresoraService
                imp = ImpresoraService(db=self.db, imprimir_en_consola=True)
                texto = None
                try:
                    texto = imp.generar_ticket_desde_id(ticket_id)
                except Exception:
                    logger.exception('Error generando ticket desde ImpresoraService')

                if not texto:
                    try:
                        row = self.db.fetch_one('SELECT ticket_text FROM tickets WHERE id = ?', (ticket_id,)) if getattr(self, 'db', None) is not None else None
                        texto = row[0] if row and row[0] else None
                    except Exception:
                        logger.exception('Error leyendo ticket_text fallback para imprimir')

                if texto:
                    try:
                        # Usar la rutina de impresión común (simulada si no hay ESC/POS)
                        imp._imprimir_texto_generico(texto, {'num_ticket': ticket_id})
                    except Exception:
                        # Fallback: imprimir en consola
                        try:
                            print('\n' + '='*50)
                            print(' SIMULACIÓN IMPRESIÓN TICKET ')
                            print('='*50 + '\n')
                            print(texto)
                            print('\n' + '='*50 + '\n')
                        except Exception:
                            logger.exception('Error simulando impresión en consola')
                else:
                    logger.info('No se encontró texto para imprimir del ticket id=%s', ticket_id)
            except Exception:
                logger.exception('Error en proceso de impresión (TicketsSubView)')

        except Exception:
            logger.exception('Error en _on_imprimir')

    def destroy(self):
        # NOTE: No need to unregister - we don't register in __init__ anymore
        # TpvView manages power handling for all subviews

        # Ensure global ticket display is hidden when this subview is destroyed
        try:
            if getattr(self, 'view', None) and getattr(self.view, 'controller', None):
                try:
                    self.view.controller.hide_ticket()
                except Exception:
                    pass
        except Exception:
            pass
        super().destroy()
