"""ClientesTicketsUI - Vista de tickets de cliente con visor.

Características:

    Hereda de PaginaConVisor (grid izquierda + visor derecha)
    Header: Filtros fecha + buscador producto
    Grid: Tickets ordenados por fecha (más reciente primero)
    Footer: Botones IMPRIMIR y EXPORTAR
    Click fila → muestra ticket_text en visor
    Colores automáticos desde clientes config (amarillo)
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Tuple

import customtkinter as ctk

from kool_tpv.utils.templates.pagina_con_visor import PaginaConVisor
from kool_tpv.utils.widgets.searchable_combo import SearchableCombo
from kool_tpv.utils.config_loader import create_action_button
from kool_tpv.utils.font_loader import get_font
from kool_tpv.utils.keyboard_manager import KeyboardManager
from kool_tpv.utils.widgets.nav_list import NavList

logger = logging.getLogger(__name__)


class ClientesTicketsUI(PaginaConVisor):
    """Vista de tickets de cliente con filtros y visor."""

    def __init__(self, parent, db, cliente_id: int, cliente_nombre: str = '', keyboard_manager=None):
        self.cliente_id = cliente_id
        self.cliente_nombre = cliente_nombre
        # Guardar referencia al KeyboardManager (si se provee desde la App)
        try:
            self.keyboard_mgr = keyboard_manager
        except Exception:
            self.keyboard_mgr = None
        self.tickets_data: List[Tuple[int, str, float, str, int]] = []
        self.fila_seleccionada = None
        self.indice_seleccionado = -1
        self.filas_widgets = []
        # Preparar KeyboardManager: usar el pasado por parámetro si existe,
        # si no, intentar reutilizar/crear en el toplevel como antes.
        try:
            if getattr(self, 'keyboard_mgr', None) is not None:
                try:
                    self.keyboard_manager = self.keyboard_mgr
                except Exception:
                    self.keyboard_manager = None
                logger.info('KeyboardManager recibido en ClientesTicketsUI')
            else:
                root = parent.winfo_toplevel()
                if not hasattr(root, 'keyboard_manager'):
                    try:
                        root.keyboard_manager = KeyboardManager(root)
                    except Exception:
                        logger.exception('Error creando KeyboardManager en toplevel')
                        root.keyboard_manager = None
                self.keyboard_manager = getattr(root, 'keyboard_manager', None)
                # Mantener también self.keyboard_mgr para consistencia
                try:
                    self.keyboard_mgr = self.keyboard_manager
                except Exception:
                    pass
                logger.info('KeyboardManager disponible en toplevel')
        except Exception:
            logger.exception('Error inicializando KeyboardManager (pre-super)')

        # Heredar de plantilla (module_name='clientes' → esquema de colores del módulo)
        super().__init__(parent, db=db, module_name='clientes')

        # Breadcrumb personalizado (opcional para quien integre)
        try:
            self.breadcrumb_text = f"CLIENTES > {cliente_nombre} > TICKETS"
        except Exception:
            self.breadcrumb_text = 'CLIENTES > TICKETS'

        # --- Título fijo encima del contenido ---
        try:
            titulo_cliente = ctk.CTkLabel(
                self.container,
                text=f'TICKETS DE {cliente_nombre.upper()}',
                font=get_font('title', module='clientes'),
                text_color=self.colors.get('accent'),
                fg_color='transparent'
            )
            titulo_cliente.grid(row=0, column=0, columnspan=2, sticky='w', padx=20, pady=(12, 0))
            # Ajustar layout: desplazar left_container y ticket_display a row=1
            try:
                self.left_container.grid(row=1, column=0, sticky='nsew', padx=(12, 6), pady=12)
            except Exception:
                pass
            try:
                self.ticket_display.grid(row=1, column=1, sticky='nsew', padx=(6, 12), pady=12)
            except Exception:
                pass
            # Rowconfigure: título fijo, contenido expansible
            try:
                self.container.grid_rowconfigure(0, weight=0)
                self.container.grid_rowconfigure(1, weight=1)
            except Exception:
                pass
        except Exception:
            logger.exception('Error creando título cliente')

        # Cargar datos
        self._cargar_tickets()

        logger.info(f'ClientesTicketsUI inicializado para cliente_id={cliente_id}')

    def _build_header(self):
        """Implementar filtros en header: fechas + buscador producto."""
        header_content = ctk.CTkFrame(self.header, fg_color='transparent')
        header_content.pack(fill='x', padx=12, pady=12)

        # FILA 1: Filtros fecha
        fecha_frame = ctk.CTkFrame(header_content, fg_color='transparent')
        fecha_frame.pack(fill='x', pady=(0, 8))

        ctk.CTkLabel(
            fecha_frame,
            text='DESDE:',
            font=get_font('label', module='clientes'),
            text_color=self.colors.get('text')
        ).pack(side='left', padx=(0, 6))

        fecha_desde = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        self.entry_desde = ctk.CTkEntry(
            fecha_frame,
            width=140,
            placeholder_text=fecha_desde,
            fg_color=self.colors.get('background'),
            text_color=self.colors.get('text'),
            border_color=self.colors.get('primary'),
            border_width=2
        , font=get_font('entry', module='clientes'))
        self.entry_desde.insert(0, fecha_desde)
        self.entry_desde.pack(side='left', padx=(0, 20))

        ctk.CTkLabel(
            fecha_frame,
            text='HASTA:',
            font=get_font('label', module='clientes'),
            text_color=self.colors.get('text')
        ).pack(side='left', padx=(0, 6))

        fecha_hasta = datetime.now().strftime('%Y-%m-%d')
        self.entry_hasta = ctk.CTkEntry(
            fecha_frame,
            width=140,
            placeholder_text=fecha_hasta,
            fg_color=self.colors.get('background'),
            text_color=self.colors.get('text'),
            border_color=self.colors.get('primary'),
            border_width=2
        , font=get_font('entry', module='clientes'))
        self.entry_hasta.insert(0, fecha_hasta)
        self.entry_hasta.pack(side='left', padx=(0, 20))

        # Botón FILTRAR
        btn_filtrar = ctk.CTkButton(
            fecha_frame,
            text='FILTRAR',
            command=self._aplicar_filtros,
            width=120,
            fg_color=self.colors.get('primary'),
            hover_color=self.colors.get('secondary'),
            text_color='#000000',
            font=get_font('button', module='clientes')
        )
        btn_filtrar.pack(side='left', padx=8)

        # FILA 2: Buscador producto
        buscar_frame = ctk.CTkFrame(header_content, fg_color='transparent')
        buscar_frame.pack(fill='x')

        ctk.CTkLabel(
            buscar_frame,
            text='BUSCAR PRODUCTO:',
            font=get_font('label', module='clientes'),
            text_color=self.colors.get('text')
        ).pack(side='left', padx=(0, 12))

        self.combo_producto = SearchableCombo(
            buscar_frame,
            placeholder='Escribe nombre y pulsa FILTRAR',
            module_name='clientes',
            width=320
        )
        self.combo_producto.pack(side='left', fill='x', expand=True, padx=(0, 12))

        # Cargar productos del cliente
        try:
            self._cargar_productos_cliente()
        except Exception:
            logger.exception('Error cargando productos para buscador')

        try:
            self.combo_producto.entry.bind('<Return>', lambda e: self._aplicar_filtros())
            self.combo_producto.entry.bind('<KeyRelease>', self._on_combo_keyrelease)
        except Exception:
            pass

    def _on_combo_keyrelease(self, event):
        """Maneja teclas en el buscador: Enter aplica filtro; si el campo queda vacío
        recarga la lista completa y limpia el visor."""
        try:
            texto = (self.combo_producto.get() or '').strip()
            if event.keysym == 'Return':
                try:
                    self._aplicar_filtros()
                except Exception:
                    logger.exception('Error aplicando filtros desde _on_combo_keyrelease')
                return

            # Si el usuario ha borrado el texto, recargar listado completo
            if texto == '':
                try:
                    self._cargar_tickets()
                    try:
                        self.update_visor('')
                    except Exception:
                        pass
                except Exception:
                    logger.exception('Error recargando tickets al vaciar buscador')
        except Exception:
            logger.exception('Error en _on_combo_keyrelease')

    def _build_grid(self):
        """Implementar grid de tickets."""
        # Usar NavList reutilizable para mostrar los tickets
        columns = [
            ('ID', 100),
            ('FECHA', 200),
            ('ARTS', 100),
            ('TOTAL', 120)
        ]

        # Reemplazar grid_scroll por NavList dentro del left_container
        try:
            # Limpiar posibles widgets residuales en left_container (salvar header/footer)
            try:
                for child in list(self.left_container.winfo_children()):
                    if child not in (self.header, self.footer):
                        try:
                            child.destroy()
                        except Exception:
                            pass
            except Exception:
                pass

            # Destruir widget viejo grid_scroll si aún existe
            try:
                if hasattr(self, 'grid_scroll') and self.grid_scroll is not None:
                    try:
                        self.grid_scroll.destroy()
                    except Exception:
                        pass
            except Exception:
                pass

            self.nav_list = NavList(
                self.left_container,
                columns=columns,
                on_select=self._on_nav_select,
                on_double_click=self._on_nav_double_click,
                module_name='clientes',
                keyboard_manager=self.keyboard_manager
            )
            self.nav_list.pack(side='top', fill='both', expand=True)

            # Mantener compatibilidad con código previo
            self.grid_scroll = self.nav_list
        except Exception:
            logger.exception('Error creando NavList en _build_grid')

    def _build_footer(self):
        """Implementar botones de acción: IMPRIMIR, EXPORTAR."""
        self.btn_imprimir = create_action_button(self.footer, 'imprimir', self._on_imprimir)
        self.btn_imprimir.pack(side='left', padx=8)

        self.btn_exportar = create_action_button(self.footer, 'exportar', self._on_exportar)
        self.btn_exportar.pack(side='left', padx=8)

    def _cargar_tickets(self):
        """Cargar tickets de la BD para el cliente."""
        try:
            if not self.db or not getattr(self.db, 'connection', None):
                logger.warning('No hay conexión BD en _cargar_tickets')
                return

            cur = self.db.connection.cursor()
            query = """
                SELECT
                    t.id,
                    t.created_at,
                    t.total,
                    t.ticket_text,
                    COUNT(tl.id) as num_productos
                FROM tickets t
                LEFT JOIN ticket_lines tl ON t.id = tl.ticket_id
                WHERE t.cliente_id = ?
                GROUP BY t.id
                ORDER BY t.created_at DESC
            """

            cur.execute(query, (self.cliente_id,))
            rows = cur.fetchall()

            self.tickets_data = [
                (
                    int(r[0]),  # ticket_id
                    r[1] or '',  # created_at
                    float(r[2]) if r[2] else 0.0,  # total
                    r[3] or '',  # ticket_text
                    int(r[4]) if r[4] else 0  # num_productos
                )
                for r in rows
            ]

            self._mostrar_tickets()
            logger.info(f'{len(self.tickets_data)} tickets cargados para cliente {self.cliente_id}')

        except Exception:
            logger.exception('Error cargando tickets')

    def _cargar_productos_cliente(self):
        """Cargar productos únicos que compró el cliente para el buscador."""
        try:
            if not self.db or not getattr(self.db, 'connection', None):
                return

            cur = self.db.connection.cursor()
            query = """
                SELECT DISTINCT tl.producto_id, tl.nombre
                FROM ticket_lines tl
                JOIN tickets t ON tl.ticket_id = t.id
                WHERE t.cliente_id = ?
                ORDER BY tl.nombre
            """
            cur.execute(query, (self.cliente_id,))
            rows = cur.fetchall()

            productos = [(int(r[0]), r[1]) for r in rows if r[1]]
            try:
                self.combo_producto.set_options(productos)
            except Exception:
                pass

            logger.debug(f'{len(productos)} productos cargados en buscador')
        except Exception:
            logger.exception('Error cargando productos cliente')

    def _mostrar_tickets(self):
        """Renderizar filas de tickets en el grid."""
        # Usar NavList para renderizar filas
        try:
            if not hasattr(self, 'nav_list') or self.nav_list is None:
                logger.warning('NavList no inicializado en _mostrar_tickets')
                return

            if not self.tickets_data:
                try:
                    self.nav_list.clear_items()
                    self.update_visor('')
                except Exception:
                    logger.exception('Error limpiando NavList con no tickets')
                return

            items = []
            for ticket_id, created_at, total, ticket_text, num_productos in self.tickets_data:
                items.append({
                    'ID': ticket_id,
                    'FECHA': created_at,
                    'ARTS': num_productos,
                    'TOTAL': f'{total:.2f}€',
                    'ticket_id': ticket_id,
                    'ticket_text': ticket_text
                })

            try:
                self.nav_list.set_items(items)
            except Exception:
                logger.exception('Error seteando items en NavList')

            # No necesitamos filas_widgets manuales ya
            self.filas_widgets = []
            self.indice_seleccionado = -1
        except Exception:
            logger.exception('Error renderizando tickets con NavList')

    def _on_nav_select(self, data):
        """Callback desde NavList cuando se selecciona una fila."""
        try:
            ticket_id = data.get('ticket_id') if isinstance(data, dict) else None
            ticket_text = data.get('ticket_text') if isinstance(data, dict) else ''
            try:
                # Llamar al handler de visualización (fila_frame no disponible en NavList)
                self._on_ticket_click(ticket_id, ticket_text, None)
            except Exception:
                logger.exception('Error mostrando ticket desde _on_nav_select')
        except Exception:
            logger.exception('Error en _on_nav_select')

    def _on_nav_double_click(self, data):
        """Doble-click en la lista de tickets: intentar abrir la ficha del cliente.

        Buscar un ancestro que implemente `show_editar_cliente` (ClientesView) y
        llamarlo con `self.cliente_id`.
        """
        try:
            # Selección local primero: mantener comportamiento de _on_nav_select
            try:
                self._on_nav_select(data)
            except Exception:
                pass

            # Buscar ancestro que tenga show_editar_cliente
            widget = getattr(self, 'container', None) or getattr(self, 'master', None)
            while widget is not None:
                if hasattr(widget, 'show_editar_cliente'):
                    try:
                        widget.show_editar_cliente(self.cliente_id)
                        return
                    except Exception:
                        logger.exception('Error llamando show_editar_cliente desde _on_nav_double_click')
                        return
                try:
                    widget = getattr(widget, 'master', None)
                except Exception:
                    break

            # Si no encontramos un ancestro, intentar llamar al toplevel si expone la vista
            try:
                root = self.container.winfo_toplevel()
                if hasattr(root, 'show_editar_cliente'):
                    try:
                        root.show_editar_cliente(self.cliente_id)
                        return
                    except Exception:
                        logger.exception('Error llamando show_editar_cliente en toplevel')
            except Exception:
                pass

            logger.debug('No se encontró show_editar_cliente en ancestros al doble-click')
        except Exception:
            logger.exception('Error manejando doble-click en ClientesTicketsUI')

    def _crear_fila_ticket(self, ticket_id, created_at, total, ticket_text, num_productos):
        fila = ctk.CTkFrame(
            self.grid_scroll,
            fg_color=self.colors.get('bg_medium', '#1a1a1a'),
            corner_radius=6,
            height=50,
            border_width=0 # Sin borde por defecto ⭐
        )
        fila.pack(fill='x', padx=6, pady=3)

        fila.bind('<Button-1>', lambda e: self._on_ticket_click(ticket_id, ticket_text, fila))

        widths = [100, 200, 100, 120]
        values = [str(ticket_id), created_at, str(num_productos), f'{total:.2f}€']

        for val, w in zip(values, widths):
            lbl = ctk.CTkLabel(
                fila,
                text=str(val),
                font=('Courier New', 12),
                text_color=self.colors.get('text'),
                width=w,
                anchor='w'
            )
            lbl.pack(side='left', padx=8, pady=8)
            lbl.bind('<Button-1>', lambda e, tid=ticket_id, txt=ticket_text, f=fila: self._on_ticket_click(tid, txt, f))

        return fila # Retornar widget para guardarlo

    def _on_ticket_click(self, ticket_id, ticket_text, fila_frame):
        try:
            # Restaurar color original de fila anterior (solo si trabajamos con widgets)
            if fila_frame is not None:
                if self.fila_seleccionada:
                    try:
                        self.fila_seleccionada.configure(
                            fg_color=self.colors.get('bg_medium', '#1a1a1a'),
                            border_width=0
                        )
                    except Exception:
                        pass

                # Highlight fila actual con borde amarillo ⭐
                try:
                    fila_frame.configure(
                        fg_color=self.colors.get('bg_dark', '#0d0d0d'),
                        border_color=self.colors.get('primary', '#FFD700'),
                        border_width=3 # Borde grueso amarillo
                    )
                except Exception:
                    pass

                self.fila_seleccionada = fila_frame

                # Actualizar índice seleccionado si tenemos la lista de widgets
                try:
                    self.indice_seleccionado = self.filas_widgets.index(fila_frame)
                except Exception:
                    self.indice_seleccionado = -1
            else:
                # Selección desde NavList: limpiar selección visual previa
                try:
                    if self.fila_seleccionada:
                        self.fila_seleccionada.configure(
                            fg_color=self.colors.get('bg_medium', '#1a1a1a'),
                            border_width=0
                        )
                except Exception:
                    pass
                self.fila_seleccionada = None
                self.indice_seleccionado = -1
            # Dar foco al container para recibir eventos teclado
            try:
                # Dar foco al toplevel para que KeyboardManager capture teclas
                    try:
                        self.container.winfo_toplevel().focus_set()
                    except Exception:
                        self.container.focus_set()
            except Exception:
                pass

            # Mostrar en visor usando la plantilla
            self.update_visor(ticket_text or 'Ticket sin contenido')
            logger.debug(f'Ticket {ticket_id} mostrado en visor')

            # Devolver foco a container para capturar flechas
            try:
                self.container.focus_set()
            except Exception:
                pass
        except Exception:
            logger.exception('Error mostrando ticket en visor')

    def _aplicar_filtros(self):
        """Aplicar filtros de fecha y producto."""
        try:
            fecha_desde = (self.entry_desde.get() or '').strip()
            fecha_hasta = (self.entry_hasta.get() or '').strip()
            producto_id = None
            try:
                producto_id = self.combo_producto.get_id()
                texto_combo = (self.combo_producto.get() or '').strip()
            except Exception:
                logger.exception('Error obteniendo producto_id')
                producto_id = None

            query = """
                SELECT
                    t.id,
                    t.created_at,
                    t.total,
                    t.ticket_text,
                    COUNT(tl.id) as num_productos
                FROM tickets t
                LEFT JOIN ticket_lines tl ON t.id = tl.ticket_id
                WHERE t.cliente_id = ?
            """
            params = [self.cliente_id]

            if fecha_desde:
                query += " AND t.created_at >= ?"
                params.append(fecha_desde)

            if fecha_hasta:
                query += " AND t.created_at <= ?"
                params.append(fecha_hasta)

            if producto_id:
                query += " AND EXISTS (SELECT 1 FROM ticket_lines WHERE ticket_id = t.id AND producto_id = ?)"
                params.append(producto_id)
            else:
                # Si no hay ID pero el usuario escribió texto, filtrar por nombre
                if texto_combo:
                    query += " AND EXISTS (SELECT 1 FROM ticket_lines tl2 WHERE tl2.ticket_id = t.id AND tl2.nombre LIKE ?)"
                    params.append(f'%{texto_combo}%')

            query += " GROUP BY t.id ORDER BY t.created_at DESC"

            cur = self.db.connection.cursor()
            cur.execute(query, tuple(params))
            rows = cur.fetchall()

            self.tickets_data = [
                (
                    int(r[0]), # ticket_id
                    r[1] or '', # created_at
                    float(r[2]) if r[2] else 0.0, # total
                    r[3] or '', # ticket_text
                    int(r[4]) if r[4] else 0 # num_productos
                )
                for r in rows
            ]

            self._mostrar_tickets()
            logger.info(f'Filtros aplicados: {len(self.tickets_data)} tickets encontrados')

        except Exception:
            logger.exception('Error aplicando filtros')

    def _on_imprimir(self):
        """Imprimir ticket seleccionado (placeholder)."""
        try:
            contenido = ''
            try:
                contenido = self.ticket_display.get_content()
            except Exception:
                contenido = ''

            if not contenido or not contenido.strip():
                from kool_tpv.utils.custom_dialog import show_error
                show_error(self.container, 'Imprimir', 'Selecciona un ticket primero')
                return

            logger.info('Acción IMPRIMIR triggered')
            from kool_tpv.utils.custom_dialog import show_success
            show_success(self.container, 'Imprimir', 'Funcionalidad en desarrollo')
        except Exception:
            logger.exception('Error en _on_imprimir')

    def _on_exportar(self):
        """Exportar ticket seleccionado a PDF (placeholder)."""
        try:
            contenido = ''
            try:
                contenido = self.ticket_display.get_content()
            except Exception:
                contenido = ''

            if not contenido or not contenido.strip():
                from kool_tpv.utils.custom_dialog import show_error
                show_error(self.container, 'Exportar', 'Selecciona un ticket primero')
                return

            logger.info('Acción EXPORTAR triggered')
            from kool_tpv.utils.custom_dialog import show_success
            show_success(self.container, 'Exportar', 'Funcionalidad en desarrollo')
        except Exception:
            logger.exception('Error en _on_exportar')

    # Arrow navigation is handled globally by KeyboardManager; local handlers removed.
