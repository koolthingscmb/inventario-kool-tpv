"""UI de Búsqueda Clientes con SearchablePaginatedNavList.

Búsqueda manual (Return) sin scroll infinito.
"""
from typing import Optional, List, Dict, Any
import logging
import customtkinter as ctk
import tkinter as tk

from kool_tpv.modulos.clientes.cliente_service import ClienteService
from kool_tpv.utils.utils import COLOR_BG_TERMINAL, COLOR_MATRIX
from kool_tpv.utils.font_loader import get_font
from kool_tpv.utils.config_loader import load_colors, load_layout_config
from kool_tpv.utils.keyboard_manager import KeyboardManager
from kool_tpv.utils.widgets.searchable_paginated_navlist import SearchablePaginatedNavList
from kool_tpv.utils.factories.button_factory import ButtonFactory
from kool_tpv.base_datos.money_adapter import read_from_db


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

        # Search entry - búsqueda manual con Return
        self.search_var = tk.StringVar()
        self.search_entry = ctk.CTkEntry(
            self.container,
            textvariable=self.search_var,
            placeholder_text='Buscar cliente (nombre, DNI, teléfono)... (pulsa Return)',
            height=36,
            fg_color=self.colors.get('background', COLOR_BG_TERMINAL),
            text_color=self.colors.get('text', COLOR_MATRIX),
            border_width=2,
            border_color=self.colors.get('primary', COLOR_MATRIX),
            font=get_font('entry', module=self.module_name)
        )
        self.search_entry.pack(fill='x', padx=12, pady=(12, 6))
        self.search_entry.bind('<Return>', lambda e: self._on_search())

        # Barra de filtros horizontal
        filter_frame = ctk.CTkFrame(self.container, fg_color='transparent', height=40)
        filter_frame.pack(fill='x', padx=12, pady=(6, 6))
        filter_frame.pack_propagate(False)

        ctk.CTkLabel(
            filter_frame,
            text='Filtrar por:',
            text_color=self.colors.get('text', COLOR_MATRIX),
            font=get_font('label', module=self.module_name)
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
            hover_color=self.colors.get('buttons', {}).get('primary', {}).get('hover', self.colors.get('secondary', '#00AA00'))
        ).pack(side='left', padx=4)

        ctk.CTkCheckBox(
            estado_frame,
            text='Tesoro Inactivo',
            variable=self.check_tesoro_inactivo,
            text_color=self.colors.get('text', COLOR_MATRIX),
            fg_color=self.colors.get('primary', COLOR_MATRIX),
            hover_color=self.colors.get('buttons', {}).get('primary', {}).get('hover', self.colors.get('secondary', '#00AA00'))
        ).pack(side='left', padx=4)

        # Botón Buscar
        self.btn_buscar = ButtonFactory.create_button(
            parent=filter_frame,
            text='BUSCAR',
            command=self._on_search,
            style_key='action_primary'
        )
        self.btn_buscar.pack(side='right', padx=12)

        # Crear SearchablePaginatedNavList (columnas según el servicio existente)
        columns = [
            ('id', 50, 'ID'),
            ('nombre', 300, 'NOMBRE', True),
            ('telefono', 140, 'TELÉFONO'),
            ('tesoro_total', 100, 'TESORO'),
            ('nivel_nombre', 120, 'NIVEL'),
            ('fecha_alta', 120, 'ALTA')
        ]

        self.search_list = SearchablePaginatedNavList(
            parent=self.container,
            columns=columns,
            search_function=self._buscar_clientes,
            map_function=self._map_cliente,
            module_name=self.module_name,
            page_limit=50,
            on_double_click=self._on_nav_double_click,
            keyboard_manager=self.keyboard_manager,
            layout_config=load_layout_config()
        )
        self.search_list.pack(fill='both', expand=True, padx=12, pady=6)

        # Auto-focus
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
            logging.exception('Error ejecutando búsqueda clientes')

    def _buscar_clientes(self, texto: str):
        """Función de búsqueda para SearchablePaginatedNavList - usa ClienteService."""
        try:
            clientes = self.service.buscar_clientes(texto)

            # Filtrar por tesoro si es necesario (en memoria, solo 50 registros)
            filtrar_tesoro_activo = None
            try:
                if self.check_tesoro_activo.get() and not self.check_tesoro_inactivo.get():
                    filtrar_tesoro_activo = True
                elif not self.check_tesoro_activo.get() and self.check_tesoro_inactivo.get():
                    filtrar_tesoro_activo = False
            except Exception:
                pass

            if filtrar_tesoro_activo is not None:
                # Si el servicio no devuelve fidelidad_activa, mostrar todos
                # (el servicio actual no tiene este campo)
                pass

            return clientes[:50] if clientes else []
        except Exception:
            logging.exception('Error en _buscar_clientes')
            return []

    def _map_cliente(self, cliente: dict) -> dict:
        """Mapear cliente a formato de fila para NavList - campos del servicio."""
        try:
            tesoro = cliente.get('tesoro_total', 0)
            
            # Formatear fecha: DD-MM-AA
            fecha_str = cliente.get('fecha_alta') or 'N/A'
            if fecha_str != 'N/A':
                try:
                    # Si viene con hora (YYYY-MM-DD HH:MM:SS), nos quedamos con la parte de la fecha
                    parts = fecha_str.split(' ')
                    date_part = parts[0]
                    # Si el formato es YYYY-MM-DD
                    if '-' in date_part:
                        y, m, d = date_part.split('-')
                        fecha_str = f"{d}-{m}-{y[2:]}"
                except Exception:
                    pass

            return {
                'id': str(cliente.get('id') or ''),
                'nombre': cliente.get('nombre') or '',
                'telefono': cliente.get('telefono') or '',
                'tesoro_total': f"{tesoro:.2f}€" if isinstance(tesoro, (int, float)) else f"{tesoro}€",
                'nivel_nombre': cliente.get('nivel_nombre') or 'Forastero',
                'fecha_alta': fecha_str,
                '_id': cliente.get('id')
            }
        except Exception:
            logging.exception('Error mapeando cliente')
            return {}

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
                canvas = getattr(self.nav_list, '_canvas', None) if hasattr(self, 'nav_list') else None
                if canvas is not None:
                    canvas.focus_set()
                elif hasattr(self, 'nav_list') and self.nav_list is not None:
                    self.nav_list.focus_set()
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
                cliente_id = data.get('_id') or data.get('id')
            if cliente_id and self.owner and hasattr(self.owner, 'show_editar_cliente'):
                try:
                    self.owner.show_editar_cliente(int(cliente_id))
                except Exception:
                    logging.exception('Error llamando show_editar_cliente desde on_double_click')
        except Exception:
            logging.exception('Error en _on_nav_double_click')
