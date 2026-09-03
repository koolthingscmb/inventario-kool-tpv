"""UI de Consultar Albaranes - Filtros y listado scroll.

Estructura similar a BusquedaUI adaptada para albaranes.
Filtros: proveedor (SearchableCombo) + fechas (DatePickerEntry).
"""
from typing import Optional
import logging
from datetime import datetime, timedelta
import tkinter as tk
import customtkinter as ctk

from kool_tpv.base_datos.albaran_service import AlbaranService
from kool_tpv.base_datos.proveedor_service import ProveedorService
from kool_tpv.utils.utils import COLOR_BG_TERMINAL, COLOR_MATRIX
from kool_tpv.utils.font_loader import get_font
from kool_tpv.utils.widgets.searchable_combo import SearchableCombo
from kool_tpv.utils.widgets.date_picker_entry import DatePickerEntry
from kool_tpv.utils.widgets.virtual_nav_list import VirtualNavList
from kool_tpv.utils.factories.button_factory import ButtonFactory
from kool_tpv.utils.keyboard_nav_mixin import KeyboardNavigableMixin


class ConsultarAlbaranUI(KeyboardNavigableMixin):
    def __init__(self, parent, db=None, owner=None, keyboard_manager=None, module_name: str = 'almacen'):
        KeyboardNavigableMixin.__init__(self)
        self.parent = parent
        self.db = db
        self.owner = owner
        self.keyboard_mgr = keyboard_manager
        self.module_name = module_name
        self.albaran_service = AlbaranService(db)
        self.proveedor_service = ProveedorService(db)
        from kool_tpv.utils.config_loader import load_colors
        try:
            self.colors = load_colors('almacen')
        except Exception:
            self.colors = {'text': COLOR_MATRIX, 'primary': COLOR_MATRIX, 'secondary': COLOR_MATRIX, 'accent': COLOR_MATRIX}

        self.container = ctk.CTkFrame(self.parent, fg_color=self.colors.get('background', COLOR_BG_TERMINAL))

        default_entry_kw = {
            'fg_color': self.colors.get('background', COLOR_BG_TERMINAL),
            'text_color': self.colors.get('text', COLOR_MATRIX),
            'border_color': self.colors.get('border', self.colors.get('primary')),
            'height': 32
        }
        # color palette from config removed: buttons now created via ButtonFactory styles

        # Fila de filtros (dividida en dos filas: top + bottom)
        filter_frame = ctk.CTkFrame(self.container, fg_color='transparent', height=50)
        filter_frame.pack(fill='x', padx=12, pady=(12, 6))
        filter_frame.pack_propagate(False)

        # Single row inside filter_frame
        row = ctk.CTkFrame(filter_frame, fg_color='transparent')
        row.pack(fill='x')

        # Filtro proveedor
        ctk.CTkLabel(
            row,
            text='Filtrar Albarán por Proveedor:',
            text_color=self.colors.get('text', COLOR_MATRIX),
            font=get_font('label', module=self.module_name)
        ).pack(side='left', padx=(0, 8))

        self.cb_proveedor = SearchableCombo(
            row,
            width=200
        )
        self.cb_proveedor.pack(side='left', padx=(0, 16))

        # Fecha Desde
        ctk.CTkLabel(
            row,
            text='Desde:',
            text_color=self.colors.get('text', COLOR_MATRIX),
            font=get_font('label', module=self.module_name)
        ).pack(side='left', padx=(8, 4))

        self.date_desde = DatePickerEntry(
            row,
            module_name=self.module_name,
            width=140,
            allow_future=False,
            default_mode='first_day_of_month'
        )
        self.date_desde.pack(side='left', padx=4)

        # Fecha Hasta
        ctk.CTkLabel(
            row,
            text='Hasta:',
            text_color=self.colors.get('text', COLOR_MATRIX),
            font=get_font('label', module=self.module_name)
        ).pack(side='left', padx=(8, 4))

        self.date_hasta = DatePickerEntry(
            row,
            module_name=self.module_name,
            width=140,
            allow_future=False,
            default_mode='today'
        )
        self.date_hasta.pack(side='left', padx=4)

        # Botón APLICAR
        self.btn_aplicar = ButtonFactory.create_button(
            parent=row,
            text='APLICAR',
            command=self._aplicar_filtros,
            style_key="action_confirm",
            module='almacen',
            palette_key='primary'
        )
        self.btn_aplicar.pack(side='left', padx=(16, 0))

        # Crear NavList para mostrar resultados (reemplaza header + data_frame)
        self.columns = [
            ('ID', 50), ('FECHA', 100), ('PROVEEDOR', 360),
            ('TIPO', 80), ('CANT. PROD.', 160), ('TOTAL NETO', 180), ('TOTAL IVA', 180), ('TOTAL', 180)
        ]

        self.nav_list = VirtualNavList(
            self.container,
            columns=self.columns,
            module_name=module_name,
            keyboard_manager=self.keyboard_mgr,
            on_double_click=self._on_double_click_row,
        )
        self.nav_list.pack(fill='both', expand=True, padx=12, pady=6)

        # Cargar opciones proveedor
        self._load_proveedores()

        # Registrar widgets navegables para KeyboardNavigableMixin
        try:
            self.register_navigable_widget(self.cb_proveedor.entry)
        except Exception:
            pass
        try:
            self.register_navigable_widget(self.date_desde.entry)
        except Exception:
            pass
        try:
            self.register_navigable_widget(self.date_hasta.entry)
        except Exception:
            pass
        try:
            self.register_navigable_widget(self.btn_aplicar, self._aplicar_filtros)
        except Exception:
            pass
        try:
            self.set_nav_enter_callback(self._aplicar_filtros)
        except Exception:
            pass

        # Cargar inicial (todos)
        self._aplicar_filtros()

    def get_widget(self):
        return self.container


    def _load_proveedores(self):
        """Cargar lista de proveedores en SearchableCombo."""
        try:
            proveedores = self.proveedor_service.get_all_proveedores()
            opts = [(0, 'Todos los proveedores')]  # opción "Todos"
            for p in proveedores or []:
                opts.append((p.get('id'), p.get('nombre', 'Sin nombre')))
            self.cb_proveedor.set_options(opts)
            # No prellenar con "Todos los proveedores" — dejar vacío y dar foco
            try:
                self.cb_proveedor.entry.focus_set()
            except Exception:
                pass
        except Exception:
            logging.exception('Error cargando proveedores')

    # Preset date methods removed: use DatePickerEntry widgets instead

    def _aplicar_filtros(self):
        """Ejecutar filtro y refrescar lista."""
        try:
            # Limpiar NavList
            try:
                self.nav_list.clear_items()
            except Exception:
                pass

            # Obtener filtros
            proveedor_id = self.cb_proveedor.get_id()
            if proveedor_id == 0:  # "Todos"
                proveedor_id = None

            # Obtener fechas directamente desde DatePickerEntry (devuelve YYYY-MM-DD)
            fecha_desde = None
            fecha_hasta = None
            try:
                fecha_desde = (self.date_desde.get() or None)
            except Exception:
                fecha_desde = None
                logging.warning('Error obteniendo fecha_desde desde DatePickerEntry')

            try:
                fecha_hasta = (self.date_hasta.get() or None)
            except Exception:
                fecha_hasta = None
                logging.warning('Error obteniendo fecha_hasta desde DatePickerEntry')

            # Llamar servicio
            albaranes = self.albaran_service.filtrar_albaranes(
                proveedor_id=proveedor_id,
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta,
                limit=200
            )

            # Renderizar filas en NavList
            rows = []
            for alb in albaranes:
                try:
                    mapped = self._map_albaran_to_row(alb)
                    rows.append(mapped)
                except Exception:
                    logging.exception('Error mapeando albarán a fila')
            self.nav_list.set_items(rows)

        except Exception:
            logging.exception('Error aplicando filtros albaranes')

    def _append_row(self, albaran: dict, index: int):
        """Compat wrapper: añade albarán a NavList."""
        try:
            mapped = self._map_albaran_to_row(albaran)
            current = list(getattr(self.nav_list, '_all_data', []))
            current.append(mapped)
            self.nav_list.set_items(current)
        except Exception:
            logging.exception('Error añadiendo fila a NavList (append)')
        return

    def _map_albaran_to_row(self, albaran: dict) -> dict:
        try:
            mapped = {
                'ID': str(albaran.get('id', '')),
                'FECHA': albaran.get('fecha', ''),
                'PROVEEDOR': albaran.get('proveedor_nombre', ''),
                'TIPO': albaran.get('tipo', ''),
                'CANT. PROD.': str(albaran.get('cant_productos', 0)),
                'TOTAL NETO': f"{albaran.get('total_neto', 0.0):.2f}€",
                'TOTAL IVA': f"{albaran.get('total_iva', 0.0):.2f}€",
                'TOTAL': f"{albaran.get('total', 0.0):.2f}€",
                '_id': albaran.get('id')
            }
            return mapped
        except Exception:
            logging.exception('Error mapeando albarán a row')
            return {}

    def _on_double_click_row(self, data: dict):
        try:
            alb_id = data.get('_id') if data.get('_id') is not None else data.get('ID')
            if self.owner and hasattr(self.owner, 'show_entrada_manual'):
                try:
                    self.owner.show_entrada_manual(albaran_id=alb_id)
                except Exception:
                    logging.exception('Error llamando a show_entrada_manual desde ConsultarAlbaranUI')
        except Exception:
            logging.exception('Error manejando doble click en NavList (albaranes)')
