"""UI de Entrada Manual de albaranes."""
from typing import Optional, List
import logging
import tkinter as tk
from datetime import date
import customtkinter as ctk
from kool_tpv.utils.factories.button_factory import ButtonFactory

from kool_tpv.base_datos.albaran_service import AlbaranService
from kool_tpv.base_datos.proveedor_service import ProveedorService
from kool_tpv.utils.utils import COLOR_BG_TERMINAL, COLOR_MATRIX
from kool_tpv.utils.font_loader import get_font
from kool_tpv.utils.widgets.searchable_combo import SearchableCombo
from kool_tpv.utils.widgets.virtual_nav_list import VirtualNavList
from kool_tpv.utils.custom_dialog import show_success
from kool_tpv.utils.config_loader import create_action_button

logger = logging.getLogger(__name__)





class EntradaManualUI:
    def __init__(self, parent, db=None, tipo='ENTRADA', module_name: str = 'almacen', keyboard_manager=None, albaran_id=None):
        self.parent = parent
        self.db = db
        self.tipo = tipo  # 'ENTRADA', 'SALIDA', 'DEVOLUCION'
        self.module_name = module_name
        self.keyboard_mgr = keyboard_manager
        self.albaran_id = albaran_id  # None = nuevo albarán, int = edición
        from kool_tpv.utils.config_loader import load_colors
        try:
            self.colors = load_colors(module_name)
        except Exception:
            self.colors = {'text': COLOR_MATRIX, 'primary': COLOR_MATRIX, 'secondary': COLOR_MATRIX, 'accent': COLOR_MATRIX}
        self.albaran_service = AlbaranService(db)
        self.proveedor_service = ProveedorService(db)
        from kool_tpv.modulos.almacen.producto_repository import ProductoRepository
        self.producto_repo = ProductoRepository(db)

        self.container = ctk.CTkFrame(parent, fg_color=self.colors.get('background', COLOR_BG_TERMINAL))

        # entry defaults from palette
        default_entry_kw = {
            'fg_color': self.colors.get('background', COLOR_BG_TERMINAL),
            'text_color': self.colors.get('text', COLOR_MATRIX),
            'border_color': self.colors.get('border', self.colors.get('primary')),
            'height': 32
        }
        # buttons palette (optional nested config)
        _buttons_cfg = self.colors.get('buttons', {})
        _primary_btn = _buttons_cfg.get('primary', {})

        # Header
        header_frame = ctk.CTkFrame(self.container, fg_color='transparent')
        header_frame.pack(fill='x', padx=6, pady=2)

        ctk.CTkLabel(header_frame, text='Nº ALBARÁN:', text_color=self.colors['text'],
                 font=get_font('label', module=self.module_name)).pack(side='left', padx=(0, 6))
        self.e_num_albaran = ctk.CTkEntry(header_frame, width=100, **default_entry_kw)
        self.e_num_albaran.pack(side='left', padx=(0, 6))

        btn_siguiente = ButtonFactory.create_button(
            parent=header_frame,
            text='SIGUIENTE',
            command=self._set_next_num,
            style_key="mini_action"
        )
        btn_siguiente.pack(side='left', padx=(0, 20))

        ctk.CTkLabel(header_frame, text='PROVEEDOR:', text_color=self.colors['text'],
                 font=get_font('label', module=self.module_name)).pack(side='left', padx=(0, 6))
        self.cb_proveedor = SearchableCombo(header_frame, options=[], placeholder='Buscar proveedor', width=250)
        self.cb_proveedor.pack(side='left', padx=(0, 20))
        self._load_proveedores()

        ctk.CTkLabel(header_frame, text='FECHA:', text_color=self.colors['text'],
                 font=get_font('label', module=self.module_name)).pack(side='left', padx=(0, 6))
        self.e_fecha = ctk.CTkEntry(header_frame, width=120, **default_entry_kw)
        self.e_fecha.pack(side='left')
        self.e_fecha.insert(0, date.today().strftime('%Y-%m-%d'))

        # Título dinámico según tipo
        titulos = {
            'ENTRADA': 'INTRODUCIR DATOS LÍNEA ALBARÁN - ENTRADA',
            'SALIDA': 'INTRODUCIR DATOS LÍNEA ALBARÁN - SALIDA MANUAL',
            'DEVOLUCION': 'INTRODUCIR DATOS LÍNEA ALBARÁN - DEVOLUCIÓN'
        }
        texto_titulo = titulos.get(self.tipo, 'INTRODUCIR DATOS LÍNEA ALBARÁN')

        lbl_entrada = ctk.CTkLabel(self.container, text=texto_titulo,
                       text_color=self.colors['text'], font=get_font('label', module=self.module_name), anchor='w')
        lbl_entrada.pack(fill='x', padx=6, pady=(6, 2))

        # Layout principal: dos columnas (buscador izquierda | entrada+líneas derecha)
        body_frame = ctk.CTkFrame(self.container, fg_color='transparent')
        body_frame.pack(fill='both', expand=True, padx=6, pady=2)

        # --- Panel IZQUIERDO: buscador de productos ---
        left_panel = ctk.CTkFrame(body_frame, fg_color=self.colors.get('bg_dark', '#1a1a1a'), width=320)
        left_panel.pack(side='left', fill='y', padx=(0, 6), pady=0)
        left_panel.pack_propagate(False)

        ctk.CTkLabel(left_panel, text='BUSCAR PRODUCTO', text_color=self.colors.get('text', COLOR_MATRIX),
                     font=get_font('label', module=self.module_name)).pack(pady=(8, 4), padx=6)

        self.search_entry = ctk.CTkEntry(
            left_panel,
            placeholder_text='Nombre o EAN…',
            **default_entry_kw
        )
        self.search_entry.pack(fill='x', padx=6, pady=(0, 4))

        from kool_tpv.utils.widgets.searchable_paginated_navlist import SearchablePaginatedNavList
        from kool_tpv.utils.config_loader import load_layout_config

        columns_buscador = [
            ('nombre', 220, 'Nombre'),
            ('stock_actual', 60, 'Stock'),
        ]

        self.buscador_list = SearchablePaginatedNavList(
            parent=left_panel,
            columns=columns_buscador,
            search_function=self.albaran_service.buscar_productos_by_nombre,
            map_function=lambda p: self._map_producto_buscador(p),
            module_name=self.module_name,
            page_limit=50,
            on_double_click=self._on_producto_seleccionado_buscador,
            keyboard_manager=self.keyboard_mgr,
            layout_config=load_layout_config(),
        )
        self.buscador_list.pack(fill='both', expand=True, padx=6, pady=(0, 6))

        self.search_entry.bind('<Return>', lambda e: self.buscador_list.search(self.search_entry.get()))

        # --- Panel DERECHO: fila de entrada + lista de líneas + totales ---
        right_panel = ctk.CTkFrame(body_frame, fg_color='transparent')
        right_panel.pack(side='left', fill='both', expand=True)

        # Cabecera de columnas
        self.col_widths = [160, 240, 70, 80, 50, 70, 90]
        col_widths = self.col_widths
        headers_input = ['EAN', 'NOMBRE', 'CANTIDAD', 'COSTE', '%IVA', 'IVA', 'TOTAL']

        cab_frame = ctk.CTkFrame(right_panel, fg_color='transparent', height=20)
        cab_frame.pack(fill='x', pady=(0, 2))
        cab_frame.pack_propagate(False)

        x = 6
        for i, h in enumerate(headers_input):
            lbl = ctk.CTkLabel(cab_frame, text=h, text_color=self.colors['text'], anchor='w',
                              font=get_font('small', module=self.module_name), width=col_widths[i]-8)
            lbl.place(x=x, y=0)
            x += col_widths[i]

        # Fila de entrada
        self.input_frame = ctk.CTkFrame(right_panel, fg_color=self.colors.get('bg_dark', '#1a1a1a'), height=40)
        self.input_frame.pack(fill='x', pady=(0, 6))
        self.input_frame.pack_propagate(False)

        entry_kw = default_entry_kw.copy()

        self.e_ean = ctk.CTkEntry(self.input_frame, width=col_widths[0]-12, placeholder_text='Escanear EAN…', **entry_kw)
        self.e_ean.place(x=6, y=4)
        self.e_ean.bind('<Return>', self._on_ean_scanned)

        self.e_nombre = ctk.CTkEntry(self.input_frame, width=col_widths[1]-12, placeholder_text='Nombre producto',
                                     state='readonly', **entry_kw)
        self.e_nombre.place(x=sum(col_widths[:1]) + 6, y=4)

        self.e_uds = ctk.CTkEntry(self.input_frame, width=col_widths[2]-12, placeholder_text='Cantidad', **entry_kw)
        self.e_uds.place(x=sum(col_widths[:2]) + 6, y=4)
        try:
            self.e_uds.bind('<KeyRelease>', lambda e: self._recalc_importe())
            self.e_uds.bind('<FocusOut>', lambda e: self._recalc_importe())
            self.e_uds.bind('<Return>', lambda e: self.btn_add.focus_set())
        except Exception:
            pass

        self.e_coste = ctk.CTkEntry(self.input_frame, width=col_widths[3]-12, placeholder_text='Coste', **entry_kw)
        self.e_coste.place(x=sum(col_widths[:3]) + 6, y=4)
        self.e_coste.insert(0, '0.00')

        self.e_pct_iva = ctk.CTkEntry(self.input_frame, width=col_widths[4]-12, placeholder_text='%IVA',
                                      state='readonly', **entry_kw)
        self.e_pct_iva.place(x=sum(col_widths[:4]) + 6, y=4)
        self.e_pct_iva.insert(0, '0')

        self.e_iva = ctk.CTkEntry(self.input_frame, width=col_widths[5]-12, placeholder_text='IVA',
                                  state='readonly', **entry_kw)
        self.e_iva.place(x=sum(col_widths[:5]) + 6, y=4)
        self.e_iva.insert(0, '0.00')

        self.e_importe = ctk.CTkEntry(self.input_frame, width=col_widths[6]-12, placeholder_text='Total',
                                      state='readonly', **entry_kw)
        self.e_importe.place(x=sum(col_widths[:6]) + 6, y=4)
        self.e_importe.insert(0, '0.00')

        # Botón AÑADIR
        _normal_fg = _primary_btn.get('bg', self.colors.get('primary', '#2ecc71'))
        _focus_fg = _primary_btn.get('hover', self.colors.get('secondary', '#c6ef0e'))
        self.btn_add = ButtonFactory.create_button(
            parent=self.input_frame,
            text='AÑADIR',
            command=self._add_line,
            style_key="mini_action"
        )

        try:
            self.btn_add.configure(takefocus=True)
        except Exception:
            pass

        try:
            self.e_coste.bind('<Return>', lambda e: self.btn_add.focus_set())
        except Exception:
            pass

        def _invoke_add(event=None):
            try:
                self.btn_add.invoke()
            except Exception:
                pass

        try:
            self.btn_add.bind('<Return>', _invoke_add)
            self.btn_add.bind('<KP_Enter>', _invoke_add)
            self.btn_add.bind('<KeyPress-Return>', _invoke_add)
        except Exception:
            pass

        def _on_btn_focus_in(ev=None):
            try:
                self.btn_add.configure(fg_color=_focus_fg)
            except Exception:
                pass

        def _on_btn_focus_out(ev=None):
            try:
                self.btn_add.configure(fg_color=_normal_fg)
            except Exception:
                pass

        try:
            self.btn_add.bind('<FocusIn>', _on_btn_focus_in)
            self.btn_add.bind('<FocusOut>', _on_btn_focus_out)
        except Exception:
            pass

        self.btn_add.place(x=sum(col_widths) + 12, y=4)

        # Área de líneas añadidas
        self.columns_lines = [
            ('EAN', 160), ('NOMBRE', 220), ('UDS', 60), ('COSTE', 75), ('%IVA', 45), ('IVA', 65), ('PVP', 75), ('TOTAL', 85)
        ]
        self.nav_list = VirtualNavList(
            right_panel,
            columns=self.columns_lines,
            module_name=self.module_name,
            keyboard_manager=self.keyboard_mgr,
            on_double_click=self._on_double_click_line,
        )
        self.nav_list.pack(fill='both', expand=True, pady=2)

        # Totales
        from kool_tpv.utils.config_loader import load_font_config
        fonts = load_font_config()
        font_totales = fonts.get('subtitle', {'family': 'Courier New', 'size': 20, 'weight': 'bold'})
        font_tuple = (font_totales.get('family', 'Courier New'), font_totales.get('size', 20), font_totales.get('weight', 'bold'))

        totales_frame = ctk.CTkFrame(right_panel, fg_color='transparent', height=50)
        totales_frame.pack(fill='x', pady=12)
        totales_frame.pack_propagate(False)

        self.lbl_neto = ctk.CTkLabel(totales_frame, text='Neto: 0.00€', text_color=self.colors['text'], font=font_tuple)
        self.lbl_neto.pack(side='left', padx=12)
        self.lbl_iva4 = ctk.CTkLabel(totales_frame, text='IVA 4%: 0.00€', text_color=self.colors['text'], font=font_tuple)
        self.lbl_iva4.pack(side='left', padx=12)
        self.lbl_iva10 = ctk.CTkLabel(totales_frame, text='IVA 10%: 0.00€', text_color=self.colors['text'], font=font_tuple)
        self.lbl_iva10.pack(side='left', padx=12)
        self.lbl_iva21 = ctk.CTkLabel(totales_frame, text='IVA 21%: 0.00€', text_color=self.colors['text'], font=font_tuple)
        self.lbl_iva21.pack(side='left', padx=12)
        self.lbl_total = ctk.CTkLabel(totales_frame, text='TOTAL: 0.00€', text_color=self.colors.get('error', '#e74c3c'), font=font_tuple)
        self.lbl_total.pack(side='left', padx=20)

        try:
            if self.tipo == 'SALIDA':
                lbl_info = ctk.CTkLabel(
                    totales_frame,
                    text='⚠️ SE RESTARÁ DEL STOCK',
                    text_color=self.colors.get('warning', '#f39c12'),
                    font=get_font('label', module=self.module_name)
                )
                lbl_info.pack(side='left', padx=20)
            elif self.tipo == 'DEVOLUCION':
                lbl_info = ctk.CTkLabel(
                    totales_frame,
                    text='🔙 DEVOLUCIÓN - SE RESTARÁ DEL STOCK',
                    text_color=self.colors.get('secondary', '#95a5a6'),
                    font=get_font('label', module=self.module_name)
                )
                lbl_info.pack(side='left', padx=20)
        except Exception:
            pass

        # Footer (desde config)
        footer = ctk.CTkFrame(self.container, fg_color='transparent')
        footer.pack(side='bottom', fill='x', padx=6, pady=12)
        btn_guardar = create_action_button(footer, 'guardar', self._save_albaran)
        btn_guardar.pack(side='left', padx=8)
        btn_eliminar = create_action_button(footer, 'eliminar', self._delete_selected_line)
        btn_eliminar.pack(side='left', padx=8)
        btn_cancelar = create_action_button(footer, 'cancelar', self._cancel)
        btn_cancelar.pack(side='left', padx=8)

        # Bind tecla Delete en NavList
        try:
            self.nav_list.bind('<Delete>', lambda e: self._delete_selected_line())
        except Exception:
            pass

        # Estado
        self.lines = []
        self._set_next_num()
        self.e_ean.focus_set()

        # Si se pasa albaran_id, cargar datos existentes
        if self.albaran_id is not None:
            self.container.after(100, self._load_albaran_existente)

    def get_widget(self):
        return self.container

    def _map_producto_buscador(self, producto: dict) -> dict:
        """Mapear producto de buscar_productos_by_nombre para mostrar en el buscador."""
        try:
            return {
                'id': producto.get('id'),
                'nombre': producto.get('nombre', ''),
                'stock_actual': producto.get('stock_actual', ''),
                '_ean': producto.get('ean', ''),
                '_coste': producto.get('coste', 0.0),
                '_tipo_iva': producto.get('tipo_iva', 21),
                '_sku': producto.get('sku', ''),
                '_pvp': producto.get('pvp', 0.0),
            }
        except Exception:
            logging.exception('Error en _map_producto_buscador')
            return {}

    def _on_producto_seleccionado_buscador(self, data: dict):
        """Al hacer doble clic en el buscador: rellenar EAN, NOMBRE y COSTE."""
        try:
            ean = data.get('_ean', '')
            nombre = data.get('nombre', '')
            coste = data.get('_coste', 0.0)
            tipo_iva = data.get('_tipo_iva', 21)
            producto_id = data.get('id')
            sku = data.get('_sku', '')

            pvp = data.get('_pvp', 0.0)
            self._current_producto = {
                'id': producto_id,
                'nombre': nombre,
                'coste': coste,
                'tipo_iva': tipo_iva,
                'ean': ean,
                'sku': sku,
                'pvp': pvp,
            }

            self.e_ean.delete(0, 'end')
            self.e_ean.insert(0, ean)

            try:
                self.e_nombre.configure(state='normal')
                self.e_nombre.delete(0, 'end')
                self.e_nombre.insert(0, nombre)
                self.e_nombre.configure(state='readonly')
            except Exception:
                pass

            self.e_coste.delete(0, 'end')
            self.e_coste.insert(0, f'{coste:.2f}')

            self._recalc_importe()
            self.e_uds.focus_set()
        except Exception:
            logging.exception('Error en _on_producto_seleccionado_buscador')

    def has_unsaved_changes(self):
        """Verificar si hay líneas sin guardar.

        En modo edición: solo líneas nuevas (sin 'id') cuentan como cambios pendientes.
        En modo nuevo: cualquier línea cuenta.

        Returns:
            bool: True si hay cambios sin guardar
        """
        try:
            if self.albaran_id is not None:
                return any('id' not in line for line in self.lines)
            return len(self.lines) > 0
        except Exception:
            return False

    def _load_proveedores(self):
        try:
            provs = self.proveedor_service.get_all_proveedores()
            opts = [(p['id'], p['nombre']) for p in provs]
            self.cb_proveedor.set_options(opts)
        except Exception:
            logging.exception('Error cargando proveedores')

    def _set_next_num(self):
        try:
            next_num = self.albaran_service.get_next_num_albaran()
            self.e_num_albaran.delete(0, 'end')
            self.e_num_albaran.insert(0, str(next_num))
        except Exception:
            logging.exception('Error obteniendo siguiente num_albaran')

    def _recalc_importe(self, event=None):
        """Recalcula IVA y TOTAL visibles usando coste, cantidad y tipo_iva del producto."""
        try:
            try:
                uds_val = int(self.e_uds.get() or 0)
            except Exception:
                uds_val = 0
            try:
                coste_val = float(self.e_coste.get() or 0.0)
            except Exception:
                coste_val = 0.0

            tipo_iva = int((self._current_producto or {}).get('tipo_iva', 21) or 21)
            neto = coste_val * uds_val if uds_val > 0 else 0.0
            iva_val = round(neto * tipo_iva / 100, 2)
            total_val = round(neto + iva_val, 2)

            for entry, value in [
                (self.e_pct_iva, f"{tipo_iva}%"),
                (self.e_iva, f"{iva_val:.2f}"),
                (self.e_importe, f"{total_val:.2f}"),
            ]:
                try:
                    entry.configure(state='normal')
                    entry.delete(0, 'end')
                    entry.insert(0, value)
                    entry.configure(state='readonly')
                except Exception:
                    pass
        except Exception:
            logging.exception('Error recalculando importe')

    


    def _on_ean_scanned(self, event=None):
        try:
            ean = self.e_ean.get().strip()
            if not ean:
                return

            producto = self.albaran_service.buscar_producto_by_ean(ean)
            if producto:
                try:
                    self.e_nombre.configure(state='normal')
                    self.e_nombre.delete(0, 'end')
                    self.e_nombre.insert(0, producto['nombre'])
                    self.e_nombre.configure(state='readonly')
                except Exception:
                    pass
                self.e_coste.delete(0, 'end')
                self.e_coste.insert(0, f"{producto['coste']:.2f}")
                self._current_producto = producto
                self._recalc_importe()
                self.e_uds.focus_set()
            else:
                try:
                    self.e_nombre.configure(state='normal')
                    self.e_nombre.delete(0, 'end')
                    self.e_nombre.insert(0, 'NO ENCONTRADO')
                    self.e_nombre.configure(state='readonly')
                except Exception:
                    pass
                self.e_coste.delete(0, 'end')
                self.e_coste.insert(0, '0.00')
                self._current_producto = None
        except Exception:
            logging.exception('Error escaneando EAN')

    def _map_line_to_row(self, line: dict) -> dict:
        try:
            cantidad = line.get('cantidad', 0)
            coste = line.get('coste', 0.0)
            tipo_iva = int(line.get('tipo_iva', 21) or 21)
            neto = cantidad * coste
            iva = round(float(neto) * tipo_iva / 100, 2)
            total = round(float(neto) + iva, 2)
            pvp = line.get('pvp', 0.0)
            mapped = {
                'EAN': line.get('ean', ''),
                'NOMBRE': line.get('nombre', ''),
                'UDS': str(cantidad),
                'COSTE': f"{float(coste):.2f}",
                '%IVA': f"{tipo_iva}%",
                'IVA': f"{iva:.2f}",
                'PVP': f"{float(pvp):.2f}" if pvp else '-',
                'TOTAL': f"{total:.2f}",
                '_idx': line.get('id') if 'id' in line else None
            }
            return mapped
        except Exception:
            logging.exception('Error mapeando línea a row')
            return {}

    def _on_double_click_line(self, data: dict):
        try:
            # Encontrar índice por id o por EAN+NOMBRE
            idx = None
            row_id = data.get('_idx')
            if row_id:
                for i, ln in enumerate(self.lines):
                    if ln.get('id') == row_id:
                        idx = i
                        break
            if idx is None:
                for i, ln in enumerate(self.lines):
                    if ln.get('ean') == data.get('EAN') and ln.get('nombre') == data.get('NOMBRE'):
                        idx = i
                        break
            if idx is None:
                return

            line = self.lines[idx]
            # Rellenar inputs para editar
            try:
                self.e_ean.delete(0, 'end')
                self.e_ean.insert(0, line.get('ean', ''))
            except Exception:
                pass
            try:
                self.e_nombre.configure(state='normal')
                self.e_nombre.delete(0, 'end')
                self.e_nombre.insert(0, line.get('nombre', ''))
                self.e_nombre.configure(state='readonly')
            except Exception:
                pass
            try:
                self.e_uds.delete(0, 'end')
                self.e_uds.insert(0, str(line.get('cantidad', '')))
            except Exception:
                pass
            try:
                self.e_coste.delete(0, 'end')
                self.e_coste.insert(0, f"{line.get('coste', 0.0):.2f}")
            except Exception:
                pass

            # Marcar edición: reemplazaremos la línea al añadir
            try:
                self._editing_index = idx
                self.e_uds.focus_set()
            except Exception:
                pass

        except Exception:
            logging.exception('Error manejando doble click en línea')

    def _delete_selected_line(self):
        """Eliminar la línea seleccionada en la NavList."""
        try:
            data = self.nav_list.get_selected_data()
            if not data:
                return

            # Encontrar índice por id o por EAN+NOMBRE
            idx = None
            row_id = data.get('_idx')
            if row_id:
                for i, ln in enumerate(self.lines):
                    if ln.get('id') == row_id:
                        idx = i
                        break
            if idx is None:
                for i, ln in enumerate(self.lines):
                    if ln.get('ean') == data.get('EAN') and ln.get('nombre') == data.get('NOMBRE'):
                        idx = i
                        break
            if idx is None:
                return

            # Eliminar línea
            self.lines.pop(idx)
            self._render_lines()
            self._update_totals()
            logging.info(f'Línea eliminada: índice {idx}')
        except Exception:
            logging.exception('Error eliminando línea')

    def _add_line(self):
        try:
            uds = int(self.e_uds.get() or 0)
            if uds <= 0:
                return

            nombre = self.e_nombre.get().strip()
            coste = float(self.e_coste.get() or 0)

            producto_id = self._current_producto['id'] if hasattr(self, '_current_producto') and self._current_producto else None
            tipo_iva = self._current_producto['tipo_iva'] if hasattr(self, '_current_producto') and self._current_producto else 21
            pvp = self._current_producto.get('pvp', 0.0) if hasattr(self, '_current_producto') and self._current_producto else 0.0

            line = {
                'producto_id': producto_id,
                'ean': self.e_ean.get().strip(),
                'nombre': nombre,
                'cantidad': uds,
                'coste': coste,
                'tipo_iva': tipo_iva,
                'pvp': pvp
            }

            # Si estamos editando, reemplazar; si no, añadir
            if hasattr(self, '_editing_index') and self._editing_index is not None:
                self.lines[self._editing_index] = line
                self._editing_index = None
            else:
                self.lines.append(line)
            self._render_lines()
            self._update_totals()

            # Limpiar
            self.e_ean.delete(0, 'end')
            try:
                self.e_nombre.configure(state='normal')
                self.e_nombre.delete(0, 'end')
                self.e_nombre.configure(state='readonly')
            except Exception:
                pass
            self.e_uds.delete(0, 'end')
            self.e_coste.delete(0, 'end')
            self.e_coste.insert(0, '0.00')
            self._current_producto = None
            self.e_ean.focus_set()

        except Exception:
            logging.exception('Error añadiendo línea')

    def _render_lines(self):
        try:
            # Limpiar NavList
            try:
                self.nav_list.clear_items()
            except Exception:
                pass

            # Añadir cada línea al NavList
            for idx, line in enumerate(self.lines):
                try:
                    mapped = self._map_line_to_row(line)
                    self.nav_list.add_item(mapped)
                except Exception:
                    logging.exception('Error añadiendo línea al NavList')
        except Exception:
            logging.exception('Error renderizando líneas')

    def _update_totals(self):
        try:
            from decimal import Decimal
            neto = Decimal('0')
            iva4 = Decimal('0')
            iva10 = Decimal('0')
            iva21 = Decimal('0')

            for line in self.lines:
                cantidad = Decimal(str(line.get('cantidad', 0)))
                coste = line.get('coste', 0)
                if not isinstance(coste, Decimal):
                    coste = Decimal(str(coste))
                importe_linea = cantidad * coste

                neto += importe_linea

                tipo = int(line.get('tipo_iva', 21) or 21)
                iva_calc = importe_linea * (Decimal(str(tipo)) / Decimal('100'))

                if tipo == 4:
                    iva4 += iva_calc
                elif tipo == 10:
                    iva10 += iva_calc
                elif tipo == 21:
                    iva21 += iva_calc

            total = neto + iva4 + iva10 + iva21

            self.lbl_neto.configure(text=f'Neto: {neto:.2f}€')
            self.lbl_iva4.configure(text=f'IVA 4%: {iva4:.2f}€')
            self.lbl_iva10.configure(text=f'IVA 10%: {iva10:.2f}€')
            self.lbl_iva21.configure(text=f'IVA 21%: {iva21:.2f}€')
            self.lbl_total.configure(text=f'TOTAL: {total:.2f}€')
        except Exception:
            logging.exception('Error actualizando totales')

    def _load_albaran_existente(self):
        """Precargar cabecera y líneas de un albarán existente para edición."""
        try:
            detalle = self.albaran_service.get_albaran_detalle(self.albaran_id)
            if not detalle:
                logging.error(f'Albarán {self.albaran_id} no encontrado')
                return

            albaran = detalle['albaran']
            lines = detalle['lines'] or []

            # Cabecera: num_albaran (readonly en edición)
            try:
                self.e_num_albaran.delete(0, 'end')
                self.e_num_albaran.insert(0, str(albaran.get('num_albaran', '')))
                self.e_num_albaran.configure(state='readonly')
            except Exception:
                pass

            # Proveedor
            try:
                prov_nombre = albaran.get('proveedor_nombre', '')
                self.cb_proveedor.set(prov_nombre)
            except Exception:
                pass

            # Fecha
            try:
                self.e_fecha.delete(0, 'end')
                self.e_fecha.insert(0, albaran.get('fecha', ''))
            except Exception:
                pass

            # Líneas: enriquecer con PVP desde ProductoRepository (una sola query)
            producto_ids = [line.get('producto_id') for line in lines if line.get('producto_id')]
            if producto_ids:
                pvps = self.producto_repo.get_pvps_by_ids(producto_ids)
                for line in lines:
                    pid = line.get('producto_id')
                    if pid and pid in pvps:
                        line['pvp'] = pvps[pid]
            self.lines = lines
            self._render_lines()
            self._update_totals()

        except Exception:
            logging.exception(f'Error cargando albarán existente {self.albaran_id}')

    def _save_albaran(self):
        try:
            if not self.lines:
                logging.info('No hay líneas para guardar')
                return

            # MODO EDICIÓN: actualizar albarán existente
            if self.albaran_id is not None:
                success = self.albaran_service.update_albaran_with_new_lines(
                    self.albaran_id,
                    self.lines
                )
                if success:
                    logging.info(f'Albarán {self.albaran_id} actualizado correctamente')
                    try:
                        show_success(self.container, 'Guardado', f'Albarán {self.albaran_id} actualizado correctamente')
                    except Exception:
                        pass
                    self._load_albaran_existente()
                else:
                    logging.error(f'Error actualizando albarán {self.albaran_id}')
                return

            # MODO NUEVO
            num = int(self.e_num_albaran.get())
            prov_id = self.cb_proveedor.get_id()
            fecha = self.e_fecha.get()

            # Validar proveedor solo si el tipo lo requiere
            if self.tipo in ['ENTRADA', 'DEVOLUCION']:
                if not prov_id:
                    from kool_tpv.utils.custom_dialog import show_error
                    show_error(self.container, 'Proveedor requerido',
                               f'Debe seleccionar un proveedor para albaranes de tipo {self.tipo}')
                    return

            albaran_id = self.albaran_service.save_albaran(num, prov_id, fecha, self.lines, tipo=self.tipo)
            if albaran_id:
                logging.info(f'Albarán guardado: {albaran_id}')
                try:
                    show_success(self.container, 'Guardado', f'Albarán {albaran_id} guardado correctamente')
                except Exception:
                    pass
                self._cancel()
        except Exception:
            logging.exception('Error guardando albarán')

    def _cancel(self):
        try:
            self.lines = []
            self.e_ean.delete(0, 'end')
            try:
                self.e_nombre.configure(state='normal')
                self.e_nombre.delete(0, 'end')
                self.e_nombre.configure(state='readonly')
            except Exception:
                pass
            try:
                self.cb_proveedor.set('')
            except Exception:
                pass
            self.e_uds.delete(0, 'end')
            self.e_coste.delete(0, 'end')
            self.e_coste.insert(0, '0.00')
            # Limpiar %IVA, IVA y TOTAL
            for entry, val in [(self.e_pct_iva, '0%'), (self.e_iva, '0.00'), (self.e_importe, '0.00')]:
                try:
                    entry.configure(state='normal')
                    entry.delete(0, 'end')
                    entry.insert(0, val)
                    entry.configure(state='readonly')
                except Exception:
                    pass
            self._render_lines()
            self._update_totals()
            self._set_next_num()
        except Exception:
            logging.exception('Error en cancel')
