"""UI de Búsqueda Clientes (Grid manual dentro de CTkScrollableFrame).

Clon de busqueda_ui.py adaptado para clientes.
Provee búsqueda en tiempo real y scroll infinito (paginado).
"""
from typing import Optional
import logging
import customtkinter as ctk
import tkinter as tk

from kool_tpv.modulos.clientes.cliente_service import ClienteService
from kool_tpv.utils.utils import COLOR_BG_TERMINAL, COLOR_MATRIX, FONT_TERMINAL
from kool_tpv.utils.config_loader import load_colors


class BusquedaClientesUI:
    def __init__(self, parent, db=None, owner=None, module_name: str = 'clientes'):
        self.parent = parent
        self.owner = owner  # ClientesView instance para llamar show_editar_cliente
        self.db = db
        self.module_name = module_name
        self.service = ClienteService(db)

        # Cargar paleta de colores para el módulo
        try:
            self.colors = load_colors(self.module_name)
        except Exception:
            self.colors = {'text': COLOR_MATRIX, 'primary': COLOR_MATRIX, 'accent': COLOR_MATRIX}
        self.container = ctk.CTkFrame(self.parent, fg_color=COLOR_BG_TERMINAL)

        # Search entry
        self.search_var = tk.StringVar()
        self.search_entry = ctk.CTkEntry(
            self.container,
            textvariable=self.search_var,
            placeholder_text='Buscar cliente (nombre, DNI, teléfono)...',
            height=36,
            fg_color='#000000',
            text_color=self.colors.get('text', COLOR_MATRIX),
            border_width=2,
            border_color=self.colors.get('primary', COLOR_MATRIX)
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
            font=FONT_TERMINAL
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
            hover_color='#00AA00',
            command=self._on_search
        ).pack(side='left', padx=4)

        ctk.CTkCheckBox(
            estado_frame,
            text='Tesoro Inactivo',
            variable=self.check_tesoro_inactivo,
            text_color=self.colors.get('text', COLOR_MATRIX),
            fg_color=self.colors.get('primary', COLOR_MATRIX),
            hover_color='#00AA00',
            command=self._on_search
        ).pack(side='left', padx=4)

        # Headers (static)
        hdr_frame = ctk.CTkFrame(self.container, fg_color='transparent', height=32)
        hdr_frame.pack(fill='x', padx=12, pady=(0, 2))
        hdr_frame.pack_propagate(False)

        # Columnas: ID, NOMBRE, TELÉFONO, EMAIL, CIUDAD, TESORO, NIVEL, COMPRAS, ÚLTIMA COMPRA, ESTADO
        col_widths = [50, 220, 120, 180, 120, 90, 100, 80, 120, 100]
        headers = ['ID', 'NOMBRE', 'TELÉFONO', 'EMAIL', 'CIUDAD', 'TESORO', 'NIVEL', 'COMPRAS', 'ÚLTIMA COMPRA', 'ESTADO']

        for i, h in enumerate(headers):
            lbl = ctk.CTkLabel(
                hdr_frame,
                text=h,
                text_color=self.colors.get('text', COLOR_MATRIX),
                fg_color='#1a1a1a',
                anchor='w',
                font=('Courier New', 13, 'bold'),
                width=col_widths[i]-6,
                height=28,
                corner_radius=0,
            )
            lbl.place(x=sum(col_widths[:i]) + 6, y=2)
            # Separador vertical
            try:
                sep = ctk.CTkFrame(hdr_frame, fg_color='#2a2a2a', width=1)
                sep.place(x=sum(col_widths[:i+1]), y=2, height=28)
            except Exception:
                pass

        # Data area
        self.data_frame = ctk.CTkScrollableFrame(self.container, fg_color=COLOR_BG_TERMINAL)
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
        # Limpiar filas existentes
        for w in list(self.data_frame.winfo_children()):
            try:
                w.destroy()
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
        """Añadir fila de cliente al grid."""
        row_bg = '#1a1a1a' if (index % 2 == 0) else '#121212'
        row = ctk.CTkFrame(self.data_frame, fg_color=row_bg, height=30)
        row.pack(fill='x', pady=0)

        # Hover effect
        def on_enter(e, w=row):
            try:
                w.configure(fg_color='#333333')
            except Exception:
                pass

        def on_leave(e, w=row, bg=row_bg):
            try:
                w.configure(fg_color=bg)
            except Exception:
                pass

        row.bind('<Enter>', on_enter)
        row.bind('<Leave>', on_leave)

        # Doble click → abrir ficha cliente
        def on_double(e, cliente_id=cliente.get('id')):
            try:
                if self.owner and hasattr(self.owner, 'show_editar_cliente'):
                    self.owner.show_editar_cliente(cliente_id)
                else:
                    logging.warning('Owner no tiene show_editar_cliente')
            except Exception:
                logging.exception('Error en doble click fila cliente')

        row.bind('<Double-Button-1>', on_double)

        # Columnas
        col_widths = [50, 220, 120, 180, 120, 90, 100, 80, 120, 100]

        # Determinar estado
        estado = 'ACTIVO' if cliente.get('fidelidad_activa') else 'INACTIVO'
        color_estado = '#00FF00' if cliente.get('fidelidad_activa') else '#FF0000'

        values = [
            str(cliente.get('id', '')),
            cliente.get('nombre', ''),
            cliente.get('telefono', ''),
            cliente.get('email', ''),
            cliente.get('ciudad', ''),
            f"{cliente.get('tesoro_total', 0.0):.2f}€",
            cliente.get('nivel_nombre', 'Forastero'),
            str(cliente.get('total_compras', 0)),
            cliente.get('fecha_ultima_compra', 'Nunca'),
            estado
        ]

        x = 6
        for i, v in enumerate(values):
            # Color según columna
            if i == 9:  # ESTADO
                color_texto = color_estado
            elif i == 5:  # TESORO ⭐ DESTACA
                color_texto = self.colors.get('accent', '#FFD700')
            else:
                color_texto = self.colors.get('text', COLOR_MATRIX)

            lbl = ctk.CTkLabel(
                row,
                text=v,
                text_color=color_texto,
                fg_color='transparent',
                anchor='w',
                font=FONT_TERMINAL,
                width=col_widths[i]-8,
                height=28
            )
            lbl.place(x=x, y=2)

            # Forward events
            lbl.bind('<Double-Button-1>', on_double)
            lbl.bind('<Enter>', on_enter)
            lbl.bind('<Leave>', on_leave)

            x += col_widths[i]

        # Separador línea
        try:
            sep = ctk.CTkFrame(self.data_frame, fg_color='#2a2a2a', height=1)
            sep.pack(fill='x')
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
