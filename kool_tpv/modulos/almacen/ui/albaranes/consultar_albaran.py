"""UI de Consultar Albaranes - Filtros y listado scroll.

Estructura similar a BusquedaUI adaptada para albaranes.
Filtros: proveedor (SearchableCombo) + fechas (botones preset + entries manuales).
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
from kool_tpv.utils.widgets.nav_list import NavList
from kool_tpv.utils.factories.button_factory import ButtonFactory


class ConsultarAlbaranUI:
    def __init__(self, parent, db=None, owner=None, keyboard_manager=None, module_name: str = 'almacen'):
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

        # Fila de filtros
        filter_frame = ctk.CTkFrame(self.container, fg_color='transparent', height=50)
        filter_frame.pack(fill='x', padx=12, pady=(12, 6))
        filter_frame.pack_propagate(False)

        # Filtro proveedor
        ctk.CTkLabel(
            filter_frame,
            text='Filtrar Albarán por Proveedor:',
            text_color=self.colors.get('text', COLOR_MATRIX),
            font=get_font('label', module=self.module_name)
        ).pack(side='left', padx=(0, 8))

        self.cb_proveedor = SearchableCombo(
            filter_frame,
            width=200
        )
        self.cb_proveedor.pack(side='left', padx=(0, 16))

        # Botones preset fecha
        self.btn_hoy = ButtonFactory.create_button(
            parent=filter_frame,
            text='HOY',
            command=self._preset_hoy,
            style_key="mini_success"
        )
        self.btn_hoy.pack(side='left', padx=4)

        self.btn_7dias = ButtonFactory.create_button(
            parent=filter_frame,
            text='7 DÍAS',
            command=self._preset_7dias,
            style_key="mini_info"
        )
        self.btn_7dias.pack(side='left', padx=4)

        self.btn_mes = ButtonFactory.create_button(
            parent=filter_frame,
            text='MES',
            command=self._preset_mes,
            style_key="mini_special"
        )
        self.btn_mes.pack(side='left', padx=4)

        # Entries fecha manual
        ctk.CTkLabel(
            filter_frame,
            text='Desde:',
            text_color=self.colors.get('text', COLOR_MATRIX),
            font=get_font('label', module=self.module_name)
        ).pack(side='left', padx=(16, 4))

        self.e_desde = ctk.CTkEntry(
            filter_frame,
            placeholder_text='DD-MM-YYYY',
            width=120,
            **default_entry_kw
        )
        self.e_desde.pack(side='left', padx=4)

        ctk.CTkLabel(
            filter_frame,
            text='Hasta:',
            text_color=self.colors.get('text', COLOR_MATRIX),
            font=get_font('label', module=self.module_name)
        ).pack(side='left', padx=(8, 4))

        self.e_hasta = ctk.CTkEntry(
            filter_frame,
            placeholder_text='DD-MM-YYYY',
            width=120,
            **default_entry_kw
        )
        self.e_hasta.pack(side='left', padx=4)

        # Botón APLICAR
        self.btn_aplicar = ButtonFactory.create_button(
            parent=filter_frame,
            text='APLICAR',
            command=self._aplicar_filtros,
            style_key="mini_warning"
        )
        self.btn_aplicar.pack(side='left', padx=(16, 0))

        # Hacer que Tab/Shift-Tab recorran todos los elementos de la fila
        try:
            # entradas y searchablecombo entry
            try:
                self.cb_proveedor.entry.bind('<Tab>', self._focus_next)
                self.cb_proveedor.entry.bind('<Shift-Tab>', self._focus_prev)
            except Exception:
                pass
            try:
                self.e_desde.bind('<Tab>', self._focus_next)
                self.e_desde.bind('<Shift-Tab>', self._focus_prev)
            except Exception:
                pass
            try:
                self.e_hasta.bind('<Tab>', self._focus_next)
                self.e_hasta.bind('<Shift-Tab>', self._focus_prev)
            except Exception:
                pass

            # botones: permitir foco via Tab y Enter (sin override visual de foco)
            try:
                for btn in (self.btn_hoy, self.btn_7dias, self.btn_mes, self.btn_aplicar):
                    try:
                        btn.bind('<Tab>', self._focus_next)
                        btn.bind('<Shift-Tab>', self._focus_prev)
                        # Enter should trigger the button
                        btn.bind('<Return>', lambda e, b=btn: (b.invoke() if hasattr(b, 'invoke') else None) or 'break')
                    except Exception:
                        pass
            except Exception:
                pass
        except Exception:
            pass

        # Crear NavList para mostrar resultados (reemplaza header + data_frame)
        self.columns = [
            ('ID', 50), ('FECHA', 100), ('PROVEEDOR', 200),
            ('CANT. PROD.', 100), ('TOTAL NETO', 100), ('TOTAL IVA', 100), ('TOTAL', 100)
        ]

        self.nav_list = NavList(
            self.container,
            columns=self.columns,
            module_name=module_name,
            keyboard_manager=self.keyboard_mgr,
            on_double_click=self._on_double_click_row,
        )
        self.nav_list.pack(fill='both', expand=True, padx=12, pady=6)

        # Cargar opciones proveedor
        self._load_proveedores()

        # Cargar inicial (todos)
        self._preset_mes()  # Por defecto último mes
        self._aplicar_filtros()

    def get_widget(self):
        return self.container

    def _focus_next(self, event):
        try:
            nxt = event.widget.tk_focusNext()
            if nxt:
                try:
                    nxt.focus_set()
                except Exception:
                    try:
                        nxt.focus()
                    except Exception:
                        pass
        except Exception:
            logging.exception('Error moviendo foco al siguiente widget')
        return 'break'

    def _focus_prev(self, event):
        try:
            prev = event.widget.tk_focusPrev()
            if prev:
                try:
                    prev.focus_set()
                except Exception:
                    try:
                        prev.focus()
                    except Exception:
                        pass
        except Exception:
            logging.exception('Error moviendo foco al widget anterior')
        return 'break'

    # _button_focus_in and _button_focus_out removed to avoid manual focus color overrides

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

    def _preset_hoy(self):
        """Rellenar entries con fecha de hoy."""
        hoy = datetime.now().strftime('%d-%m-%Y')
        self.e_desde.delete(0, 'end')
        self.e_desde.insert(0, hoy)
        self.e_hasta.delete(0, 'end')
        self.e_hasta.insert(0, hoy)

    def _preset_7dias(self):
        """Rellenar entries con últimos 7 días."""
        hoy = datetime.now()
        hace_7 = hoy - timedelta(days=7)
        self.e_desde.delete(0, 'end')
        self.e_desde.insert(0, hace_7.strftime('%d-%m-%Y'))
        self.e_hasta.delete(0, 'end')
        self.e_hasta.insert(0, hoy.strftime('%d-%m-%Y'))

    def _preset_mes(self):
        """Rellenar entries con último mes (30 días)."""
        hoy = datetime.now()
        hace_30 = hoy - timedelta(days=30)
        self.e_desde.delete(0, 'end')
        self.e_desde.insert(0, hace_30.strftime('%d-%m-%Y'))
        self.e_hasta.delete(0, 'end')
        self.e_hasta.insert(0, hoy.strftime('%d-%m-%Y'))

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

            # Convertir fechas DD-MM-YYYY a YYYY-MM-DD
            fecha_desde = None
            fecha_hasta = None

            try:
                desde_raw = (self.e_desde.get() or '').strip()
                if desde_raw:
                    partes = desde_raw.split('-')
                    if len(partes) == 3:
                        fecha_desde = f"{partes[2]}-{partes[1]}-{partes[0]}"  # YYYY-MM-DD
            except Exception:
                logging.warning('Error parseando fecha desde')

            try:
                hasta_raw = (self.e_hasta.get() or '').strip()
                if hasta_raw:
                    partes = hasta_raw.split('-')
                    if len(partes) == 3:
                        fecha_hasta = f"{partes[2]}-{partes[1]}-{partes[0]}"  # YYYY-MM-DD
            except Exception:
                logging.warning('Error parseando fecha hasta')

            # Llamar servicio
            albaranes = self.albaran_service.filtrar_albaranes(
                proveedor_id=proveedor_id,
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta,
                limit=200
            )

            # Renderizar filas en NavList
            for i, alb in enumerate(albaranes):
                try:
                    mapped = self._map_albaran_to_row(alb)
                    self.nav_list.add_item(mapped)
                except Exception:
                    logging.exception('Error añadiendo albarán a NavList')

        except Exception:
            logging.exception('Error aplicando filtros albaranes')

    def _append_row(self, albaran: dict, index: int):
        """Compat wrapper: añade albarán a NavList."""
        try:
            mapped = self._map_albaran_to_row(albaran)
            self.nav_list.add_item(mapped)
        except Exception:
            logging.exception('Error añadiendo fila a NavList (append)')

        row.bind('<Enter>', on_enter)
        row.bind('<Leave>', on_leave)

        # Double-click: abrir detalle
        def on_double(e, alb_id=albaran.get('id')):
            try:
                if self.owner and hasattr(self.owner, 'show_detalle_albaran'):
                    try:
                        self.owner.show_detalle_albaran(alb_id)
                    except Exception:
                        logging.exception(f'Error ejecutando owner.show_detalle_albaran for ID={alb_id}')
                else:
                    logging.warning(f'Owner no disponible o sin método show_detalle_albaran')
            except Exception:
                logging.exception(f'Error abriendo detalle albarán ID={alb_id}')

        row.bind('<Double-Button-1>', on_double)

        # Columnas
        col_widths = [50, 100, 200, 100, 100, 100, 100]
        values = [
            str(albaran.get('id', '')),
            albaran.get('fecha', ''),
            albaran.get('proveedor_nombre', ''),
            str(albaran.get('cant_productos', 0)),
            f"{albaran.get('total_neto', 0.0):.2f}€",
            f"{albaran.get('total_iva', 0.0):.2f}€",
            f"{albaran.get('total', 0.0):.2f}€"
        ]

        x = 6
        for i, v in enumerate(values):
            lbl = ctk.CTkLabel(
                row,
                text=v,
                text_color=self.colors.get('text', COLOR_MATRIX),
                fg_color='transparent',
                anchor='w',
                font=FONT_TERMINAL,
                width=col_widths[i] - 8,
                height=28
            )
            lbl.place(x=x, y=2)
            lbl.bind('<Double-Button-1>', on_double)
            lbl.bind('<Enter>', on_enter)
            lbl.bind('<Leave>', on_leave)
            x += col_widths[i]

        # Separador inferior
        try:
            sep = ctk.CTkFrame(self.data_frame, fg_color='#2a2a2a', height=1)
            sep.pack(fill='x')
        except Exception:
            pass

    def _map_albaran_to_row(self, albaran: dict) -> dict:
        try:
            mapped = {
                'ID': str(albaran.get('id', '')),
                'FECHA': albaran.get('fecha', ''),
                'PROVEEDOR': albaran.get('proveedor_nombre', ''),
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
            if self.owner and hasattr(self.owner, 'show_detalle_albaran'):
                try:
                    self.owner.show_detalle_albaran(alb_id)
                except Exception:
                    logging.exception('Error llamando a show_detalle_albaran desde ConsultarAlbaranUI')
        except Exception:
            logging.exception('Error manejando doble click en NavList (albaranes)')
