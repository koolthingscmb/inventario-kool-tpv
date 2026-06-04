"""UI de Detalle de Albarán - visualización y edición."""
from typing import Optional, List
import logging
import tkinter as tk
from datetime import date
import customtkinter as ctk

from kool_tpv.base_datos.albaran_service import AlbaranService
from kool_tpv.base_datos.proveedor_service import ProveedorService
from kool_tpv.utils.utils import COLOR_BG_TERMINAL, COLOR_MATRIX
from kool_tpv.utils.font_loader import get_font
from kool_tpv.utils.widgets.searchable_combo import SearchableCombo
from kool_tpv.utils.widgets.nav_list import NavList
from kool_tpv.utils.custom_dialog import show_success
from kool_tpv.utils.config_loader import create_action_button

logger = logging.getLogger(__name__)





class DetalleAlbaranUI:
    def __init__(self, parent, db=None, albaran_id=None, owner=None, module_name: str = 'almacen', keyboard_manager=None):
        self.parent = parent
        self.db = db
        self.albaran_id = albaran_id
        self.owner = owner
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

        # Header READONLY
        header_frame = ctk.CTkFrame(self.container, fg_color='transparent')
        header_frame.pack(fill='x', padx=6, pady=2)

        ctk.CTkLabel(header_frame, text='Nº ALBARÁN:', text_color=self.colors['text'],
                 font=get_font('label', module=self.module_name)).pack(side='left', padx=(0, 6))
        self.e_num_albaran = ctk.CTkEntry(header_frame, width=100, fg_color='#000000',
                         text_color=self.colors['text'], border_color=self.colors['primary'],
                         state='readonly')
        self.e_num_albaran.pack(side='left', padx=(0, 20))

        ctk.CTkLabel(header_frame, text='PROVEEDOR:', text_color=self.colors['text'],
                 font=get_font('label', module=self.module_name)).pack(side='left', padx=(0, 6))
        self.e_proveedor = ctk.CTkEntry(header_frame, width=250, fg_color='#000000',
                        text_color=self.colors['text'], border_color=self.colors['primary'],
                        state='readonly')
        self.e_proveedor.pack(side='left', padx=(0, 20))

        ctk.CTkLabel(header_frame, text='FECHA:', text_color=self.colors['text'],
                 font=get_font('label', module=self.module_name)).pack(side='left', padx=(0, 6))
        self.e_fecha = ctk.CTkEntry(header_frame, width=120, fg_color='#000000',
                        text_color=self.colors['text'], border_color=self.colors['primary'],
                        state='readonly')
        self.e_fecha.pack(side='left')

        # Label entrada
        lbl_entrada = ctk.CTkLabel(self.container, text='INTRODUCIR DATOS LÍNEA ALBARÁN',
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
        self.input_frame = ctk.CTkFrame(self.container, fg_color='#1a1a1a', height=40)
        self.input_frame.pack(fill='x', padx=6, pady=(0, 6))
        self.input_frame.pack_propagate(False)

        entry_kw = {'fg_color': '#000000', 'text_color': self.colors['text'], 'border_color': self.colors['primary'], 'height': 32}

        self.e_ean = ctk.CTkEntry(self.input_frame, width=col_widths[0]-12, placeholder_text='Escanear EAN…', **entry_kw)
        self.e_ean.place(x=6, y=4)
        try:
            self.e_ean.bind('<Return>', self._on_ean_scanned)
        except Exception:
            pass

        self.cb_nombre = SearchableCombo(
            self.input_frame,
            search_function=self.albaran_service.buscar_productos_by_nombre,
            placeholder='Buscar producto…',
            width=col_widths[1]-12,
            height=32
        )
        try:
            self.cb_nombre.entry.configure(width=col_widths[1]-12, **entry_kw)
        except Exception:
            pass
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
        except Exception:
            pass

        self.e_coste = ctk.CTkEntry(self.input_frame, width=col_widths[3]-12, placeholder_text='Coste', **entry_kw)
        self.e_coste.place(x=sum(col_widths[:3]) + 6, y=4)
        try:
            self.e_coste.insert(0, '0.00')
        except Exception:
            pass

        self.e_dto = ctk.CTkEntry(self.input_frame, width=col_widths[4]-12, placeholder_text='Descuento', **entry_kw)
        self.e_dto.place(x=sum(col_widths[:4]) + 6, y=4)
        try:
            self.e_dto.insert(0, '0')
        except Exception:
            pass
        try:
            self.e_dto.bind('<KeyRelease>', lambda e: self._recalc_importe())
            self.e_dto.bind('<FocusOut>', lambda e: self._recalc_importe())
        except Exception:
            pass

        self.e_importe = ctk.CTkEntry(self.input_frame, width=col_widths[5]-12, placeholder_text='Importe', state='readonly', **entry_kw)
        self.e_importe.place(x=sum(col_widths[:5]) + 6, y=4)
        try:
            self.e_importe.insert(0, '0.00')
        except Exception:
            pass

        # Botón AÑADIR
        from kool_tpv.utils.factories.button_factory import ButtonFactory
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
            self.e_dto.bind('<KeyPress-Tab>', lambda e: (self.btn_add.focus_set(), "break"))
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

        try:
            self.btn_add.place(x=sum(col_widths) + 12, y=4)
        except Exception:
            pass

        # Manual header removed — NavList will provide the visible header

        # Área de líneas: usar NavList para soporte de teclado y selección
        self.columns_lines = [
            ('EAN', 160), ('NOMBRE', 320), ('UDS', 90), ('COSTE', 90), ('DTO', 90), ('IMPORTE', 110)
        ]
        self.nav_list = NavList(
            self.container,
            columns=self.columns_lines,
            module_name=self.module_name,
            keyboard_manager=self.keyboard_mgr,
            on_double_click=self._on_double_click_line,
        )
        self.nav_list.pack(fill='both', expand=True, padx=6, pady=2)

        # Totales
        totales_frame = ctk.CTkFrame(self.container, fg_color='transparent', height=50)
        totales_frame.pack(fill='x', padx=6, pady=12)
        totales_frame.pack_propagate(False)

        font_totales = ('Courier New', 15, 'bold')
        self.lbl_neto = ctk.CTkLabel(totales_frame, text='Neto: 0.00€', text_color=self.colors['text'], font=font_totales)
        self.lbl_neto.pack(side='left', padx=8)
        ctk.CTkLabel(totales_frame, text='-', text_color=self.colors['text'], font=font_totales).pack(side='left', padx=4)
        self.lbl_iva4 = ctk.CTkLabel(totales_frame, text='IVA 4%: 0.00€', text_color=self.colors['text'], font=font_totales)
        self.lbl_iva4.pack(side='left', padx=8)
        ctk.CTkLabel(totales_frame, text='-', text_color=self.colors['text'], font=font_totales).pack(side='left', padx=4)
        self.lbl_iva10 = ctk.CTkLabel(totales_frame, text='IVA 10%: 0.00€', text_color=self.colors['text'], font=font_totales)
        self.lbl_iva10.pack(side='left', padx=8)
        ctk.CTkLabel(totales_frame, text='-', text_color=self.colors['text'], font=font_totales).pack(side='left', padx=4)
        self.lbl_iva21 = ctk.CTkLabel(totales_frame, text='IVA 21%: 0.00€', text_color=self.colors['text'], font=font_totales)
        self.lbl_iva21.pack(side='left', padx=8)
        ctk.CTkLabel(totales_frame, text='-', text_color=self.colors['text'], font=font_totales).pack(side='left', padx=4)
        self.lbl_total = ctk.CTkLabel(totales_frame, text='TOTAL: 0.00€', text_color='#FF0000', font=('Courier New', 16, 'bold'))
        self.lbl_total.pack(side='left', padx=12)

        # Footer (solo GUARDAR + IMPRIMIR) desde config
        footer = ctk.CTkFrame(self.container, fg_color='transparent')
        footer.pack(side='bottom', fill='x', padx=6, pady=12)
        btn_guardar = create_action_button(footer, 'guardar', self._save_albaran)
        btn_guardar.pack(side='left', padx=8)
        btn_imprimir = create_action_button(footer, 'imprimir', self._print_albaran)
        btn_imprimir.pack(side='left', padx=8)

        # Estado
        self.lines = []
        self._row_bg_main = '#1a1a1a'
        self._row_bg_alt = '#111111'
        self._editing_index = None

        # Cargar datos del albarán
        try:
            self._load_albaran()
        except Exception:
            pass

    def get_widget(self):
        return self.container

    def has_unsaved_changes(self):
        """Verificar si hay líneas nuevas añadidas sin guardar.

        Detecta líneas que no tienen 'id' (aún no están en BD).

        Returns:
            bool: True si hay líneas nuevas, False si no
        """
        try:
            # Buscar líneas sin 'id' (nuevas, no guardadas)
            for line in self.lines:
                if isinstance(line, dict) and 'id' not in line:
                    return True
            return False
        except Exception:
            return False

    def _load_albaran(self):
        """Cargar datos del albarán existente."""
        try:
            detalle = self.albaran_service.get_albaran_detalle(self.albaran_id)
            if not detalle:
                logging.error(f'Albarán {self.albaran_id} no encontrado')
                return

            albaran = detalle['albaran']
            lines = detalle['lines']

            # Llenar header
            try:
                self.e_num_albaran.configure(state='normal')
                self.e_num_albaran.delete(0, 'end')
                self.e_num_albaran.insert(0, str(albaran.get('num_albaran', '')))
                self.e_num_albaran.configure(state='readonly')
            except Exception:
                pass

            try:
                self.e_proveedor.configure(state='normal')
                self.e_proveedor.delete(0, 'end')
                self.e_proveedor.insert(0, albaran.get('proveedor_nombre', ''))
                self.e_proveedor.configure(state='readonly')
            except Exception:
                pass

            try:
                self.e_fecha.configure(state='normal')
                self.e_fecha.delete(0, 'end')
                self.e_fecha.insert(0, albaran.get('fecha', ''))
                self.e_fecha.configure(state='readonly')
            except Exception:
                pass

            # Cargar líneas
            self.lines = lines or []
            self._render_lines()
            self._update_totals()

        except Exception:
            logging.exception(f'Error cargando albarán {self.albaran_id}')

    def _on_nombre_selected(self, event=None):
        try:
            producto = self.cb_nombre.get_producto_data()
            if producto:
                try:
                    self.e_coste.delete(0, 'end')
                    self.e_coste.insert(0, f"{producto.get('coste', 0.0):.2f}")
                except Exception:
                    pass
                self._current_producto = producto
                try:
                    self.e_uds.focus_set()
                except Exception:
                    pass
        except Exception:
            logging.exception('Error en _on_nombre_selected')

    def _recalc_importe(self, event=None):
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
            ean = (self.e_ean.get() or '').strip()
            if not ean:
                return

            producto = self.albaran_service.buscar_producto_by_ean(ean)
            if producto:
                try:
                    self.cb_nombre.set(producto.get('nombre', ''))
                    self.e_coste.delete(0, 'end')
                    self.e_coste.insert(0, f"{producto.get('coste', 0.0):.2f}")
                except Exception:
                    pass
                self._current_producto = producto
                try:
                    self.e_uds.focus_set()
                except Exception:
                    pass
            else:
                try:
                    self.cb_nombre.set('NO ENCONTRADO')
                    self.e_coste.delete(0, 'end')
                    self.e_coste.insert(0, '0.00')
                except Exception:
                    pass
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
            # When user double-clicks a line, populate input fields for editing
            # Find the corresponding index in self.lines by matching id or EAN+nombre
            idx = None
            # First try by stored DB id
            row_id = data.get('_idx')
            if row_id:
                for i, ln in enumerate(self.lines):
                    if ln.get('id') == row_id:
                        idx = i
                        break
            if idx is None:
                # Fallback: match by EAN and name
                for i, ln in enumerate(self.lines):
                    if ln.get('ean') == data.get('EAN') and ln.get('nombre') == data.get('NOMBRE'):
                        idx = i
                        break

            if idx is None:
                return

            line = self.lines[idx]
            # Populate input fields
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

            # Mark editing index and focus on quantity
            try:
                self._editing_index = idx
                self.e_uds.focus_set()
            except Exception:
                pass

        except Exception:
            logging.exception('Error manejando doble click en línea del albarán')

    def _add_line(self):
        try:
            try:
                uds = int(self.e_uds.get() or 0)
            except Exception:
                uds = 0
            if uds <= 0:
                return

            nombre = (self.cb_nombre.get() or '').strip()
            if '(' in nombre and nombre.endswith(')'):
                nombre = nombre.split('(')[0].strip()
            try:
                coste = float(self.e_coste.get() or 0)
            except Exception:
                coste = 0.0
            try:
                dto = float(self.e_dto.get() or 0)
            except Exception:
                dto = 0.0

            producto_id = self._current_producto.get('id') if hasattr(self, '_current_producto') and self._current_producto else None
            tipo_iva = self._current_producto.get('tipo_iva') if hasattr(self, '_current_producto') and self._current_producto else 21

            line = {
                'producto_id': producto_id,
                'ean': (self.e_ean.get() or '').strip(),
                'nombre': nombre,
                'cantidad': uds,
                'coste': coste,
                'descuento': dto,
                'tipo_iva': tipo_iva
            }

            # If editing, replace the line at editing index
            if self._editing_index is not None and 0 <= self._editing_index < len(self.lines):
                try:
                    self.lines[self._editing_index] = line
                except Exception:
                    self.lines.append(line)
                self._editing_index = None
            else:
                self.lines.append(line)
            self._render_lines()
            self._update_totals()

            # Limpiar
            try:
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
                pass

        except Exception:
            logging.exception('Error añadiendo línea')

    def _render_lines(self):
        try:
            # Reemplazar contenido del NavList
            try:
                self.nav_list.clear_items()
            except Exception:
                pass

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
            neto = Decimal('0.0')
            iva4 = Decimal('0.0')
            iva10 = Decimal('0.0')
            iva21 = Decimal('0.0')

            for line in self.lines:
                cantidad = Decimal(str(line['cantidad']))
                coste = line['coste'] if isinstance(line['coste'], Decimal) else Decimal(str(line['coste']))
                descuento = line['descuento'] if isinstance(line['descuento'], Decimal) else Decimal(str(line['descuento']))
                importe_linea = (cantidad * coste) - descuento
                neto += importe_linea

                tipo = line['tipo_iva']
                iva_calc = importe_linea * (Decimal(str(tipo)) / Decimal('100'))

                if tipo == 4:
                    iva4 += iva_calc
                elif tipo == 10:
                    iva10 += iva_calc
                elif tipo == 21:
                    iva21 += iva_calc

            total = neto + iva4 + iva10 + iva21

            try:
                self.lbl_neto.configure(text=f'Neto: {neto:.2f}€')
                self.lbl_iva4.configure(text=f'IVA 4%: {iva4:.2f}€')
                self.lbl_iva10.configure(text=f'IVA 10%: {iva10:.2f}€')
                self.lbl_iva21.configure(text=f'IVA 21%: {iva21:.2f}€')
                self.lbl_total.configure(text=f'TOTAL: {total:.2f}€')
            except Exception:
                pass
        except Exception:
            logging.exception('Error actualizando totales')

    def _save_albaran(self):
        """Guardar cambios: nuevas líneas + recalcular totales + actualizar stock."""
        try:
            # Validar que hay líneas
            if not self.lines:
                logging.warning('No hay líneas para guardar')
                try:
                    from kool_tpv.utils.custom_dialog import show_error
                    show_error(self.container, 'Error', 'No hay líneas en el albarán')
                except Exception:
                    pass
                return

            # Llamar al servicio para actualizar
            success = self.albaran_service.update_albaran_with_new_lines(
                self.albaran_id,
                self.lines
            )

            if success:
                logging.info(f'Albarán {self.albaran_id} actualizado correctamente')
                try:
                    show_success(self.container, 'Guardado', f'Albarán actualizado correctamente')
                except Exception:
                    pass

                # Recargar datos actualizados desde BD
                try:
                    self._load_albaran()
                except Exception:
                    logging.exception('Error recargando albarán tras guardar')

            else:
                logging.error(f'Error actualizando albarán {self.albaran_id}')
                try:
                    from kool_tpv.utils.custom_dialog import show_error
                    show_error(self.container, 'Error', 'No se pudo guardar el albarán')
                except Exception:
                    pass

        except Exception:
            logging.exception('Error en _save_albaran')
            try:
                from kool_tpv.utils.custom_dialog import show_error
                show_error(self.container, 'Error', 'Error inesperado al guardar')
            except Exception:
                pass

    def _print_albaran(self):
        """Imprimir albarán (pendiente implementar)."""
        try:
            logging.info(f'Imprimir albarán {self.albaran_id} (pendiente implementar)')
            try:
                show_success(self.container, 'Imprimir', 'Función pendiente de implementar')
            except Exception:
                pass
        except Exception:
            logging.exception('Error imprimiendo albarán')
