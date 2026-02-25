"""UI de Búsqueda Clientes (Grid manual dentro de CTkScrollableFrame).

Clon de busqueda_ui.py adaptado para clientes.
Provee búsqueda en tiempo real y scroll infinito (paginado).
"""
from typing import Optional
import logging
import customtkinter as ctk
import tkinter as tk

from kool_tpv.modulos.clientes.cliente_service import ClienteService
from kool_tpv.utils.utils import COLOR_BG_TERMINAL, COLOR_MATRIX
from kool_tpv.utils.font_loader import get_font
from kool_tpv.utils.config_loader import load_colors
from kool_tpv.utils.keyboard_manager import KeyboardManager
from kool_tpv.utils.widgets.nav_list import NavList


class BusquedaClientesUI:
    def __init__(self, parent, db=None, owner=None, module_name: str = 'clientes', keyboard_manager=None):
        self.parent = parent
        self.owner = owner  # ClientesView instance para llamar show_editar_cliente
        self.db = db
        self.module_name = module_name
        self.service = ClienteService(db)

        # KeyboardManager: preferir la instancia pasada por parámetro (desde App/ClientesView),
        # en caso contrario conservar la lógica anterior que crea/obtiene una en el toplevel.
        try:
            if keyboard_manager is not None:
                self.keyboard_mgr = keyboard_manager
                try:
                    self.keyboard_manager = self.keyboard_mgr
                except Exception:
                    self.keyboard_manager = None
            else:
                root = parent.winfo_toplevel()
                if not hasattr(root, 'keyboard_manager'):
                    try:
                        root.keyboard_manager = KeyboardManager(root)
                    except Exception:
                        logging.exception('Error creando KeyboardManager en BusquedaClientesUI')
                        root.keyboard_manager = None
                self.keyboard_manager = getattr(root, 'keyboard_manager', None)
                try:
                    self.keyboard_mgr = self.keyboard_manager
                except Exception:
                    self.keyboard_mgr = None
        except Exception:
            logging.exception('Error inicializando KeyboardManager (BusquedaClientesUI)')

        # Cargar paleta de colores para el módulo
        try:
            self.colors = load_colors(self.module_name)
        except Exception:
            self.colors = {'text': COLOR_MATRIX, 'primary': COLOR_MATRIX, 'accent': COLOR_MATRIX}
        self.container = ctk.CTkFrame(self.parent, fg_color=self.colors.get('background', COLOR_BG_TERMINAL))

        # Search entry
        self.search_var = tk.StringVar()
        self.search_entry = ctk.CTkEntry(
            self.container,
            textvariable=self.search_var,
            placeholder_text='Buscar cliente (nombre, DNI, teléfono)...',
            height=36,
            fg_color=self.colors.get('background', COLOR_BG_TERMINAL),
            text_color=self.colors.get('text', COLOR_MATRIX),
            border_width=2,
            border_color=self.colors.get('primary', COLOR_MATRIX),
            font=get_font('entry', module='clientes')
        )
        self.search_entry.pack(fill='x', padx=12, pady=(12, 6))
        self.search_entry.bind('<KeyRelease>', lambda e: self._on_search())

        # Barra de filtros horizontal
        filter_frame = ctk.CTkFrame(self.container, fg_color='transparent', height=40)
        filter_frame.pack(fill='x', padx=12, pady=(6, 6))
        filter_frame.pack_propagate(False)

        ctk.CTkLabel(
            filter_frame,
            text='Filtrar por:',
            text_color=self.colors.get('text', COLOR_MATRIX),
            font=get_font('label', module='clientes')
        ).pack(side='left', padx=(0, 12))

        # Checkboxes estado
        estado_frame = ctk.CTkFrame(filter_frame, fg_color='transparent')
        estado_frame.pack(side='left', padx=(16, 0))

        self.check_tesoro_activo = tk.BooleanVar(value=True)
        self.check_tesoro_inactivo = tk.BooleanVar(value=False)

        ctk.CTkCheckBox(
            estado_frame,
            text='Tesoro Activo',
            variable=self.check_tesoro_activo,
            text_color=self.colors.get('text', COLOR_MATRIX),
            fg_color=self.colors.get('primary', COLOR_MATRIX),
            hover_color=self.colors.get('buttons', {}).get('primary', {}).get('hover', self.colors.get('secondary', '#00AA00')),
            command=self._on_search
        ).pack(side='left', padx=4)

        ctk.CTkCheckBox(
            estado_frame,
            text='Tesoro Inactivo',
            variable=self.check_tesoro_inactivo,
            text_color=self.colors.get('text', COLOR_MATRIX),
            fg_color=self.colors.get('primary', COLOR_MATRIX),
            hover_color=self.colors.get('buttons', {}).get('primary', {}).get('hover', self.colors.get('secondary', '#00AA00')),
            command=self._on_search
        ).pack(side='left', padx=4)

        # Data area -> usar NavList para filas
        columns = [
            ('ID', 50), ('NOMBRE', 220), ('TELÉFONO', 120), ('EMAIL', 180), ('CIUDAD', 120),
            ('TESORO', 90), ('NIVEL', 100), ('COMPRAS', 80), ('ÚLTIMA COMPRA', 120), ('ESTADO', 100)
        ]

        try:
            self.nav_list = NavList(
                self.container,
                columns=columns,
                on_select=self._on_nav_select,
                on_double_click=self._on_nav_double_click,
                module_name=self.module_name,
                keyboard_manager=self.keyboard_manager
            )
            self.nav_list.pack(fill='both', expand=True, padx=12, pady=6)

            # Exponer alias usado por el código existente
            self.data_frame = self.nav_list
            # canvas para chequear scroll
            self._canvas = getattr(self.nav_list, '_parent_canvas', getattr(self.nav_list, '_canvas', None))
        except Exception:
            logging.exception('Error creando NavList en BusquedaClientesUI')
            # Fallback: crear data_frame clásico
            self.data_frame = ctk.CTkScrollableFrame(self.container, fg_color=self.colors.get('background', COLOR_BG_TERMINAL))
            self.data_frame.pack(fill='both', expand=True, padx=12, pady=6)

        # Paginación
        self.page_limit = 50
        self.offset = 0
        self.termino = ''
        self.loading = False
        self.row_count = 0
        self._canvas = getattr(self.data_frame, '_canvas', None)

        # Cargar primera página
        self._reset_and_load()

        # Auto-scroll check
        try:
            self._periodic_check()
        except Exception:
            pass

        # Auto-focus
        try:
            self.container.after(100, lambda: self.search_entry.focus_set())
        except Exception:
            pass

    def get_widget(self):
        return self.container

    def _on_search(self):
        self.termino = (self.search_var.get() or '').strip()
        self._reset_and_load()

    def _reset_and_load(self):
        # Limpiar filas existentes (NavList o data_frame)
        try:
            if hasattr(self, 'nav_list') and self.nav_list is not None:
                try:
                    self.nav_list.clear_items()
                except Exception:
                    pass
            else:
                for w in list(self.data_frame.winfo_children()):
                    try:
                        w.destroy()
                    except Exception:
                        pass
        except Exception:
            pass

        self.offset = 0
        self.row_count = 0
        self._load_next_page()

    def _load_next_page(self):
        if self.loading:
            return
        self.loading = True
        try:
            # Aplicar filtros
            filtrar_tesoro_activo = None
            try:
                if self.check_tesoro_activo.get() and not self.check_tesoro_inactivo.get():
                    filtrar_tesoro_activo = True
                elif not self.check_tesoro_activo.get() and self.check_tesoro_inactivo.get():
                    filtrar_tesoro_activo = False
            except Exception:
                pass

            # Obtener clientes paginados
            items = self._buscar_clientes_paginados(
                termino=self.termino,
                tesoro_activo=filtrar_tesoro_activo,
                limit=self.page_limit,
                offset=self.offset
            )

            if not items:
                self.loading = False
                return

            # Añadir items a NavList o a data_frame tradicional
            if hasattr(self, 'nav_list') and self.nav_list is not None:
                for cliente in items:
                    try:
                        item = {
                            'ID': cliente.get('id'),
                            'NOMBRE': cliente.get('nombre'),
                            'TELÉFONO': cliente.get('telefono'),
                            'EMAIL': cliente.get('email'),
                            'CIUDAD': cliente.get('ciudad'),
                            'TESORO': f"{cliente.get('tesoro_total', 0.0):.2f}€",
                            'NIVEL': cliente.get('nivel_nombre'),
                            'COMPRAS': str(cliente.get('total_compras', 0)),
                            'ÚLTIMA COMPRA': cliente.get('fecha_ultima_compra'),
                            'ESTADO': 'ACTIVO' if cliente.get('fidelidad_activa') else 'INACTIVO',
                            'cliente_id': cliente.get('id')
                        }
                        self.nav_list.add_item(item)
                    except Exception:
                        logging.exception('Error añadiendo item a NavList')
            else:
                for i, cliente in enumerate(items):
                    self._append_row(cliente, self.row_count + i)

            self.row_count += len(items)
            self.offset += len(items)

        except Exception:
            logging.exception('Error cargando página de búsqueda clientes')
        finally:
            self.loading = False

    def _buscar_clientes_paginados(self, termino='', tesoro_activo=None, limit=50, offset=0):
        """Buscar clientes con paginado y filtros."""
        try:
            # Construir query con JOIN a niveles
            query = """
                SELECT c.id, c.nombre, c.telefono, c.email, c.ciudad, 
                       c.tesoro_total, c.total_compras, c.fecha_ultima_compra, 
                       c.fidelidad_activa, c.id_nivel,
                       n.nombre_nivel
                FROM clientes c
                LEFT JOIN niveles_fidelidad n ON c.id_nivel = n.id
                WHERE (c.nombre LIKE ? OR c.dni LIKE ? OR c.telefono LIKE ?)
            """
            params = [f'%{termino}%', f'%{termino}%', f'%{termino}%']

            # Filtro tesoro
            if tesoro_activo is not None:
                query += " AND c.fidelidad_activa = ?"
                params.append(1 if tesoro_activo else 0)

            query += " ORDER BY c.tesoro_total DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            rows = self.db.fetch_all(query, tuple(params))

            clientes = []
            for r in rows or []:
                clientes.append({
                    'id': r[0],
                    'nombre': r[1] or '',
                    'telefono': r[2] or '',
                    'email': r[3] or '',
                    'ciudad': r[4] or '',
                    'tesoro_total': float(r[5] or 0.0),
                    'total_compras': int(r[6] or 0),
                    'fecha_ultima_compra': r[7] or 'Nunca',
                    'fidelidad_activa': int(r[8] or 1),
                    'id_nivel': r[9],
                    'nivel_nombre': r[10] or 'Forastero'
                })

            return clientes

        except Exception:
            logging.exception('Error en _buscar_clientes_paginados')
            return []

    def _append_row(self, cliente: dict, index: int):
        """(Obsoleto) Añadir fila de cliente al grid.

        Nota: si `NavList` está activo, este método ya no se usa.
        """
        try:
            # Mantener fallback para compatibilidad
            row_bg = self.colors.get('bg_dark', '#1a1a1a') if (index % 2 == 0) else self.colors.get('bg_medium', '#121212')
            row = ctk.CTkFrame(self.data_frame, fg_color=row_bg, height=30)
            row.pack(fill='x', pady=0)
        except Exception:
            pass

    def _periodic_check(self):
        """Check scroll position para cargar más resultados."""
        try:
            canvas = self._canvas
            if canvas is not None:
                try:
                    yview = canvas.yview()
                    if len(yview) == 2 and yview[1] >= 0.995:
                        self._load_next_page()
                except Exception:
                    pass
        except Exception:
            pass
        try:
            self.container.after(200, self._periodic_check)
        except Exception:
            pass

    def _on_nav_select(self, data):
        """Callback cuando NavList selecciona un cliente."""
        try:
            # Solo seleccionar / preparar preview. No abrir ficha en single-click.
            # Dejamos la compatibilidad con usos futuros: exponer cliente seleccionado.
            cliente_id = None
            if isinstance(data, dict):
                cliente_id = data.get('cliente_id') or data.get('ID')
            # Exponer dato seleccionado en objeto (otras partes pueden leerlo)
            try:
                self.selected_cliente_id = cliente_id
            except Exception:
                pass
            # Mover foco al NavList para capturar teclas de navegación
            try:
                if hasattr(self, 'nav_list') and self.nav_list is not None:
                    try:
                        self.nav_list.focus_set()
                    except Exception:
                        self.container.focus_set()
                else:
                    self.container.focus_set()
            except Exception:
                pass
        except Exception:
            logging.exception('Error en _on_nav_select')

    def _on_nav_double_click(self, data):
        """Doble-click: abrir ficha de cliente usando el owner (ClientesView)."""
        try:
            cliente_id = None
            if isinstance(data, dict):
                cliente_id = data.get('cliente_id') or data.get('ID')
            if cliente_id and self.owner and hasattr(self.owner, 'show_editar_cliente'):
                try:
                    self.owner.show_editar_cliente(cliente_id)
                except Exception:
                    logging.exception('Error llamando show_editar_cliente desde on_double_click')
        except Exception:
            logging.exception('Error en _on_nav_double_click')
