"""UI de Proveedores del módulo de Producción."""
from typing import Optional
import logging
import webbrowser
import tkinter as tk
import customtkinter as ctk

from kool_tpv.base_datos.proveedor_service import ProveedorService
from kool_tpv.utils.utils import COLOR_BG_TERMINAL, COLOR_MATRIX
from kool_tpv.utils.font_loader import get_font
from kool_tpv.utils.config_loader import create_action_button
from kool_tpv.utils.factories.button_factory import ButtonFactory


class ProduccionProveedoresView:
    def __init__(self, parent, db=None, owner=None, module_name: str = 'produccion'):
        self.parent = parent
        self.db = db
        self.owner = owner
        self.module_name = module_name
        from kool_tpv.utils.config_loader import load_colors
        try:
            self.colors = load_colors(module_name)
        except Exception:
            self.colors = {'text': COLOR_MATRIX, 'primary': COLOR_MATRIX}
        self.service = ProveedorService(db)
        self.container = ctk.CTkFrame(self.parent, fg_color=self.colors.get('background', COLOR_BG_TERMINAL))
        self._build_grid()
        self._build_footer()
        self.selected_chip = None
        self._load_proveedores()

    def _build_grid(self):
        self.grid_frame = ctk.CTkFrame(self.container, fg_color='transparent')
        self.grid_frame.pack(fill='both', expand=True, padx=12, pady=6)
        for c in range(8):
            self.grid_frame.grid_columnconfigure(c, weight=1)
        lbl_font = get_font('label', module=self.module_name)
        ekw = {'fg_color': self.colors.get('background', COLOR_BG_TERMINAL),
               'text_color': self.colors.get('text', COLOR_MATRIX),
               'border_color': self.colors.get('border', self.colors.get('primary')),
               'height': 32, 'border_width': 2}
        # Fila 0: ID | NOMBRE
        ctk.CTkLabel(self.grid_frame, text='ID:', text_color=self.colors['text'], font=lbl_font).grid(row=0, column=0, sticky='w', padx=6, pady=6)
        idkw = ekw.copy(); idkw.update({'state': 'disabled', 'text_color': self.colors.get('light', '#666666')})
        self.e_id = ctk.CTkEntry(self.grid_frame, placeholder_text='ID', **idkw)
        self.e_id.grid(row=0, column=1, sticky='ew', padx=6, pady=6)
        ctk.CTkLabel(self.grid_frame, text='NOMBRE:', text_color=self.colors['text'], font=lbl_font).grid(row=0, column=2, sticky='w', padx=6, pady=6)
        self.e_nombre = ctk.CTkEntry(self.grid_frame, placeholder_text='Nombre del proveedor', **ekw)
        self.e_nombre.grid(row=0, column=3, columnspan=5, sticky='ew', padx=6, pady=6)
        # Fila 1: QUE_VENDE
        ctk.CTkLabel(self.grid_frame, text='QUÉ VENDE:', text_color=self.colors['text'], font=lbl_font).grid(row=1, column=0, sticky='w', padx=6, pady=6)
        self.e_que_vende = ctk.CTkEntry(self.grid_frame, placeholder_text='Descripción', **ekw)
        self.e_que_vende.grid(row=1, column=1, columnspan=7, sticky='ew', padx=6, pady=6)
        # Fila 2: NIF | IVA | PAGO
        ctk.CTkLabel(self.grid_frame, text='NIF/CIF:', text_color=self.colors['text'], font=lbl_font).grid(row=2, column=0, sticky='w', padx=6, pady=6)
        self.e_nif = ctk.CTkEntry(self.grid_frame, placeholder_text='NIF/CIF', **ekw)
        self.e_nif.grid(row=2, column=1, columnspan=2, sticky='ew', padx=6, pady=6)
        ctk.CTkLabel(self.grid_frame, text='IVA INTRA:', text_color=self.colors['text'], font=lbl_font).grid(row=2, column=3, sticky='w', padx=6, pady=6)
        self.e_iva_intra = ctk.CTkEntry(self.grid_frame, placeholder_text='IVA', **ekw)
        self.e_iva_intra.grid(row=2, column=4, sticky='ew', padx=6, pady=6)
        ctk.CTkLabel(self.grid_frame, text='FORMA PAGO:', text_color=self.colors['text'], font=lbl_font).grid(row=2, column=5, sticky='w', padx=6, pady=6)
        self.e_forma_pago = ctk.CTkEntry(self.grid_frame, placeholder_text='30 días...', **ekw)
        self.e_forma_pago.grid(row=2, column=6, columnspan=2, sticky='ew', padx=6, pady=6)
        # Fila 3-4: DIR FISCAL | ENVIO
        ctk.CTkLabel(self.grid_frame, text='DIR. FISCAL:', text_color=self.colors['text'], font=lbl_font).grid(row=3, column=0, sticky='nw', padx=6, pady=6)
        ctk.CTkLabel(self.grid_frame, text='DIR. ENVÍO:', text_color=self.colors['text'], font=lbl_font).grid(row=3, column=4, sticky='nw', padx=6, pady=6)
        tkw = ekw.copy(); tkw.pop('height', None)
        self.txt_dir_fiscal = ctk.CTkTextbox(self.grid_frame, height=60, **tkw)
        self.txt_dir_fiscal.grid(row=4, column=0, columnspan=4, sticky='ew', padx=6, pady=6)
        self.txt_dir_envio = ctk.CTkTextbox(self.grid_frame, height=60, **tkw)
        self.txt_dir_envio.grid(row=4, column=4, columnspan=4, sticky='ew', padx=6, pady=6)
        # Fila 5: EMAIL | TLF
        ctk.CTkLabel(self.grid_frame, text='EMAIL:', text_color=self.colors['text'], font=lbl_font).grid(row=5, column=0, sticky='w', padx=6, pady=6)
        self.e_email = ctk.CTkEntry(self.grid_frame, placeholder_text='email@ejemplo.com', **ekw)
        self.e_email.grid(row=5, column=1, columnspan=3, sticky='ew', padx=6, pady=6)
        ctk.CTkLabel(self.grid_frame, text='TELÉFONO:', text_color=self.colors['text'], font=lbl_font).grid(row=5, column=4, sticky='w', padx=6, pady=6)
        self.e_telefono = ctk.CTkEntry(self.grid_frame, placeholder_text='Teléfono', **ekw)
        self.e_telefono.grid(row=5, column=5, columnspan=3, sticky='ew', padx=6, pady=6)
        # Fila 6: COMERCIAL | TLF | EMAIL
        ctk.CTkLabel(self.grid_frame, text='COMERCIAL:', text_color=self.colors['text'], font=lbl_font).grid(row=6, column=0, sticky='w', padx=6, pady=6)
        self.e_comercial = ctk.CTkEntry(self.grid_frame, placeholder_text='Nombre', **ekw)
        self.e_comercial.grid(row=6, column=1, columnspan=2, sticky='ew', padx=6, pady=6)
        ctk.CTkLabel(self.grid_frame, text='TLF:', text_color=self.colors['text'], font=lbl_font).grid(row=6, column=3, sticky='w', padx=6, pady=6)
        self.e_tlf_comercial = ctk.CTkEntry(self.grid_frame, placeholder_text='Teléfono', **ekw)
        self.e_tlf_comercial.grid(row=6, column=4, sticky='ew', padx=6, pady=6)
        ctk.CTkLabel(self.grid_frame, text='EMAIL:', text_color=self.colors['text'], font=lbl_font).grid(row=6, column=5, sticky='w', padx=6, pady=6)
        self.e_email_comercial = ctk.CTkEntry(self.grid_frame, placeholder_text='email comercial', **ekw)
        self.e_email_comercial.grid(row=6, column=6, columnspan=2, sticky='ew', padx=6, pady=6)
        # Fila 7: WEB | IR
        ctk.CTkLabel(self.grid_frame, text='WEB:', text_color=self.colors['text'], font=lbl_font).grid(row=7, column=0, sticky='w', padx=6, pady=6)
        self.e_web = ctk.CTkEntry(self.grid_frame, placeholder_text='https://...', **ekw)
        self.e_web.grid(row=7, column=1, columnspan=6, sticky='ew', padx=6, pady=6)
        self.btn_ir_web = ButtonFactory.create_button(parent=self.grid_frame, text='IR', command=self._abrir_web, style_key="mini_action")
        self.btn_ir_web.grid(row=7, column=7, sticky='ew', padx=6, pady=6)
        # Fila 8: NOTAS
        ctk.CTkLabel(self.grid_frame, text='NOTAS:', text_color=self.colors['text'], font=lbl_font).grid(row=8, column=0, sticky='w', padx=6, pady=6)
        self.e_notas = ctk.CTkEntry(self.grid_frame, placeholder_text='Observaciones', **ekw)
        self.e_notas.grid(row=8, column=1, columnspan=7, sticky='ew', padx=6, pady=6)
        # Fila 9: Chips
        self.grid_frame.grid_rowconfigure(9, weight=1)
        self.chips_frame = ctk.CTkScrollableFrame(self.grid_frame, fg_color=self.colors.get('background', COLOR_BG_TERMINAL))
        self.chips_frame.grid(row=9, column=0, columnspan=8, sticky='nsew', padx=6, pady=6)

    def _build_footer(self):
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
        self.btn_config_mapeos = create_action_button(self.footer, 'configurar_mapeos', self._abrir_configurador_mapeos)
        self.btn_config_mapeos.pack(side='left', padx=8)

        self.btn_importar = create_action_button(self.footer, 'importar_albaran', self._importar_albaran)
        self.btn_importar.pack(side='right', padx=8)

    def _abrir_configurador_mapeos(self):
        try:
            id_text = self.e_id.get().strip()
            if not id_text:
                from kool_tpv.utils.widgets.notificaciones import show_warning
                show_warning(self.container, 'Selecciona un proveedor antes de configurar los mapeos')
                return
            prov_id = int(id_text)
            nombre_prov = self.e_nombre.get().strip() or 'Proveedor'
            if getattr(self, 'owner', None) and hasattr(self.owner, 'show_configurar_mapeos'):
                self.owner.show_configurar_mapeos(prov_id, nombre_prov)
            else:
                from kool_tpv.utils.custom_dialog import show_error
                show_error(self.container, 'Error', 'No se puede abrir el configurador de mapeos')
        except Exception:
            logging.exception('Error en _abrir_configurador_mapeos')

    def get_widget(self):
        return self.container

    def cargar_proveedor(self, proveedor_id):
        try:
            prov = self.service.get_proveedor(proveedor_id)
            if not prov:
                return False
            self._load_proveedor_into_form(prov)
            for child in list(self.chips_frame.winfo_children()):
                if hasattr(child, '_prov_data') and child._prov_data.get('id') == proveedor_id:
                    self._select_chip(child)
                    break
            return True
        except Exception:
            logging.exception(f'Error cargando proveedor {proveedor_id}')
            return False

    def _load_proveedores(self):
        try:
            for w in list(self.chips_frame.winfo_children()):
                w.destroy()
            provs = self.service.get_proveedores_con_mapeos()
            if not provs:
                ctk.CTkLabel(self.chips_frame, text='No hay proveedores', text_color=self.colors.get('text'), fg_color='transparent').grid(row=0, column=0, padx=6, pady=6)
                return
            for i, p in enumerate(provs):
                row = i // 6
                col = i % 6
                btn = ButtonFactory.create_button(parent=self.chips_frame, text=p.get('nombre') or '', command=None, style_key="chip_default")
                btn.grid(row=row, column=col, padx=5, pady=5, sticky='w')
                btn.bind('<Button-1>', lambda e, btn=btn: self._select_chip(btn))
                btn.bind('<Double-Button-1>', lambda e, prov=p: self._load_proveedor_into_form(prov))
                setattr(btn, '_prov_data', p)
        except Exception:
            logging.exception('Error cargando chips de proveedores')

    def _select_chip(self, btn):
        try:
            if self.selected_chip is not None:
                ButtonFactory.apply_style(self.selected_chip, "chip_default")
            self.selected_chip = btn
            ButtonFactory.apply_style(btn, "chip_selected")
        except Exception:
            logging.exception("Error aplicando estilos de chip")

    def _load_proveedor_into_form(self, prov: dict):
        try:
            self.e_id.configure(state='normal')
            self.e_id.delete(0, 'end')
            self.e_id.insert(0, str(prov.get('id') or ''))
            self.e_id.configure(state='disabled')
            self.e_nombre.delete(0, 'end'); self.e_nombre.insert(0, prov.get('nombre') or '')
            self.e_que_vende.delete(0, 'end'); self.e_que_vende.insert(0, prov.get('que_vende') or '')
            self.e_nif.delete(0, 'end'); self.e_nif.insert(0, prov.get('nif_cif') or '')
            self.e_iva_intra.delete(0, 'end'); self.e_iva_intra.insert(0, prov.get('iva_intracom') or '')
            self.e_forma_pago.delete(0, 'end'); self.e_forma_pago.insert(0, prov.get('forma_pago') or '')
            self.txt_dir_fiscal.delete('1.0', 'end'); self.txt_dir_fiscal.insert('1.0', prov.get('dir_fiscal') or '')
            self.txt_dir_envio.delete('1.0', 'end'); self.txt_dir_envio.insert('1.0', prov.get('dir_envio') or '')
            self.e_email.delete(0, 'end'); self.e_email.insert(0, prov.get('email') or '')
            self.e_telefono.delete(0, 'end'); self.e_telefono.insert(0, prov.get('telefono') or '')
            self.e_comercial.delete(0, 'end'); self.e_comercial.insert(0, prov.get('persona_comercial') or '')
            self.e_tlf_comercial.delete(0, 'end'); self.e_tlf_comercial.insert(0, prov.get('telefono_comercial') or '')
            self.e_email_comercial.delete(0, 'end'); self.e_email_comercial.insert(0, prov.get('email_comercial') or '')
            self.e_web.delete(0, 'end'); self.e_web.insert(0, prov.get('web') or '')
            self.e_notas.delete(0, 'end'); self.e_notas.insert(0, prov.get('notas') or '')
            self.btn_guardar.configure(text='ACTUALIZAR')
        except Exception:
            logging.exception('Error cargando proveedor en formulario')

    def clear(self):
        try:
            self.e_id.configure(state='normal'); self.e_id.delete(0, 'end'); self.e_id.configure(state='disabled')
            self.e_nombre.delete(0, 'end'); self.e_que_vende.delete(0, 'end')
            self.e_nif.delete(0, 'end'); self.e_iva_intra.delete(0, 'end'); self.e_forma_pago.delete(0, 'end')
            self.txt_dir_fiscal.delete('1.0', 'end'); self.txt_dir_envio.delete('1.0', 'end')
            self.e_email.delete(0, 'end'); self.e_telefono.delete(0, 'end')
            self.e_comercial.delete(0, 'end'); self.e_tlf_comercial.delete(0, 'end')
            self.e_email_comercial.delete(0, 'end'); self.e_web.delete(0, 'end'); self.e_notas.delete(0, 'end')
            self.btn_guardar.configure(text='GUARDAR')
        except Exception:
            logging.exception('Error limpiando formulario')

    def save(self):
        try:
            nombre = self.e_nombre.get().strip()
            if not nombre:
                return
            data = {
                'nombre': nombre, 'que_vende': self.e_que_vende.get().strip(),
                'nif_cif': self.e_nif.get().strip(), 'iva_intracom': self.e_iva_intra.get().strip(),
                'dir_fiscal': self.txt_dir_fiscal.get('1.0', 'end-1c').strip(),
                'dir_envio': self.txt_dir_envio.get('1.0', 'end-1c').strip(),
                'email': self.e_email.get().strip(), 'telefono': self.e_telefono.get().strip(),
                'forma_pago': self.e_forma_pago.get().strip(),
                'persona_comercial': self.e_comercial.get().strip(),
                'telefono_comercial': self.e_tlf_comercial.get().strip(),
                'email_comercial': self.e_email_comercial.get().strip(),
                'web': self.e_web.get().strip(), 'notas': self.e_notas.get().strip()
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
            logging.exception('Error abriendo web')

    def _mostrar_albaranes(self):
        logging.info('CONSULTAR ALBARANES - pendiente implementar')

    def _importar_albaran(self):
        try:
            id_text = self.e_id.get().strip()
            prov_id = int(id_text) if id_text else None
            nombre_prov = self.e_nombre.get().strip() or ''
            if getattr(self, 'owner', None) and hasattr(self.owner, 'show_importar_albaran'):
                self.owner.show_importar_albaran(prov_id, nombre_prov)
            else:
                from kool_tpv.utils.custom_dialog import show_error
                show_error(self.container, 'Error', 'No se puede abrir el importador de albaranes')
        except Exception:
            logging.exception('Error en _importar_albaran')
