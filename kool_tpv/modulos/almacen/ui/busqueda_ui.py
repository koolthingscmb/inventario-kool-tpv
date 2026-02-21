"""UI de Búsqueda (Grid manual dentro de CTkScrollableFrame).

Provee búsqueda en tiempo real y scroll infinito (paginado).
"""
from typing import Optional
import logging
import customtkinter as ctk
import tkinter as tk

from kool_tpv.base_datos.producto_service import ProductoService
from kool_tpv.utils.utils import COLOR_BG_TERMINAL, COLOR_MATRIX, FONT_TERMINAL
from kool_tpv.utils.widgets.searchable_combo import SearchableCombo


class BusquedaUI:
    def __init__(self, parent, db=None, owner=None, module_name: str = 'almacen'):
        self.parent = parent
        self.owner = owner  # AlmacenView instance to call show_crear
        self.db = db
        self.service = ProductoService(db)
        from kool_tpv.utils.config_loader import load_colors
        try:
            self.colors = load_colors(module_name)
        except Exception:
            self.colors = {'background': COLOR_BG_TERMINAL, 'text': COLOR_MATRIX, 'border': COLOR_MATRIX, 'primary': COLOR_MATRIX, 'secondary': COLOR_MATRIX, 'light': COLOR_MATRIX, 'accent': COLOR_MATRIX, 'error': '#FF0000', 'warning': '#FFFF00'}

        self.container = ctk.CTkFrame(self.parent, fg_color=self.colors.get('background', COLOR_BG_TERMINAL))

        # Breadcrumb handled by BaseModuleView (owner)

        # Search entry
        self.search_var = tk.StringVar()
        self.search_entry = ctk.CTkEntry(
            self.container,
            textvariable=self.search_var,
            placeholder_text='Buscar...',
            height=36,
            fg_color=self.colors.get('background', COLOR_BG_TERMINAL),
            text_color=self.colors.get('text', COLOR_MATRIX),
            border_width=2,
            border_color=self.colors.get('border', COLOR_MATRIX),
        )
        self.search_entry.pack(fill='x', padx=12, pady=(12, 6))
        self.search_entry.bind('<KeyRelease>', lambda e: self._on_search())

        # Barra de filtros horizontal
        filter_frame = ctk.CTkFrame(self.container, fg_color='transparent', height=40)
        filter_frame.pack(fill='x', padx=12, pady=(6, 6))
        filter_frame.pack_propagate(False)

        # Label "Filtrar por:"
        ctk.CTkLabel(filter_frame, text='Filtrar por:', text_color=self.colors.get('text', COLOR_MATRIX), font=FONT_TERMINAL).pack(side='left', padx=(0, 12))

        # Cargar opciones
        categorias = [{'id': None, 'nombre': 'Todas'}] + (self.service.listar_categorias() or [])
        tipos = [{'id': None, 'nombre': 'Todos'}] + (self.service.listar_tipos() or [])

        # Label Categorías
        ctk.CTkLabel(filter_frame, text='Categorías:', text_color=self.colors.get('text', COLOR_MATRIX), font=FONT_TERMINAL).pack(side='left', padx=(0, 4))
        self.cat_combo = SearchableCombo(
            filter_frame,
            options=[(c['id'], c['nombre']) for c in categorias],
            width=160
        )
        self.cat_combo.set('Todas')
        # Bind both key events and the selection virtual event to trigger search
        self.cat_combo.entry.bind('<KeyRelease>', lambda e: self._on_search())
        self.cat_combo.entry.bind('<<SearchableComboSelected>>', lambda e: self._on_search())
        self.cat_combo.pack(side='left', padx=(0, 12))

        # Label Tipos
        ctk.CTkLabel(filter_frame, text='Tipos:', text_color=self.colors.get('text', COLOR_MATRIX), font=FONT_TERMINAL).pack(side='left', padx=(0, 4))
        self.tipo_combo = SearchableCombo(
            filter_frame,
            options=[(t['id'], t['nombre']) for t in tipos],
            width=160
        )
        self.tipo_combo.set('Todos')
        self.tipo_combo.entry.bind('<KeyRelease>', lambda e: self._on_search())
        self.tipo_combo.entry.bind('<<SearchableComboSelected>>', lambda e: self._on_search())
        self.tipo_combo.pack(side='left', padx=(0, 12))

        # Frame para checkboxes de estado
        estado_frame = ctk.CTkFrame(filter_frame, fg_color='transparent')
        estado_frame.pack(side='left', padx=(16, 0))

        self.check_activo = tk.BooleanVar(value=True)
        self.check_sin_stock = tk.BooleanVar(value=True)
        self.check_archivado = tk.BooleanVar(value=False)

        ctk.CTkCheckBox(
            estado_frame,
            text='Activos',
            variable=self.check_activo,
            text_color=self.colors.get('text', COLOR_MATRIX),
            fg_color=self.colors.get('primary', COLOR_MATRIX),
            hover_color=self.colors.get('light', '#00AA00'),
            command=self._on_search,
        ).pack(side='left', padx=4)
        ctk.CTkCheckBox(
            estado_frame,
            text='Sin Stock',
            variable=self.check_sin_stock,
            text_color=self.colors.get('text', COLOR_MATRIX),
            fg_color=self.colors.get('secondary', COLOR_MATRIX),
            hover_color=self.colors.get('light', '#00AA00'),
            command=self._on_search,
        ).pack(side='left', padx=4)
        ctk.CTkCheckBox(
            estado_frame,
            text='Archivados',
            variable=self.check_archivado,
            text_color=self.colors.get('text', COLOR_MATRIX),
            fg_color=self.colors.get('accent', COLOR_MATRIX),
            hover_color=self.colors.get('light', '#00AA00'),
            command=self._on_search,
        ).pack(side='left', padx=4)

        # Headers (static)
        hdr_frame = ctk.CTkFrame(self.container, fg_color='transparent', height=32)
        hdr_frame.pack(fill='x', padx=12, pady=(0, 2))
        hdr_frame.pack_propagate(False) # Forzar altura fija
        # Column widths (px): ID, SKU, NOMBRE, CATEGORÍA, TIPO, CÓDIGO BARRAS, PVP, STOCK, VENTAS, ESTADO
        col_widths = [50, 140, 280, 140, 110, 130, 85, 75, 75, 95]
        headers = ['ID', 'SKU', 'NOMBRE', 'CATEGORÍA', 'TIPO', 'CÓDIGO BARRAS', 'PVP', 'STOCK', 'VENTAS', 'ESTADO']
        for i, h in enumerate(headers):
            lbl = ctk.CTkLabel(
                hdr_frame,
                text=h,
                text_color=self.colors.get('text', COLOR_MATRIX),
                fg_color=self.colors.get('bg_sidebar', '#1a1a1a'),
                anchor='w',
                font=('Courier New', 13, 'bold'),
                width=col_widths[i]-6,
                height=28,
                corner_radius=0,
            )
            lbl.place(x=sum(col_widths[:i]) + 6, y=2)
            # vertical separator (right border)
            try:
                sep = ctk.CTkFrame(hdr_frame, fg_color=self.colors.get('bg_medium', '#2a2a2a'), width=1)
                sep.place(x=sum(col_widths[:i+1]), y=2, height=28)
            except Exception:
                pass

        # Data area
        self.data_frame = ctk.CTkScrollableFrame(self.container, fg_color=self.colors.get('background', COLOR_BG_TERMINAL))
        self.data_frame.pack(fill='both', expand=True, padx=12, pady=6)

        # pagination state
        self.page_limit = 50
        self.offset = 0
        self.termino = ''
        self.loading = False

        # list of rendered rows count
        self.row_count = 0

        # attempt to access underlying canvas for scroll checks
        self._canvas = getattr(self.data_frame, '_canvas', None)

        # start with first page
        self._reset_and_load()

        # start periodic check for scroll end (fallback)
        try:
            self._periodic_check()
        except Exception:
            pass

        # Auto-focus en search entry
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
        # Clear existing rows
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
            # Recoger filtros activos usando get_id() de SearchableCombo
            cat_id = None
            tipo_id = None
            try:
                cat_id = self.cat_combo.get_id() if hasattr(self, 'cat_combo') else None
            except Exception:
                cat_id = None
            try:
                tipo_id = self.tipo_combo.get_id() if hasattr(self, 'tipo_combo') else None
            except Exception:
                tipo_id = None

            estados = []
            try:
                if getattr(self, 'check_activo', None) and self.check_activo.get():
                    estados.append('activo')
                if getattr(self, 'check_sin_stock', None) and self.check_sin_stock.get():
                    estados.append('sin_stock')
                if getattr(self, 'check_archivado', None) and self.check_archivado.get():
                    estados.append('archivado')
            except Exception:
                pass

            items = self.service.buscar_productos_paginados(
                termino_busqueda=self.termino,
                categoria_id=cat_id,
                tipo_id=tipo_id,
                estados=estados if estados else None,
                limit=self.page_limit,
                offset=self.offset
            )
            if not items:
                self.loading = False
                return
            for i, it in enumerate(items):
                self._append_row(it, self.row_count + i)
            self.row_count += len(items)
            self.offset += len(items)
        except Exception:
            logging.exception('Error cargando página de búsqueda')
        finally:
            self.loading = False

    def _append_row(self, item: dict, index: int):
        # Create a horizontal frame representing a row
        row_bg = self.colors.get('bg_sidebar', '#1a1a1a') if (index % 2 == 0) else self.colors.get('bg_dark', '#121212')
        row = ctk.CTkFrame(self.data_frame, fg_color=row_bg, height=30)
        row.pack(fill='x', pady=0)
        # hover effect
        def on_enter(e, w=row):
            try:
                w.configure(fg_color=self.colors.get('bg_medium', '#333333'))
            except Exception:
                pass
        def on_leave(e, w=row, bg=row_bg):
            try:
                w.configure(fg_color=bg)
            except Exception:
                pass

        row.bind('<Enter>', on_enter)
        row.bind('<Leave>', on_leave)

        # double click => open editor via owner
        def on_double(e, prod_id=item.get('id')):
            try:
                if self.owner and hasattr(self.owner, 'show_crear'):
                    try:
                        self.owner.show_crear(producto_id=prod_id)
                    except Exception:
                        # fallback: attempt call without kw
                        try:
                            self.owner.show_crear(prod_id)
                        except Exception:
                            logging.exception('Error llamando a show_crear desde BusquedaUI')
            except Exception:
                logging.exception('Error en doble click fila')

        row.bind('<Double-Button-1>', on_double)

        # Column labels inside the row (follow same widths as header)
        col_widths = [50, 140, 280, 140, 110, 130, 85, 75, 75, 95]
        estado = item.get('estado', 'Activo')
        values = [
            str(item.get('id') or ''),
            item.get('sku') or '',
            item.get('nombre') or '',
            item.get('categoria') or '',
            item.get('tipo') or '',
            item.get('ean') or 'Sin EAN',
            item.get('pvp') or '0.00',
            str(item.get('stock_actual') or 0),
            str(item.get('ventas') or 0),
            estado
        ]
        x = 6
        for i, v in enumerate(values):
            # Determinar color según columna ESTADO
            if i == 9:
                if v == 'Activo':
                    color_texto = self.colors.get('primary', '#00FF00')
                elif v == 'Sin Stock':
                    color_texto = self.colors.get('warning', '#FFFF00')
                else:
                    color_texto = self.colors.get('error', '#FF0000')
            else:
                color_texto = self.colors.get('text', COLOR_MATRIX)

            lbl = ctk.CTkLabel(row, text=v, text_color=color_texto, fg_color='transparent', anchor='w', font=FONT_TERMINAL, width=col_widths[i]-8, height=28)
            lbl.place(x=x, y=2)
            # forward events for double click and hover
            lbl.bind('<Double-Button-1>', on_double)
            lbl.bind('<Enter>', on_enter)
            lbl.bind('<Leave>', on_leave)
            x += col_widths[i]
        # thin separator line below row to emulate cell borders
        try:
            sep = ctk.CTkFrame(self.data_frame, fg_color=self.colors.get('bg_medium', '#2a2a2a'), height=1)
            sep.pack(fill='x')
        except Exception:
            pass

    def _periodic_check(self):
        try:
            canvas = self._canvas
            if canvas is not None:
                try:
                    yview = canvas.yview()
                    if len(yview) == 2 and yview[1] >= 0.995:
                        # near bottom
                        self._load_next_page()
                except Exception:
                    pass
        except Exception:
            pass
        try:
            self.container.after(200, self._periodic_check)
        except Exception:
            pass
