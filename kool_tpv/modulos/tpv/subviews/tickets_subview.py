from customtkinter import CTkFrame
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class TicketsSubView(CTkFrame):

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

        self.btn_imprimir = ButtonFactory.create_button(
            parent=self.header_frame,
            text="IMPRIMIR",
            style_key="mini_outline_clientes",
            command=lambda: logger.info('Imprimir (no implementado)')
        )

        from customtkinter import CTkEntry

        self.search_entry = CTkEntry(
            self.header_frame,
            placeholder_text="Buscar ticket...",
            width=300,
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
            return self.repo.listar_tickets(texto or '')
        except Exception:
            logger.exception('Error buscando tickets')
            return []

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
