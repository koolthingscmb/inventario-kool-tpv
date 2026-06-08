"""UI de Búsqueda (Grid manual dentro de CTkScrollableFrame).

Provee búsqueda en tiempo real y scroll infinito (paginado).
"""
from typing import Optional, List
import logging
import customtkinter as ctk
import tkinter as tk

from kool_tpv.base_datos.producto_service import ProductoService
from kool_tpv.base_datos.categoria_service import CategoriaService
from kool_tpv.base_datos.tipo_service import TipoService
from kool_tpv.utils.font_loader import get_font
from kool_tpv.utils.widgets.searchable_combo import SearchableCombo
from kool_tpv.utils.widgets.virtual_nav_list import VirtualNavList


class BusquedaUI:
    def __init__(self, parent, db=None, owner=None, keyboard_manager=None, module_name: str = 'almacen'):
        self.parent = parent
        self.owner = owner  # AlmacenView instance to call show_crear
        self.db = db
        self.service = ProductoService(db)
        self.categoria_service = CategoriaService(db)
        self.tipo_service = TipoService(db)
        from kool_tpv.utils.config_loader import load_colors
        try:
            self.colors = load_colors(module_name)
        except Exception:
            self.colors = {'background': '#1a1a1a', 'text': '#00FF00', 'border': '#00FF00', 'primary': '#00FF00', 'secondary': '#00FF00', 'light': '#00AA00', 'accent': '#00FF00', 'error': '#FF0000', 'warning': '#FFFF00'}

        self.container = ctk.CTkFrame(self.parent, fg_color=self.colors.get('background', '#1a1a1a'))
        self.module_name = module_name
        self.keyboard_mgr = keyboard_manager

        # Breadcrumb handled by BaseModuleView (owner)

        # Search entry
        self.search_var = tk.StringVar()
        self.search_entry = ctk.CTkEntry(
            self.container,
            textvariable=self.search_var,
            placeholder_text='Buscar...',
            height=36,
            fg_color=self.colors.get('background', '#1a1a1a'),
            text_color=self.colors.get('text', '#00FF00'),
            border_width=2,
            border_color=self.colors.get('border', '#00FF00'),
        )
        self.search_entry.pack(fill='x', padx=12, pady=(12, 6))
        self.search_entry.bind('<KeyRelease>', lambda e: self._on_search())

        # Barra de filtros horizontal
        filter_frame = ctk.CTkFrame(self.container, fg_color='transparent', height=40)
        filter_frame.pack(fill='x', padx=12, pady=(6, 6))
        filter_frame.pack_propagate(False)

        # Label "Filtrar por:"
        ctk.CTkLabel(filter_frame, text='Filtrar por:', text_color=self.colors.get('text', '#00FF00'), font=get_font('label', module=self.module_name)).pack(side='left', padx=(0, 12))

        # Cargar opciones
        categorias = [{'id': None, 'nombre': 'Todas'}] + (self.categoria_service.get_all() or [])
        tipos = [{'id': None, 'nombre': 'Todos'}] + (self.tipo_service.get_all_tipos() or [])

        # Label Categorías
        ctk.CTkLabel(filter_frame, text='Categorías:', text_color=self.colors.get('text', '#00FF00'), font=get_font('label', module=self.module_name)).pack(side='left', padx=(0, 4))
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
        ctk.CTkLabel(filter_frame, text='Tipos:', text_color=self.colors.get('text', '#00FF00'), font=get_font('label', module=self.module_name)).pack(side='left', padx=(0, 4))
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
            text_color=self.colors.get('text', '#00FF00'),
            fg_color=self.colors.get('primary', '#00FF00'),
            hover_color=self.colors.get('light', '#00AA00'),
            command=self._on_search,
        ).pack(side='left', padx=4)
        ctk.CTkCheckBox(
            estado_frame,
            text='Sin Stock',
            variable=self.check_sin_stock,
            text_color=self.colors.get('text', '#00FF00'),
            fg_color=self.colors.get('secondary', '#00FF00'),
            hover_color=self.colors.get('light', '#00AA00'),
            command=self._on_search,
        ).pack(side='left', padx=4)
        ctk.CTkCheckBox(
            estado_frame,
            text='Archivados',
            variable=self.check_archivado,
            text_color=self.colors.get('text', '#00FF00'),
            fg_color=self.colors.get('accent', '#00FF00'),
            hover_color=self.colors.get('light', '#00AA00'),
            command=self._on_search,
        ).pack(side='left', padx=4)

        # Crear NavList (reemplaza header + data area manual)
        # Definimos columnas visibles y anchos (display keys)
        self.columns = [
            ('ID', 50), ('SKU', 140), ('NOMBRE', 280), ('CATEGORÍA', 140),
            ('TIPO', 110), ('PVP', 85), ('STOCK', 75), ('ESTADO', 95)
        ]

        self.nav_list = VirtualNavList(
            self.container,
            columns=self.columns,
            module_name=module_name,
            keyboard_manager=self.keyboard_mgr,
            on_double_click=self._on_double_click_row,
        )
        self.nav_list.pack(fill='both', expand=True, padx=12, pady=6)

        # pagination state
        self.page_limit = 50
        self.offset = 0
        self.termino = ''
        self.loading = False

        # list of rendered rows count
        self.row_count = 0

        # attempt to access underlying canvas for scroll checks
        self._canvas = getattr(self.nav_list, '_canvas', None)

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
        # Clear NavList rows
        try:
            self.nav_list.clear_items()
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
                try:
                    mapped = self._map_item_to_row(it)
                    self.nav_list.add_item(mapped)
                except Exception:
                    logging.exception('Error añadiendo item a NavList')
            self.row_count += len(items)
            self.offset += len(items)
        except Exception:
            logging.exception('Error cargando página de búsqueda')
        finally:
            self.loading = False

    def _append_row(self, item: dict, index: int):
        # Legacy compatibility: map and add to NavList
        try:
            mapped = self._map_item_to_row(item)
            self.nav_list.add_item(mapped)
        except Exception:
            logging.exception('Error añadiendo fila a NavList (append)')

    def _map_item_to_row(self, item: dict) -> dict:
        # Map DB row to NavList row keys (display headers)
        try:
            estado = item.get('estado', 'Activo')
            mapped = {
                'ID': str(item.get('id') or ''),
                'SKU': item.get('sku') or '',
                'NOMBRE': item.get('nombre') or '',
                'CATEGORÍA': item.get('categoria') or '',
                'TIPO': item.get('tipo') or '',
                'PVP': str(item.get('pvp') or '0.00'),
                'STOCK': str(item.get('stock_actual') or 0),
                'ESTADO': estado,
                # keep original id for callbacks
                '_id': item.get('id')
            }
            return mapped
        except Exception:
            logging.exception('Error mapeando item a row')
            return {}

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

    def _on_double_click_row(self, data: dict):
        # Called by NavList when a row is double-clicked
        try:
            prod_id = data.get('_id') if data.get('_id') is not None else data.get('ID')
            if self.owner and hasattr(self.owner, 'show_crear'):
                try:
                    self.owner.show_crear(producto_id=prod_id)
                except Exception:
                    try:
                        self.owner.show_crear(prod_id)
                    except Exception:
                        logging.exception('Error llamando a show_crear desde BusquedaUI (double click)')
        except Exception:
            logging.exception('Error manejando doble click en NavList')
