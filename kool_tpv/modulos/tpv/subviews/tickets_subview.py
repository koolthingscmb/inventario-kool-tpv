from customtkinter import CTkFrame
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class TicketsSubView(CTkFrame):

    def __init__(self, parent, db, view=None, pending_only: bool = False):
        super().__init__(parent)

        self.db = db
        self.view = view

        # In-memory cache for generated tickets (ticket_id -> content)
        self._ticket_cache = {}

        # Header (top, spans both columns)
        self.header_frame = CTkFrame(self)
        self.header_frame.grid(row=0, column=0, columnspan=2, sticky='ew', padx=20, pady=10)

        from kool_tpv.utils.factories.button_factory import ButtonFactory

        self.btn_imprimir = ButtonFactory.create_button(
            parent=self.header_frame,
            text="IMPRIMIR",
            style_key="mini_outline_clientes",
            command=self._on_imprimir
        )

        from customtkinter import CTkEntry

        # Date pickers for filtering range (desde / hasta)
        try:
            from kool_tpv.utils.widgets.date_picker_entry import DatePickerEntry
            self.date_from = DatePickerEntry(self.header_frame, module_name='tickets', width=90, allow_future=False, command=lambda d=None: self._on_date_change())
            self.date_from.pack(side="left", padx=(0, 4))
            # small separator label
            try:
                from customtkinter import CTkLabel
                self._date_range_label = CTkLabel(self.header_frame, text='a')
                self._date_range_label.pack(side='left')
            except Exception:
                self._date_range_label = None
            self.date_to = DatePickerEntry(self.header_frame, module_name='tickets', width=90, allow_future=False, command=lambda d=None: self._on_date_change())
            self.date_to.pack(side="left", padx=(4, 6))
            # Botón 'X' pequeño junto a los date pickers (config-driven, con fallback)
            try:
                from kool_tpv.utils.config_loader import create_action_button
                self.btn_x = create_action_button(parent=self.header_frame, button_key='x', command=lambda: self._on_x_clicked(), width=40)
                self.btn_x.pack(side='left', padx=6)
            except Exception:
                try:
                    from customtkinter import CTkButton
                    self.btn_x = CTkButton(self.header_frame, text='X', command=lambda: self._on_x_clicked(), width=40)
                    self.btn_x.pack(side='left', padx=6)
                except Exception:
                    self.btn_x = None
        except Exception:
            self.date_from = None
            self.date_to = None

        self.search_entry = CTkEntry(
            self.header_frame,
            placeholder_text="Buscar ticket...",
            width=250,
        )
        self.search_entry.pack(side="left", padx=10)

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

        # Repo
        try:
            from kool_tpv.modulos.ticket.ticket_repository import TicketRepository
            self.repo = TicketRepository(self.db)
        except Exception:
            self.repo = None

        # Auth service (used to protect dangerous actions)
        try:
            from kool_tpv.utils.auth_service import AuthService
            self.auth_service = AuthService(self.db)
        except Exception:
            self.auth_service = None

        # Mode: if pending_only, list only tickets with cierre_id IS NULL
        self.pending_only = bool(pending_only)

        # Keyboard manager
        root = self.winfo_toplevel()
        from kool_tpv.utils.keyboard_manager import KeyboardManager

        if not hasattr(root, "keyboard_manager") or root.keyboard_manager is None:
            root.keyboard_manager = KeyboardManager(root)

        self.keyboard_manager = root.keyboard_manager

        # Power handler registration
        try:
            root = self.winfo_toplevel()
            if hasattr(root, "register_power_handler"):
                root.register_power_handler(self._handle_power, owner=self)
        except Exception:
            pass

        columns = [
            ("num_ticket", 80, "Nº"),
            ("created_at", 180, "Día / Hora"),
            ("total", 120, "Total"),
            ("cajero", 140, "Cajero"),
            ("cliente", 180, "Cliente"),
            ("forma_pago", 120, "Forma Pago"),
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
            search_function=self._buscar_tickets,
            map_function=self._map_ticket,
            module_name="tickets",
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

        # Bind search entry to widget
        self.search_entry.bind(
            "<KeyRelease>",
            lambda e: self.search_list.set_search_text(self.search_entry.get())
        )

    def _buscar_tickets(self, texto):
        try:
            if not self.repo:
                return []
            # obtener lista base desde repo
            if self.pending_only:
                rows = self.repo.listar_tickets_pendientes(texto or '')
            else:
                rows = self.repo.listar_tickets(texto or '')

            # aplicar filtro por rango de fechas si los date pickers existen
            date_from = None
            date_to = None
            try:
                if getattr(self, 'date_from', None):
                    date_from = self.date_from.get() or None
            except Exception:
                date_from = None
            try:
                if getattr(self, 'date_to', None):
                    date_to = self.date_to.get() or None
            except Exception:
                date_to = None

            if (date_from or date_to) and rows:
                filtered = []
                for r in rows:
                    try:
                        created = r.get('created_at') if isinstance(r, dict) else (r[2] if len(r) > 2 else None)
                        if not created:
                            continue
                        # created may be 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS'
                        created_date = str(created).split(' ')[0]
                        if date_from and created_date < date_from:
                            continue
                        if date_to and created_date > date_to:
                            continue
                        filtered.append(r)
                    except Exception:
                        filtered.append(r)
                return filtered

            return rows
        except Exception:
            logger.exception('Error buscando tickets')
            return []

    def _on_date_change(self):
        try:
            # trigger navlist refresh
            try:
                self.search_list._on_search()
            except Exception:
                # fallback: set search text to re-trigger
                try:
                    self.search_list.set_search_text(self.search_entry.get())
                except Exception:
                    pass
        except Exception:
            logger.exception('Error en _on_date_change')

    def _map_ticket(self, detalle):
        try:
            # Formatear fecha
            created = detalle.get('created_at')
            created_str = created
            try:
                if created:
                    created_dt = datetime.fromisoformat(created)
                    created_str = created_dt.strftime('%d/%m/%Y %H:%M')
            except Exception:
                try:
                    if isinstance(created, datetime):
                        created_str = created.strftime('%d/%m/%Y %H:%M')
                except Exception:
                    created_str = str(created)

            total = detalle.get('total')
            try:
                # total is a Decimal (read_from_db). Format to 2 decimals
                total_str = f"{total:.2f}"
            except Exception:
                total_str = str(total)

            return {
                'ticket_id': detalle.get('id'),
                'num_ticket': detalle.get('num_ticket'),
                'created_at': created_str,
                'total': total_str,
                'cajero': detalle.get('cajero') or '',
                'cliente': detalle.get('cliente') or '',
                'forma_pago': detalle.get('forma_pago') or '',
            }
        except Exception:
            logger.exception('Error mapeando ticket')
            return {}

    def _on_nav_select(self, data):
        try:
            ticket_id = None
            if isinstance(data, dict):
                ticket_id = data.get('ticket_id') or data.get('id')
            if not ticket_id:
                return
            # Delegate to central controller's ticket display (uses cache there)
            try:
                if getattr(self, 'view', None) and getattr(self.view, 'controller', None):
                    try:
                        self.view.controller.show_ticket(ticket_id)
                    except Exception:
                        logger.exception('Error pidiendo visor global al controller')
                    return
            except Exception:
                logger.exception('Error delegando show_ticket al controller')

        except Exception:
            logger.exception('Error en _on_nav_select')

    def _handle_power(self):
        try:
            if self.view and hasattr(self.view, "pop_subview"):
                self.view.pop_subview()
                try:
                    if getattr(self.view, "ticket_carrito", None):
                        self.view.ticket_carrito.update_carrito()
                except Exception:
                    pass
                return True
        except Exception:
            pass
        return False

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
                    from kool_tpv.utils.custom_dialog import show_warning
                    root = self.winfo_toplevel()
                    show_warning(root, 'No hay selección', 'Selecciona un ticket para imprimir')
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

    def _on_x_clicked(self):
        try:
            from kool_tpv.utils.custom_dialog import show_password_dialog, show_warning, show_info

            parent = None
            try:
                parent = self.winfo_toplevel()
            except Exception:
                parent = None

            password = show_password_dialog(
                parent,
                titulo="Autenticación Admin",
                mensaje="Introduce contraseña de administrador:"
            )

            if password is None or password == "":
                return

            # Validate admin password
            try:
                if not (self.auth_service and self.auth_service.validate_admin_password(password)):
                    show_warning(parent, "ACCESO DENEGADO", "Contraseña incorrecta.", callback=self._on_x_clicked)
                    return
            except Exception:
                logger.exception('Error validando contraseña admin')
                show_warning(parent, 'Error', 'Fallo validando contraseña admin')
                return

            # Authenticated: ask for explicit confirmation to close tickets
            logger.info("Botón 'X' presionado en TicketsSubView (autenticado)")
            try:
                confirmed = False
                try:
                    confirmed = bool(show_info(parent, 'AUTENTICADO', '¿Quieres cerrar los tickets mostrados en el Display?', confirm=True))
                except Exception:
                    confirmed = False

                if not confirmed:
                    return

                logger.info(f"Confirmación cierre: {confirmed}")

                # --- EXTRAER ticket_ids segun filtro (rango) o pendientes ---
                rows = None
                try:
                    if getattr(self, 'date_from', None) or getattr(self, 'date_to', None):
                        rows = self._buscar_tickets('')
                    else:
                        rows = self.repo.listar_tickets_pendientes('') if getattr(self, 'repo', None) is not None else []
                except Exception:
                    rows = []

                logger.info(f"Rows extraídos: {len(rows or [])} tickets")

                ticket_ids = []
                for r in (rows or []):
                    try:
                        if isinstance(r, dict):
                            tid = r.get('id')
                        else:
                            tid = r[0] if len(r) > 0 else None
                        if tid is None:
                            continue
                        ticket_ids.append(int(tid))
                    except Exception:
                        continue

                logger.info(f"Ticket_ids extraídos: {ticket_ids}")

                if not ticket_ids:
                    try:
                        show_warning(parent, 'Nada que cerrar', 'No hay tickets a cerrar en el rango seleccionado o pendientes')
                    except Exception:
                        logger.info('No hay tickets a cerrar')
                    return

                logger.info('Procesando cierre para %d tickets (preview)', len(ticket_ids))

                # --- PROCESAR CIERRE (no capturar excepciones aquí según indicación) ---
                from kool_tpv.modulos.ticket.cierre_caja_processor import CierreCajaProcessor

                processor = CierreCajaProcessor(self.db)
                resultado = processor.process(ticket_ids=ticket_ids)

                logger.info(f"Resultado proceso cierre: success={resultado.get('success')}, cierre_id={resultado.get('cierre_id')}")

                if not resultado or not resultado.get('success'):
                    try:
                        show_warning(parent, 'Error', f"No se pudo generar el cierre: {resultado.get('error') if resultado else 'unknown'}")
                    except Exception:
                        logger.error('Fallo generando cierre: %s', resultado)
                    return

                # --- GENERAR TEXTO del cierre usando ImpresoraService / CierreTicketGenerator ---
                try:
                    from kool_tpv.modulos.impresion.impresora_service import ImpresoraService
                    imp = ImpresoraService(db=self.db)
                    config = getattr(imp, 'config', {}) or {}
                    cierre_data = resultado.get('cierre', {}) or {}
                    tickets = resultado.get('tickets', []) or []
                    totals = resultado.get('totals', {}) or {}
                    texto = imp.cierre_ticket_generator.generate(config, cierre_data, tickets, totals=totals)
                except Exception:
                    logger.exception('Error generando texto de cierre')
                    try:
                        show_warning(parent, 'Error', 'Fallo generando preview del cierre')
                    except Exception:
                        pass
                    return

                # --- MOSTRAR EN VISOR GLOBAL (usar cache_key 'cierre_preview') ---
                try:
                    ctrl = getattr(self.view, 'controller', None)
                    if not ctrl:
                        logger.error('Controller no disponible para mostrar preview')
                        return

                    # Asegurar que exista el visor
                    try:
                        if not getattr(ctrl, '_ticket_display', None):
                            ctrl.setup_ticket_display()
                    except Exception:
                        pass

                    cache_key = 'cierre_preview'
                    try:
                        ctrl._ticket_display_cache[cache_key] = texto
                    except Exception:
                        try:
                            ctrl._ticket_display_cache = {cache_key: texto}
                        except Exception:
                            pass

                    # Set content and place overlay
                    try:
                        td = getattr(ctrl, '_ticket_display', None)
                        if td is None:
                            logger.error('No hay _ticket_display en controller')
                            return
                        try:
                            td.set_content(texto)
                        except Exception:
                            logger.exception('Error seteando contenido en ticket_display')
                        try:
                            td.place(relx=0, rely=0, relwidth=1, relheight=1)
                        except Exception:
                            try:
                                td.pack(fill='both', expand=True)
                            except Exception:
                                pass
                        try:
                            td.lift()
                        except Exception:
                            pass
                    except Exception:
                        logger.exception('Error mostrando ticket_display para preview')

                except Exception:
                    logger.exception('Error preparando visor para preview')

                # --- PEDIR CONFIRMACIÓN FINAL al admin: si cancela, ocultar visor ---
                try:
                    confirmed2 = False
                    try:
                        confirmed2 = bool(show_info(parent, 'AUTENTICADO', '¿Confirmas cierre de estos tickets?', confirm=True))
                    except Exception:
                        confirmed2 = False

                    if not confirmed2:
                        try:
                            if getattr(self.view, 'controller', None):
                                try:
                                    self.view.controller.hide_ticket()
                                except Exception:
                                    pass
                        except Exception:
                            pass
                        return
                    # If confirmed, stop here and wait for next phase (do not execute close now)
                except Exception:
                    logger.exception('Error pidiendo confirmación final para cierre')
            except Exception:
                logger.exception('Error mostrando confirmación tras autenticación')

        except Exception:
            logger.exception('Error en _on_x_clicked')

    def destroy(self):
        try:
            root = self.winfo_toplevel()
            if hasattr(root, "unregister_power_handler"):
                root.unregister_power_handler(owner=self)
        except Exception:
            pass

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
