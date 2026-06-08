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
    def __init__(self, parent, db=None, tipo='ENTRADA', module_name: str = 'almacen', keyboard_manager=None):
        self.parent = parent
        self.db = db
        self.tipo = tipo  # 'ENTRADA', 'SALIDA', 'DEVOLUCION'
        self.module_name = module_name
        self.keyboard_mgr = keyboard_manager
        from kool_tpv.utils.config_loader import load_colors
        try:
            self.colors = load_colors(module_name)
        except Exception:
            self.colors = {'text': COLOR_MATRIX, 'primary': COLOR_MATRIX, 'secondary': COLOR_MATRIX, 'accent': COLOR_MATRIX}
        self.albaran_service = AlbaranService(db)
        self.proveedor_service = ProveedorService(db)

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
        _secondary_btn = _buttons_cfg.get('secondary', {})

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

        # Grid header (layout values kept here; visual header moved below)
        self.col_widths = [160, 320, 90, 90, 90, 110]
        col_widths = self.col_widths
        # color de fila por defecto (se alternará en _render_lines)
        self._row_bg_main = self.colors.get('bg_dark', '#1a1a1a')
        self._row_bg_alt = self.colors.get('bg_medium', '#111111')
        headers = ['EAN', 'NOMBRE', 'UDS', 'COSTE', 'DTO', 'IMPORTE']

        # Título dinámico según tipo
        titulos = {
            'ENTRADA': 'INTRODUCIR DATOS LÍNEA ALBARÁN - ENTRADA',
            'SALIDA': 'INTRODUCIR DATOS LÍNEA ALBARÁN - SALIDA MANUAL',
            'DEVOLUCION': 'INTRODUCIR DATOS LÍNEA ALBARÁN - DEVOLUCIÓN'
        }
        texto_titulo = titulos.get(self.tipo, 'INTRODUCIR DATOS LÍNEA ALBARÁN')

        lbl_entrada = ctk.CTkLabel(self.container, text=texto_titulo,
                       text_color=self.colors['text'], font=('Courier New', 13, 'bold'), anchor='w')
        lbl_entrada.pack(fill='x', padx=6, pady=(6, 2))

        # Cabecera campos
        cab_frame = ctk.CTkFrame(self.container, fg_color='transparent', height=20)
        cab_frame.pack(fill='x', padx=6, pady=(0, 2))
        cab_frame.pack_propagate(False)

        self.col_widths = [160, 320, 90, 90, 90, 110]
        col_widths = self.col_widths
        headers_input = ['EAN', 'NOMBRE', 'CANTIDAD', 'COSTE', 'DTO', 'IMPORTE']

        x = 6
        for i, h in enumerate(headers_input):
            lbl = ctk.CTkLabel(cab_frame, text=h, text_color=self.colors['text'], anchor='w',
                              font=('Courier New', 10), width=col_widths[i]-8)
            lbl.place(x=x, y=0)
            x += col_widths[i]

        # Fila de entrada
        self.input_frame = ctk.CTkFrame(self.container, fg_color=self.colors.get('bg_dark', '#1a1a1a'), height=40)
        self.input_frame.pack(fill='x', padx=6, pady=(0, 6))
        self.input_frame.pack_propagate(False)

        entry_kw = default_entry_kw.copy()

        self.e_ean = ctk.CTkEntry(self.input_frame, width=col_widths[0]-12, placeholder_text='Escanear EAN…', **entry_kw)
        self.e_ean.place(x=6, y=4)
        self.e_ean.bind('<Return>', self._on_ean_scanned)

        self.cb_nombre = SearchableCombo(
            self.input_frame,
            search_function=self.albaran_service.buscar_productos_by_nombre,
            placeholder='Buscar producto…',
            width=col_widths[1]-12,
            height=32
        )
        self.cb_nombre.entry.configure(width=col_widths[1]-12, **entry_kw)
        self.cb_nombre.place(x=sum(col_widths[:1]) + 6, y=4)
        # Bindings: autocompletar coste al seleccionar producto
        try:
            # Evento de selección explícita (Return o click)
            self.cb_nombre.entry.bind('<<SearchableComboSelected>>', self._on_nombre_selected)
            # También al salir del campo (previene perder coste si usuario hace Tab directo)
            self.cb_nombre.entry.bind('<FocusOut>', self._on_nombre_selected)
        except Exception:
            pass

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

        self.e_dto = ctk.CTkEntry(self.input_frame, width=col_widths[4]-12, placeholder_text='Descuento', **entry_kw)
        self.e_dto.place(x=sum(col_widths[:4]) + 6, y=4)
        self.e_dto.insert(0, '0')
        try:
            self.e_dto.bind('<KeyRelease>', lambda e: self._recalc_importe())
            self.e_dto.bind('<FocusOut>', lambda e: self._recalc_importe())
        except Exception:
            pass

        self.e_importe = ctk.CTkEntry(self.input_frame, width=col_widths[5]-12, placeholder_text='Importe', state='readonly', **entry_kw)
        self.e_importe.place(x=sum(col_widths[:5]) + 6, y=4)
        self.e_importe.insert(0, '0.00')

        # Botón AÑADIR (usar botones config si existe)
        _normal_fg = _primary_btn.get('bg', self.colors.get('primary', '#2ecc71'))
        _focus_fg = _primary_btn.get('hover', self.colors.get('secondary', '#c6ef0e'))
        _hover_fg = _primary_btn.get('hover', self.colors.get('secondary', '#e0fc0f'))
        self.btn_add = ButtonFactory.create_button(
            parent=self.input_frame,
            text='AÑADIR',
            command=self._add_line,
            style_key="mini_action"
        )

        # permitir que el botón reciba foco por Tab
        try:
            self.btn_add.configure(takefocus=True)
        except Exception:
            pass

        # al pulsar Tab desde DTO forzar foco al botón (evita que salte fuera)
        try:
            self.e_dto.bind('<KeyPress-Tab>', lambda e: (self.btn_add.focus_set(), "break"))
        except Exception:
            pass

        # permitir activar con cualquier Enter (Return y keypad Enter) cuando el botón tiene foco
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

        # foco visual: cambiar color cuando el botón recibe/ pierde foco
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

        # Header labels removed — NavList will provide the visible header

        # Área de líneas -> NavList para soporte teclado y selección
        self.columns_lines = [
            ('EAN', 160), ('NOMBRE', 320), ('UDS', 90), ('COSTE', 90), ('DTO', 90), ('IMPORTE', 110)
        ]
        self.nav_list = VirtualNavList(
            self.container,
            columns=self.columns_lines,
            module_name=self.module_name,
            keyboard_manager=self.keyboard_mgr,
            on_double_click=self._on_double_click_line,
        )
        self.nav_list.pack(fill='both', expand=True, padx=6, pady=2)

        # Totales - usando config de fuentes
        from kool_tpv.utils.config_loader import load_font_config
        fonts = load_font_config()
        font_totales = fonts.get('large', {'family': 'Courier New', 'size': 26, 'weight': 'bold'})
        font_tuple = (font_totales.get('family', 'Courier New'), font_totales.get('size', 26), font_totales.get('weight', 'bold'))

        totales_frame = ctk.CTkFrame(self.container, fg_color='transparent', height=50)
        totales_frame.pack(fill='x', padx=6, pady=12)
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

        # Label informativo según tipo
        try:
            if self.tipo == 'SALIDA':
                lbl_info = ctk.CTkLabel(
                    totales_frame,
                    text='⚠️ SE RESTARÁ DEL STOCK',
                    text_color=self.colors.get('warning', '#f39c12'),
                    font=('Courier New', 13, 'bold')
                )
                lbl_info.pack(side='left', padx=20)
            elif self.tipo == 'DEVOLUCION':
                lbl_info = ctk.CTkLabel(
                    totales_frame,
                    text='🔙 DEVOLUCIÓN - SE RESTARÁ DEL STOCK',
                    text_color=self.colors.get('secondary', '#95a5a6'),
                    font=('Courier New', 13, 'bold')
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

    def get_widget(self):
        return self.container

    def has_unsaved_changes(self):
        """Verificar si hay líneas añadidas sin guardar.

        Returns:
            bool: True si hay líneas en memoria, False si está vacío
        """
        try:
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

    def _on_nombre_selected(self, event=None):
        """Autocompletar coste al seleccionar producto."""
        try:
            producto = self.cb_nombre.get_producto_data()
            if producto:
                self.e_coste.delete(0, 'end')
                self.e_coste.insert(0, f"{producto['coste']:.2f}")
                self._current_producto = producto
                self.e_uds.focus_set()
        except Exception:
            logging.exception('Error en _on_nombre_selected')

    def _recalc_importe(self, event=None):
        """Recalcula el importe visible usando coste, cantidad y descuento."""
        try:
            try:
                uds_val = int(self.e_uds.get() or 0)
            except Exception:
                uds_val = 0
            try:
                dto_val = float(self.e_dto.get() or 0)
            except Exception:
                dto_val = 0.0
            try:
                coste_val = float(self.e_coste.get() or 0.0)
            except Exception:
                coste_val = 0.0

            if uds_val <= 0:
                importe_val = 0.0
            else:
                importe_val = (coste_val * uds_val) - dto_val

            try:
                self.e_importe.configure(state='normal')
                self.e_importe.delete(0, 'end')
                self.e_importe.insert(0, f"{importe_val:.2f}")
                self.e_importe.configure(state='readonly')
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
                self.cb_nombre.set(producto['nombre'])
                self.e_coste.delete(0, 'end')
                self.e_coste.insert(0, f"{producto['coste']:.2f}")
                self._current_producto = producto
                self.e_uds.focus_set()
            else:
                self.cb_nombre.set('NO ENCONTRADO')
                self.e_coste.delete(0, 'end')
                self.e_coste.insert(0, '0.00')
                self._current_producto = None
        except Exception:
            logging.exception('Error escaneando EAN')

    def _map_line_to_row(self, line: dict) -> dict:
        try:
            importe = (line.get('cantidad', 0) * line.get('coste', 0.0)) - line.get('descuento', 0.0)
            mapped = {
                'EAN': line.get('ean', ''),
                'NOMBRE': line.get('nombre', ''),
                'UDS': str(line.get('cantidad', '')),
                'COSTE': f"{line.get('coste', 0.0):.2f}",
                'DTO': f"{line.get('descuento', 0.0):.2f}",
                'IMPORTE': f"{importe:.2f}",
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
                self.cb_nombre.set(line.get('nombre', ''))
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
            try:
                self.e_dto.delete(0, 'end')
                self.e_dto.insert(0, f"{line.get('descuento', 0.0):.2f}")
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

            nombre = self.cb_nombre.get().strip()
            if '(' in nombre and nombre.endswith(')'):
                nombre = nombre.split('(')[0].strip()
            coste = float(self.e_coste.get() or 0)
            dto = float(self.e_dto.get() or 0)

            producto_id = self._current_producto['id'] if hasattr(self, '_current_producto') and self._current_producto else None
            tipo_iva = self._current_producto['tipo_iva'] if hasattr(self, '_current_producto') and self._current_producto else 21

            line = {
                'producto_id': producto_id,
                'ean': self.e_ean.get().strip(),
                'nombre': nombre,
                'cantidad': uds,
                'coste': coste,
                'descuento': dto,
                'tipo_iva': tipo_iva
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
            self.cb_nombre.set('')
            self.e_uds.delete(0, 'end')
            self.e_coste.delete(0, 'end')
            self.e_coste.insert(0, '0.00')
            self.e_dto.delete(0, 'end')
            self.e_dto.insert(0, '0')
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
            neto = 0.0
            iva4 = 0.0
            iva10 = 0.0
            iva21 = 0.0

            for line in self.lines:
                importe_linea = (line['cantidad'] * line['coste']) - line['descuento']
                neto += importe_linea

                tipo = line['tipo_iva']
                iva_calc = importe_linea * (tipo / 100.0)

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

    def _save_albaran(self):
        try:
            if not self.lines:
                logging.info('No hay líneas para guardar')
                return

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
            self.cb_nombre.set('')
            try:
                self.cb_proveedor.set('')
            except Exception:
                pass
            self.e_uds.delete(0, 'end')
            self.e_coste.delete(0, 'end')
            self.e_coste.insert(0, '0.00')
            self.e_dto.delete(0, 'end')
            self.e_dto.insert(0, '0')
            # Limpiar importe
            try:
                self.e_importe.configure(state='normal')
                self.e_importe.delete(0, 'end')
                self.e_importe.insert(0, '0.00')
                self.e_importe.configure(state='readonly')
            except Exception:
                pass
            self._render_lines()
            self._update_totals()
            self._set_next_num()
        except Exception:
            logging.exception('Error en cancel')
