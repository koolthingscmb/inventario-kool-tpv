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
from kool_tpv.utils.utils import COLOR_BG_TERMINAL, COLOR_MATRIX, FONT_TERMINAL
from kool_tpv.utils.widgets.searchable_combo import SearchableCombo


class ConsultarAlbaranUI:
    def __init__(self, parent, db=None, owner=None):
        self.parent = parent
        self.db = db
        self.owner = owner
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
        _buttons_cfg = self.colors.get('buttons', {})
        _primary_btn = _buttons_cfg.get('primary', {})
        _secondary_btn = _buttons_cfg.get('secondary', {})
        _accent_btn = _buttons_cfg.get('accent', {})

        # Fila de filtros
        filter_frame = ctk.CTkFrame(self.container, fg_color='transparent', height=50)
        filter_frame.pack(fill='x', padx=12, pady=(12, 6))
        filter_frame.pack_propagate(False)

        # Filtro proveedor
        ctk.CTkLabel(
            filter_frame,
            text='Filtrar Albarán por Proveedor:',
            text_color=self.colors.get('text', COLOR_MATRIX),
            font=FONT_TERMINAL
        ).pack(side='left', padx=(0, 8))

        self.cb_proveedor = SearchableCombo(
            filter_frame,
            width=200
        )
        self.cb_proveedor.pack(side='left', padx=(0, 16))

        # Botones preset fecha
        self.btn_hoy = ctk.CTkButton(
            filter_frame,
            text='HOY',
            width=70,
            height=32,
            fg_color=_primary_btn.get('bg', '#2ecc71'),
            hover_color=_primary_btn.get('hover', '#27ae60'),
            text_color=_primary_btn.get('text', self.colors.get('text', COLOR_MATRIX)),
            command=self._preset_hoy
        )
        self.btn_hoy.pack(side='left', padx=4)

        self.btn_7dias = ctk.CTkButton(
            filter_frame,
            text='7 DÍAS',
            width=70,
            height=32,
            fg_color=_secondary_btn.get('bg', '#3498db'),
            hover_color=_secondary_btn.get('hover', '#2980b9'),
            text_color=_secondary_btn.get('text', self.colors.get('text', COLOR_MATRIX)),
            command=self._preset_7dias
        )
        self.btn_7dias.pack(side='left', padx=4)

        self.btn_mes = ctk.CTkButton(
            filter_frame,
            text='MES',
            width=70,
            height=32,
            fg_color=_accent_btn.get('bg', '#9b59b6'),
            hover_color=_accent_btn.get('hover', '#8e44ad'),
            text_color=_accent_btn.get('text', self.colors.get('text', COLOR_MATRIX)),
            command=self._preset_mes
        )
        self.btn_mes.pack(side='left', padx=4)

        # Entries fecha manual
        ctk.CTkLabel(
            filter_frame,
            text='Desde:',
            text_color=self.colors.get('text', COLOR_MATRIX),
            font=FONT_TERMINAL
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
            font=FONT_TERMINAL
        ).pack(side='left', padx=(8, 4))

        self.e_hasta = ctk.CTkEntry(
            filter_frame,
            placeholder_text='DD-MM-YYYY',
            width=120,
            **default_entry_kw
        )
        self.e_hasta.pack(side='left', padx=4)

        # Botón APLICAR
        self.btn_aplicar = ctk.CTkButton(
            filter_frame,
            text='APLICAR',
            width=100,
            height=32,
            fg_color=_accent_btn.get('bg', '#e67e22'),
            hover_color=_accent_btn.get('hover', '#d35400'),
            text_color=_accent_btn.get('text', self.colors.get('text', COLOR_MATRIX)),
            command=self._aplicar_filtros
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

            # botones: permitir foco via Tab y mostrar efecto visual al recibir foco
            try:
                # map buttons to palette hover colors
                btn_hover_map = (
                    (self.btn_hoy, _primary_btn.get('hover', '#27ae60')),
                    (self.btn_7dias, _secondary_btn.get('hover', '#2980b9')),
                    (self.btn_mes, _accent_btn.get('hover', '#8e44ad')),
                    (self.btn_aplicar, _accent_btn.get('hover', '#d35400')),
                )
                for btn, hover in btn_hover_map:
                    try:
                        btn.bind('<Tab>', self._focus_next)
                        btn.bind('<Shift-Tab>', self._focus_prev)
                        btn.bind('<FocusIn>', lambda e, b=btn, hc=hover: self._button_focus_in(b, hc))
                        btn.bind('<FocusOut>', lambda e, b=btn: self._button_focus_out(b))
                        # Enter should trigger the button
                        btn.bind('<Return>', lambda e, b=btn: (b.invoke() if hasattr(b, 'invoke') else None) or 'break')
                    except Exception:
                        pass
            except Exception:
                pass
        except Exception:
            pass

        # Headers tabla
        hdr_frame = ctk.CTkFrame(self.container, fg_color='transparent', height=32)
        hdr_frame.pack(fill='x', padx=12, pady=(0, 2))
        hdr_frame.pack_propagate(False)

        # Anchos columnas: ID (50), Fecha (100), Proveedor (200), Cant.Prod (100), Total Neto (100), Total IVA (100), Total (100)
        col_widths = [50, 100, 200, 100, 100, 100, 100]
        headers = ['ID', 'FECHA', 'PROVEEDOR', 'CANT. PROD.', 'TOTAL NETO', 'TOTAL IVA', 'TOTAL']

        for i, h in enumerate(headers):
            lbl = ctk.CTkLabel(
                hdr_frame,
                text=h,
                text_color=self.colors.get('text', COLOR_MATRIX),
                fg_color=self.colors.get('bg_dark', '#1a1a1a'),
                anchor='w',
                font=('Courier New', 13, 'bold'),
                width=col_widths[i] - 6,
                height=28,
                corner_radius=0
            )
            lbl.place(x=sum(col_widths[:i]) + 6, y=2)

            # Separador vertical
            try:
                sep = ctk.CTkFrame(hdr_frame, fg_color=self.colors.get('bg_medium', '#2a2a2a'), width=1)
                sep.place(x=sum(col_widths[:i+1]), y=2, height=28)
            except Exception:
                pass

        # Data area scroll
        self.data_frame = ctk.CTkScrollableFrame(self.container, fg_color=self.colors.get('background', COLOR_BG_TERMINAL))
        self.data_frame.pack(fill='both', expand=True, padx=12, pady=6)

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

    def _button_focus_in(self, btn, hover_color=None):
        try:
            # store original color
            if not hasattr(btn, '_orig_fg'):
                try:
                    btn._orig_fg = btn.cget('fg_color')
                except Exception:
                    btn._orig_fg = None
            # apply hover color if provided
            if hover_color:
                try:
                    btn.configure(fg_color=hover_color)
                except Exception:
                    pass
        except Exception:
            pass

    def _button_focus_out(self, btn):
        try:
            if hasattr(btn, '_orig_fg') and btn._orig_fg is not None:
                try:
                    btn.configure(fg_color=btn._orig_fg)
                except Exception:
                    pass
        except Exception:
            pass

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
            # Limpiar data_frame
            for w in list(self.data_frame.winfo_children()):
                try:
                    w.destroy()
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

            # Renderizar filas
            for i, alb in enumerate(albaranes):
                self._append_row(alb, i)

        except Exception:
            logging.exception('Error aplicando filtros albaranes')

    def _append_row(self, albaran: dict, index: int):
        """Añadir fila a la lista scroll."""
        row_bg = self.colors.get('bg_dark', '#1a1a1a') if (index % 2 == 0) else self.colors.get('bg_medium', '#121212')
        row = ctk.CTkFrame(self.data_frame, fg_color=row_bg, height=30)
        row.pack(fill='x', pady=0)

        # Hover effect
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
