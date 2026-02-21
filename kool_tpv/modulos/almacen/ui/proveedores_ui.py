"""UI de Proveedores - estética Matrix, grid 8 columnas."""
from typing import Optional
import logging
import webbrowser
import tkinter as tk
import customtkinter as ctk

from kool_tpv.base_datos.proveedor_service import ProveedorService
from kool_tpv.utils.utils import COLOR_BG_TERMINAL, COLOR_MATRIX, FONT_TERMINAL, FONT_BUTTONS
from kool_tpv.utils.config_loader import create_action_button


class ProveedoresUI:
    def __init__(self, parent, db=None, owner=None, module_name: str = 'almacen'):
        self.parent = parent
        self.db = db
        self.owner = owner
        self.module_name = module_name
        from kool_tpv.utils.config_loader import load_colors
        try:
            self.colors = load_colors(module_name)
        except Exception:
            self.colors = {'text': COLOR_MATRIX, 'primary': COLOR_MATRIX, 'secondary': COLOR_MATRIX}
        self.service = ProveedorService(db)
        self.container = ctk.CTkFrame(self.parent, fg_color=self.colors.get('background', COLOR_BG_TERMINAL))

        # defaults for entries/textboxes and buttons palette
        default_entry_kw = {
            'fg_color': self.colors.get('background', COLOR_BG_TERMINAL),
            'text_color': self.colors.get('text', COLOR_MATRIX),
            'border_color': self.colors.get('border', self.colors.get('primary')),
            'height': 32
        }
        self._buttons_cfg = self.colors.get('buttons', {})
        self._primary_btn = self._buttons_cfg.get('primary', {})
        self._secondary_btn = self._buttons_cfg.get('secondary', {})

        # Grid area
        self.grid_frame = ctk.CTkFrame(self.container, fg_color='transparent')
        self.grid_frame.pack(fill='both', expand=True, padx=12, pady=6)

        for c in range(8):
            self.grid_frame.grid_columnconfigure(c, weight=1)

        lbl_font = FONT_TERMINAL
        entry_kw = default_entry_kw.copy()
        entry_kw.update({'border_width': 2})

        # Fila 0: ID | NOMBRE
        ctk.CTkLabel(self.grid_frame, text='ID:', text_color=self.colors['text'], font=lbl_font).grid(row=0, column=0, sticky='w', padx=6, pady=6)
        e_id_kwargs = default_entry_kw.copy()
        e_id_kwargs.update({'state': 'disabled', 'text_color': self.colors.get('light', '#666666')})
        self.e_id = ctk.CTkEntry(self.grid_frame, placeholder_text='ID', **e_id_kwargs)
        self.e_id.grid(row=0, column=1, sticky='ew', padx=6, pady=6)

        ctk.CTkLabel(self.grid_frame, text='NOMBRE:', text_color=self.colors['text'], font=lbl_font).grid(row=0, column=2, sticky='w', padx=6, pady=6)
        self.e_nombre = ctk.CTkEntry(self.grid_frame, placeholder_text='Nombre del proveedor', **entry_kw)
        self.e_nombre.grid(row=0, column=3, columnspan=5, sticky='ew', padx=6, pady=6)

        # Fila 1: QUE_VENDE (campo entry simple)
        ctk.CTkLabel(self.grid_frame, text='QUÉ VENDE:', text_color=self.colors['text'], font=lbl_font).grid(row=1, column=0, sticky='w', padx=6, pady=6)
        self.e_que_vende = ctk.CTkEntry(self.grid_frame, placeholder_text='Descripción de productos/servicios', **entry_kw)
        self.e_que_vende.grid(row=1, column=1, columnspan=7, sticky='ew', padx=6, pady=6)

        # Fila 2: NIF_CIF | IVA_INTRACOM | FORMA_PAGO
        ctk.CTkLabel(self.grid_frame, text='NIF/CIF:', text_color=self.colors['text'], font=lbl_font).grid(row=2, column=0, sticky='w', padx=6, pady=6)
        self.e_nif = ctk.CTkEntry(self.grid_frame, placeholder_text='NIF/CIF', **entry_kw)
        self.e_nif.grid(row=2, column=1, columnspan=2, sticky='ew', padx=6, pady=6)

        ctk.CTkLabel(self.grid_frame, text='IVA INTRA:', text_color=self.colors['text'], font=lbl_font).grid(row=2, column=3, sticky='w', padx=6, pady=6)
        self.e_iva_intra = ctk.CTkEntry(self.grid_frame, placeholder_text='IVA Intracom', **entry_kw)
        self.e_iva_intra.grid(row=2, column=4, columnspan=1, sticky='ew', padx=6, pady=6)

        ctk.CTkLabel(self.grid_frame, text='FORMA PAGO:', text_color=self.colors['text'], font=lbl_font).grid(row=2, column=5, sticky='w', padx=6, pady=6)
        self.e_forma_pago = ctk.CTkEntry(self.grid_frame, placeholder_text='30 días...', **entry_kw)
        self.e_forma_pago.grid(row=2, column=6, columnspan=2, sticky='ew', padx=6, pady=6)

        # Fila 3: DIR_FISCAL (label)
        ctk.CTkLabel(self.grid_frame, text='DIR. FISCAL:', text_color=self.colors['text'], font=lbl_font).grid(row=3, column=0, sticky='nw', padx=6, pady=6)
        # Fila 3: DIR_ENVIO (label)
        ctk.CTkLabel(self.grid_frame, text='DIR. ENVÍO:', text_color=self.colors['text'], font=lbl_font).grid(row=3, column=4, sticky='nw', padx=6, pady=6)
        # Fila 4: Textboxes de DIR_FISCAL y DIR_ENVIO en misma fila
        # CTkTextbox does not accept duplicate 'height' if present in entry_kw
        txt_kwargs = entry_kw.copy()
        txt_kwargs.pop('height', None)
        self.txt_dir_fiscal = ctk.CTkTextbox(self.grid_frame, height=60, **txt_kwargs)
        self.txt_dir_fiscal.grid(row=4, column=0, columnspan=4, sticky='ew', padx=6, pady=6)

        txt_kwargs2 = entry_kw.copy()
        txt_kwargs2.pop('height', None)
        self.txt_dir_envio = ctk.CTkTextbox(self.grid_frame, height=60, **txt_kwargs2)
        self.txt_dir_envio.grid(row=4, column=4, columnspan=4, sticky='ew', padx=6, pady=6)

        # Fila 5: EMAIL | TELEFONO
        ctk.CTkLabel(self.grid_frame, text='EMAIL:', text_color=self.colors['text'], font=lbl_font).grid(row=5, column=0, sticky='w', padx=6, pady=6)
        self.e_email = ctk.CTkEntry(self.grid_frame, placeholder_text='email@ejemplo.com', **entry_kw)
        self.e_email.grid(row=5, column=1, columnspan=3, sticky='ew', padx=6, pady=6)

        ctk.CTkLabel(self.grid_frame, text='TELÉFONO:', text_color=self.colors['text'], font=lbl_font).grid(row=5, column=4, sticky='w', padx=6, pady=6)
        self.e_telefono = ctk.CTkEntry(self.grid_frame, placeholder_text='Teléfono', **entry_kw)
        self.e_telefono.grid(row=5, column=5, columnspan=3, sticky='ew', padx=6, pady=6)

        # Fila 6: COMERCIAL | TLF_COMERCIAL | EMAIL_COMERCIAL
        ctk.CTkLabel(self.grid_frame, text='COMERCIAL:', text_color=self.colors['text'], font=lbl_font).grid(row=6, column=0, sticky='w', padx=6, pady=6)
        self.e_comercial = ctk.CTkEntry(self.grid_frame, placeholder_text='Nombre', **entry_kw)
        self.e_comercial.grid(row=6, column=1, columnspan=2, sticky='ew', padx=6, pady=6)

        ctk.CTkLabel(self.grid_frame, text='TLF:', text_color=self.colors['text'], font=lbl_font).grid(row=6, column=3, sticky='w', padx=6, pady=6)
        self.e_tlf_comercial = ctk.CTkEntry(self.grid_frame, placeholder_text='Teléfono', **entry_kw)
        self.e_tlf_comercial.grid(row=6, column=4, columnspan=1, sticky='ew', padx=6, pady=6)

        ctk.CTkLabel(self.grid_frame, text='EMAIL:', text_color=self.colors['text'], font=lbl_font).grid(row=6, column=5, sticky='w', padx=6, pady=6)
        self.e_email_comercial = ctk.CTkEntry(self.grid_frame, placeholder_text='email comercial', **entry_kw)
        self.e_email_comercial.grid(row=6, column=6, columnspan=2, sticky='ew', padx=6, pady=6)

        # Fila 7: WEB | BTN_IR
        ctk.CTkLabel(self.grid_frame, text='WEB:', text_color=self.colors['text'], font=lbl_font).grid(row=7, column=0, sticky='w', padx=6, pady=6)
        self.e_web = ctk.CTkEntry(self.grid_frame, placeholder_text='https://...', **entry_kw)
        self.e_web.grid(row=7, column=1, columnspan=6, sticky='ew', padx=6, pady=6)

        self.btn_ir_web = ctk.CTkButton(
            self.grid_frame,
            text='IR',
            width=60,
            fg_color=self._secondary_btn.get('bg', '#2980b9'),
            hover_color=self._secondary_btn.get('hover', '#2a7ab8'),
            text_color=self._secondary_btn.get('text', self.colors.get('text', COLOR_MATRIX)),
            command=self._abrir_web
        )
        self.btn_ir_web.grid(row=7, column=7, sticky='ew', padx=6, pady=6)

        # Fila 8: NOTAS (campo entry simple)
        ctk.CTkLabel(self.grid_frame, text='NOTAS:', text_color=self.colors['text'], font=lbl_font).grid(row=8, column=0, sticky='w', padx=6, pady=6)
        self.e_notas = ctk.CTkEntry(self.grid_frame, placeholder_text='Observaciones internas', **entry_kw)
        self.e_notas.grid(row=8, column=1, columnspan=7, sticky='ew', padx=6, pady=6)

        # Fila 9: Chips area
        self.grid_frame.grid_rowconfigure(9, weight=1)
        self.chips_frame = ctk.CTkScrollableFrame(self.grid_frame, fg_color=self.colors.get('background', COLOR_BG_TERMINAL))
        self.chips_frame.grid(row=9, column=0, columnspan=8, sticky='nsew', padx=6, pady=6)

        # Footer buttons (desde config)
        self.footer = ctk.CTkFrame(self.container, fg_color='transparent')
        self.footer.pack(side='bottom', fill='x', padx=12, pady=12)

        self.btn_nuevo = create_action_button(self.footer, 'nuevo_limpiar', self.clear)
        self.btn_nuevo.pack(side='left', padx=8)

        self.btn_guardar = create_action_button(self.footer, 'guardar', self.save)
        self.btn_guardar.pack(side='left', padx=8)

        self.btn_eliminar = create_action_button(self.footer, 'eliminar', self.delete)
        self.btn_eliminar.pack(side='left', padx=8)

        self.btn_albaranes = create_action_button(self.footer, 'consultar_albaranes', self._mostrar_albaranes)
        self.btn_albaranes.pack(side='left', padx=8)

        self.btn_mapeo = create_action_button(self.footer, 'mapeo_csv', self._editar_mapeo_csv)
        self.btn_mapeo.pack(side='left', padx=8)

        # Load proveedores
        self.selected_chip = None
        self._load_proveedores()

    def get_widget(self):
        return self.container

    def cargar_proveedor(self, proveedor_id):
        """Cargar proveedor por ID en el formulario.

        Args:
            proveedor_id: ID del proveedor a cargar

        Returns:
            bool: True si se cargó correctamente, False si no existe
        """
        try:
            # Obtener proveedor desde BD
            prov = self.service.get_proveedor(proveedor_id)

            if not prov:
                logging.warning(f'Proveedor {proveedor_id} no encontrado')
                return False

            # Cargar en formulario
            self._load_proveedor_into_form(prov)

            # Seleccionar chip correspondiente
            try:
                for child in list(self.chips_frame.winfo_children()):
                    if hasattr(child, '_prov_data') and child._prov_data.get('id') == proveedor_id:
                        self._select_chip(child)
                        break
            except Exception:
                logging.exception('Error seleccionando chip en cargar_proveedor')

            logging.info(f'Proveedor {proveedor_id} cargado correctamente')
            return True

        except Exception:
            logging.exception(f'Error cargando proveedor {proveedor_id}')
            return False

    def _load_proveedores(self):
        try:
            logging.debug('ProveedoresUI: limpiando chips existentes')
            for w in list(self.chips_frame.winfo_children()):
                try:
                    w.destroy()
                except Exception:
                    pass
            provs = self.service.get_all_proveedores()
            logging.info(f'ProveedoresUI: obtenidos {len(provs or [])} proveedores')
            if not provs:
                # show helpful placeholder so user sees empty state
                try:
                    ctk.CTkLabel(self.chips_frame, text='No hay proveedores', text_color=self.colors.get('text'), fg_color='transparent').grid(row=0, column=0, padx=6, pady=6)
                except Exception:
                    pass
                return

            for i, p in enumerate(provs):
                row = i // 6
                col = i % 6
                name = p.get('nombre') or ''
                btn = ctk.CTkButton(
                    self.chips_frame,
                    text=name,
                    fg_color=self._primary_btn.get('bg', 'transparent'),
                    text_color=self._primary_btn.get('text', self.colors['text']),
                    border_width=2,
                    border_color=self._primary_btn.get('border', self.colors.get('border', self.colors['primary'])),
                    height=28
                )
                btn.grid(row=row, column=col, padx=5, pady=5, sticky='w')
                btn.bind('<Button-1>', lambda e, btn=btn: self._select_chip(btn))
                btn.bind('<Double-Button-1>', lambda e, prov=p: self._load_proveedor_into_form(prov))
                setattr(btn, '_prov_data', p)
        except Exception:
            logging.exception('Error cargando chips de proveedores')

    def _select_chip(self, btn):
        try:
            if self.selected_chip is not None:
                try:
                    self.selected_chip.configure(border_color=self._primary_btn.get('border', self.colors.get('border', self.colors['primary'])))
                except Exception:
                    pass
            self.selected_chip = btn
            try:
                    btn.configure(border_color=self._primary_btn.get('hover', self.colors.get('secondary', self.colors['primary'])))
            except Exception:
                pass
        except Exception:
            pass

    def _load_proveedor_into_form(self, prov: dict):
        try:
            self.e_id.configure(state='normal')
            self.e_id.delete(0, 'end')
            self.e_id.insert(0, str(prov.get('id') or ''))
            self.e_id.configure(state='disabled')

            self.e_nombre.delete(0, 'end')
            self.e_nombre.insert(0, prov.get('nombre') or '')

            self.e_que_vende.delete(0, 'end')
            self.e_que_vende.insert(0, prov.get('que_vende') or '')

            self.e_nif.delete(0, 'end')
            self.e_nif.insert(0, prov.get('nif_cif') or '')

            self.e_iva_intra.delete(0, 'end')
            self.e_iva_intra.insert(0, prov.get('iva_intracom') or '')

            self.e_forma_pago.delete(0, 'end')
            self.e_forma_pago.insert(0, prov.get('forma_pago') or '')

            self.txt_dir_fiscal.delete('1.0', 'end')
            self.txt_dir_fiscal.insert('1.0', prov.get('dir_fiscal') or '')

            self.txt_dir_envio.delete('1.0', 'end')
            self.txt_dir_envio.insert('1.0', prov.get('dir_envio') or '')

            self.e_email.delete(0, 'end')
            self.e_email.insert(0, prov.get('email') or '')

            self.e_telefono.delete(0, 'end')
            self.e_telefono.insert(0, prov.get('telefono') or '')

            self.e_comercial.delete(0, 'end')
            self.e_comercial.insert(0, prov.get('persona_comercial') or '')

            self.e_tlf_comercial.delete(0, 'end')
            self.e_tlf_comercial.insert(0, prov.get('telefono_comercial') or '')

            self.e_email_comercial.delete(0, 'end')
            self.e_email_comercial.insert(0, prov.get('email_comercial') or '')

            self.e_web.delete(0, 'end')
            self.e_web.insert(0, prov.get('web') or '')

            self.e_notas.delete(0, 'end')
            self.e_notas.insert(0, prov.get('notas') or '')

            self.btn_guardar.configure(text='ACTUALIZAR')
        except Exception:
            logging.exception('Error cargando proveedor en formulario')

    def clear(self):
        try:
            self.e_id.configure(state='normal')
            self.e_id.delete(0, 'end')
            self.e_id.configure(state='disabled')

            self.e_nombre.delete(0, 'end')
            self.e_que_vende.delete(0, 'end')
            self.e_nif.delete(0, 'end')
            self.e_iva_intra.delete(0, 'end')
            self.e_forma_pago.delete(0, 'end')
            self.txt_dir_fiscal.delete('1.0', 'end')
            self.txt_dir_envio.delete('1.0', 'end')
            self.e_email.delete(0, 'end')
            self.e_telefono.delete(0, 'end')
            self.e_comercial.delete(0, 'end')
            self.e_tlf_comercial.delete(0, 'end')
            self.e_email_comercial.delete(0, 'end')
            self.e_web.delete(0, 'end')
            self.e_notas.delete(0, 'end')

            self.btn_guardar.configure(text='GUARDAR')
        except Exception:
            logging.exception('Error limpiando formulario proveedores')

    def save(self):
        try:
            nombre = self.e_nombre.get().strip()
            if not nombre:
                return

            data = {
                'nombre': nombre,
                'que_vende': self.e_que_vende.get().strip(),
                'nif_cif': self.e_nif.get().strip(),
                'iva_intracom': self.e_iva_intra.get().strip(),
                'dir_fiscal': self.txt_dir_fiscal.get('1.0', 'end-1c').strip(),
                'dir_envio': self.txt_dir_envio.get('1.0', 'end-1c').strip(),
                'email': self.e_email.get().strip(),
                'telefono': self.e_telefono.get().strip(),
                'forma_pago': self.e_forma_pago.get().strip(),
                'persona_comercial': self.e_comercial.get().strip(),
                'telefono_comercial': self.e_tlf_comercial.get().strip(),
                'email_comercial': self.e_email_comercial.get().strip(),
                'web': self.e_web.get().strip(),
                'notas': self.e_notas.get().strip()
            }

            id_val = None
            try:
                id_text = self.e_id.get()
                id_val = int(id_text) if id_text else None
            except Exception:
                id_val = None

            if id_val:
                ok = self.service.update_proveedor(id_val, **data)
            else:
                ok = self.service.save_proveedor(**data)

            if ok:
                self.clear()
                self._load_proveedores()
        except Exception:
            logging.exception('Error guardando proveedor')

    def delete(self):
        try:
            id_text = self.e_id.get()
            id_val = int(id_text) if id_text else None
            if not id_val:
                return

            ok = self.service.delete_proveedor(id_val)
            if ok:
                self.clear()
                self._load_proveedores()
        except Exception:
            logging.exception('Error eliminando proveedor')

    def _abrir_web(self):
        try:
            url = self.e_web.get().strip()
            if url:
                if not url.startswith('http'):
                    url = 'https://' + url
                webbrowser.open(url)
        except Exception:
            logging.exception('Error abriendo web proveedor')

    def _mostrar_albaranes(self):
        logging.info('Función CONSULTAR ALBARANES - pendiente implementar')

    def _editar_mapeo_csv(self):
        """Abrir editor de mapeo CSV delegando al owner."""
        try:
            # Obtener ID del proveedor actual
            id_text = self.e_id.get().strip()
            if not id_text:
                from kool_tpv.utils.custom_dialog import show_warning
                show_warning(self.container, 'Sin proveedor',
                             'Selecciona un proveedor antes de configurar el mapeo CSV')
                return

            try:
                prov_id = int(id_text)
            except ValueError:
                logging.error('ID proveedor no válido en _editar_mapeo_csv')
                return

            # Obtener nombre del proveedor
            nombre_prov = self.e_nombre.get().strip() or 'Proveedor'

            # Delegar a owner (AlmacenView)
            if getattr(self, 'owner', None) and hasattr(self.owner, 'show_mapeo_csv'):
                try:
                    self.owner.show_mapeo_csv(prov_id, nombre_prov)
                except Exception:
                    logging.exception(f'Error llamando owner.show_mapeo_csv para {prov_id}')
                    from kool_tpv.utils.custom_dialog import show_error
                    show_error(self.container, 'Error', 'No se puede abrir editor de mapeo')
            else:
                logging.warning('ProveedoresUI: owner no disponible para show_mapeo_csv')
                from kool_tpv.utils.custom_dialog import show_error
                show_error(self.container, 'Error', 'No se puede abrir editor de mapeo')

        except Exception:
            logging.exception('Error en _editar_mapeo_csv')

    
