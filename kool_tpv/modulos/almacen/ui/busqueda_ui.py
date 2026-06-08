"""UI de Búsqueda con SearchablePaginatedNavList.

Búsqueda manual (Return) sin scroll infinito.
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
from kool_tpv.utils.widgets.searchable_paginated_navlist import SearchablePaginatedNavList


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

        # Search entry - búsqueda manual con Return
        self.search_var = tk.StringVar()
        self.search_entry = ctk.CTkEntry(
            self.container,
            textvariable=self.search_var,
            placeholder_text='Buscar... (pulsa Return)',
            height=36,
            fg_color=self.colors.get('background', '#1a1a1a'),
            text_color=self.colors.get('text', '#00FF00'),
            border_width=2,
            border_color=self.colors.get('border', '#00FF00'),
        )
        self.search_entry.pack(fill='x', padx=12, pady=(12, 6))
        self.search_entry.bind('<Return>', lambda e: self._on_search())

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
        self.cat_combo.pack(side='left', padx=(0, 12))

        # Label Tipos
        ctk.CTkLabel(filter_frame, text='Tipos:', text_color=self.colors.get('text', '#00FF00'), font=get_font('label', module=self.module_name)).pack(side='left', padx=(0, 4))
        self.tipo_combo = SearchableCombo(
            filter_frame,
            options=[(t['id'], t['nombre']) for t in tipos],
            width=160
        )
        self.tipo_combo.set('Todos')
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
        ).pack(side='left', padx=4)
        ctk.CTkCheckBox(
            estado_frame,
            text='Sin Stock',
            variable=self.check_sin_stock,
            text_color=self.colors.get('text', '#00FF00'),
            fg_color=self.colors.get('secondary', '#00FF00'),
            hover_color=self.colors.get('light', '#00AA00'),
        ).pack(side='left', padx=4)
        ctk.CTkCheckBox(
            estado_frame,
            text='Archivados',
            variable=self.check_archivado,
            text_color=self.colors.get('text', '#00FF00'),
            fg_color=self.colors.get('accent', '#00FF00'),
            hover_color=self.colors.get('light', '#00AA00'),
        ).pack(side='left', padx=4)

        # Botón Buscar
        from kool_tpv.utils.factories.button_factory import ButtonFactory
        self.btn_buscar = ButtonFactory.create_button(
            parent=filter_frame,
            text='BUSCAR',
            command=self._on_search,
            style_key='action_primary'
        )
        self.btn_buscar.pack(side='right', padx=12)

        # Crear SearchablePaginatedNavList
        columns = [
            ('id', 50, 'ID'),
            ('sku', 140, 'SKU'),
            ('nombre', 280, 'NOMBRE'),
            ('categoria', 140, 'CATEGORÍA'),
            ('tipo', 110, 'TIPO'),
            ('pvp', 85, 'PVP'),
            ('stock_actual', 75, 'STOCK'),
            ('estado', 95, 'ESTADO'),
        ]

        from kool_tpv.utils.config_loader import load_layout_config

        self.search_list = SearchablePaginatedNavList(
            parent=self.container,
            columns=columns,
            search_function=self._buscar_productos,
            map_function=self._map_producto,
            module_name=module_name,
            page_limit=50,
            on_double_click=self._on_double_click_row,
            keyboard_manager=self.keyboard_mgr,
            layout_config=load_layout_config(),
        )
        self.search_list.pack(fill='both', expand=True, padx=12, pady=6)

        # Auto-focus en search entry
        try:
            self.container.after(100, lambda: self.search_entry.focus_set())
        except Exception:
            pass

    def get_widget(self):
        return self.container

    def _on_search(self):
        """Disparar búsqueda con filtros actuales."""
        termino = (self.search_var.get() or '').strip()
        try:
            self.search_list.search(termino)
        except Exception:
            logging.exception('Error ejecutando búsqueda')

    def _buscar_productos(self, texto: str) -> List[dict]:
        """Función de búsqueda para SearchablePaginatedNavList."""
        try:
            # Recoger filtros activos
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
            if getattr(self, 'check_activo', None) and self.check_activo.get():
                estados.append('activo')
            if getattr(self, 'check_sin_stock', None) and self.check_sin_stock.get():
                estados.append('sin_stock')
            if getattr(self, 'check_archivado', None) and self.check_archivado.get():
                estados.append('archivado')

            return self.service.buscar_productos_paginados(
                termino_busqueda=texto,
                categoria_id=cat_id,
                tipo_id=tipo_id,
                estados=estados if estados else None,
                limit=50,
                offset=0
            )
        except Exception:
            logging.exception('Error en _buscar_productos')
            return []

    def _map_producto(self, item: dict) -> dict:
        """Mapear producto a formato de fila para NavList."""
        try:
            estado = item.get('estado', 'Activo')
            return {
                'id': str(item.get('id') or ''),
                'sku': item.get('sku') or '',
                'nombre': item.get('nombre') or '',
                'categoria': item.get('categoria') or '',
                'tipo': item.get('tipo') or '',
                'pvp': str(item.get('pvp') or '0.00'),
                'stock_actual': str(item.get('stock_actual') or 0),
                'estado': estado,
                '_id': item.get('id')
            }
        except Exception:
            logging.exception('Error mapeando producto')
            return {}

    def _on_double_click_row(self, data: dict):
        """Manejar doble click en fila de producto."""
        try:
            prod_id = data.get('_id') if data.get('_id') is not None else data.get('id')
            if self.owner and hasattr(self.owner, 'show_crear'):
                try:
                    self.owner.show_crear(producto_id=prod_id)
                except Exception:
                    try:
                        self.owner.show_crear(prod_id)
                    except Exception:
                        logging.exception('Error llamando a show_crear desde BusquedaUI')
        except Exception:
            logging.exception('Error manejando doble click en NavList')
