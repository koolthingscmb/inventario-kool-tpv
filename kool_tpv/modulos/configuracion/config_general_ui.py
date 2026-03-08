import logging
import tkinter as tk
import customtkinter as ctk
from pathlib import Path

from kool_tpv.utils.utils import COLOR_BG_TERMINAL, COLOR_MATRIX, FONT_TERMINAL
from kool_tpv.utils.config_loader import load_colors
from kool_tpv.utils.font_loader import get_font


class ConfigGeneralUI:
    def __init__(self, parent, db, module_name='config'):
        self.parent = parent
        self.db = db
        self.module_name = module_name

        # Colors for this module
        try:
            self.colors = load_colors(module_name)
        except Exception:
            logging.exception('Error cargando colores en ConfigGeneralUI')
            self.colors = {}

        bg = self.colors.get('background', COLOR_BG_TERMINAL)

        # Container frame
        self.container = ctk.CTkFrame(parent, fg_color=bg)

        # Fonts and common kwargs (use font_config)
        lbl_font = get_font('label', module=module_name)
        entry_kwargs = {
            "fg_color": bg,
            "text_color": self.colors.get('text', '#FFFFFF'),
            "border_width": 2,
            "border_color": self.colors.get('border', self.colors.get('primary')),
            "corner_radius": 4,
            "font": get_font('entry', module=module_name),
        }

        # Configure grid inside container: we'll use two stacked frames with 8 columns each
        # IDENTIDAD COMERCIAL
        self.identidad_frame = ctk.CTkFrame(self.container, fg_color=bg)
        self.identidad_frame.pack(fill='both', expand=False, padx=12, pady=8)

        for c in range(8):
            try:
                self.identidad_frame.grid_columnconfigure(c, weight=1, uniform='col')
            except Exception:
                pass

        # Row 0: NOMBRE COMERCIAL (label col0, entry col1-7)
        lbl = ctk.CTkLabel(self.identidad_frame, text='Nombre comercial', font=lbl_font, text_color=self.colors.get('text'))
        lbl.grid(row=0, column=0, sticky='w', padx=6, pady=6)
        self.e_name = ctk.CTkEntry(self.identidad_frame, **entry_kwargs)
        self.e_name.grid(row=0, column=1, columnspan=7, sticky='we', padx=6, pady=6)
        self.e_name.insert(0, '')

        # Row 1: WEB (cols 1-4) | TELEFONO (cols 6-7)
        lbl_web = ctk.CTkLabel(self.identidad_frame, text='Web', font=lbl_font, text_color=self.colors.get('text'))
        lbl_web.grid(row=1, column=0, sticky='w', padx=6, pady=6)
        self.e_web = ctk.CTkEntry(self.identidad_frame, **entry_kwargs)
        self.e_web.grid(row=1, column=1, columnspan=4, sticky='we', padx=6, pady=6)
        self.e_web.insert(0, '')

        lbl_tel = ctk.CTkLabel(self.identidad_frame, text='Teléfono', font=lbl_font, text_color=self.colors.get('text'))
        lbl_tel.grid(row=1, column=5, sticky='w', padx=6, pady=6)
        self.e_phone = ctk.CTkEntry(self.identidad_frame, **entry_kwargs)
        self.e_phone.grid(row=1, column=6, columnspan=2, sticky='we', padx=6, pady=6)
        self.e_phone.insert(0, '')

        # Row 2: EMAIL
        lbl_email = ctk.CTkLabel(self.identidad_frame, text='Email', font=lbl_font, text_color=self.colors.get('text'))
        lbl_email.grid(row=2, column=0, sticky='w', padx=6, pady=6)
        self.e_email = ctk.CTkEntry(self.identidad_frame, **entry_kwargs)
        self.e_email.grid(row=2, column=1, columnspan=7, sticky='we', padx=6, pady=6)
        self.e_email.insert(0, '')

        # DATOS FISCALES
        self.fiscal_frame = ctk.CTkFrame(self.container, fg_color=bg)
        self.fiscal_frame.pack(fill='both', expand=True, padx=12, pady=(0, 8))

        for c in range(8):
            try:
                self.fiscal_frame.grid_columnconfigure(c, weight=1, uniform='col')
            except Exception:
                pass

        # PARÁMETROS FISCALES
        self.fiscal_params_frame = ctk.CTkFrame(self.container, fg_color=bg)
        self.fiscal_params_frame.pack(fill='both', expand=False, padx=12, pady=(0, 8))

        for c in range(8):
            try:
                self.fiscal_params_frame.grid_columnconfigure(c, weight=1, uniform='col')
            except Exception:
                pass

        # Label separador
        lbl_params = ctk.CTkLabel(self.fiscal_params_frame, text='PARÁMETROS FISCALES', 
                                  font=lbl_font, text_color=self.colors.get('secondary', '#FFB74D'))
        lbl_params.grid(row=0, column=0, columnspan=8, sticky='w', padx=6, pady=(12, 6))

        # Row 1: IVA GENERAL (3 cols) | IVA REDUCIDO (2 cols) | IVA SUPERREDUCIDO (3 cols)
        lbl_iva_gen = ctk.CTkLabel(self.fiscal_params_frame, text='IVA General (%)', 
                                   font=lbl_font, text_color=self.colors.get('text'))
        lbl_iva_gen.grid(row=1, column=0, sticky='w', padx=6, pady=6)
        self.e_iva_general = ctk.CTkEntry(self.fiscal_params_frame, **entry_kwargs)
        self.e_iva_general.grid(row=1, column=1, columnspan=2, sticky='we', padx=6, pady=6)
        self.e_iva_general.insert(0, '21')

        lbl_iva_red = ctk.CTkLabel(self.fiscal_params_frame, text='IVA Red. (%)', 
                                   font=lbl_font, text_color=self.colors.get('text'))
        lbl_iva_red.grid(row=1, column=3, sticky='w', padx=6, pady=6)
        self.e_iva_reducido = ctk.CTkEntry(self.fiscal_params_frame, **entry_kwargs)
        self.e_iva_reducido.grid(row=1, column=4, sticky='we', padx=6, pady=6)
        self.e_iva_reducido.insert(0, '10')

        lbl_iva_super = ctk.CTkLabel(self.fiscal_params_frame, text='IVA Superred. (%)', 
                                     font=lbl_font, text_color=self.colors.get('text'))
        lbl_iva_super.grid(row=1, column=5, sticky='w', padx=6, pady=6)
        self.e_iva_superreducido = ctk.CTkEntry(self.fiscal_params_frame, **entry_kwargs)
        self.e_iva_superreducido.grid(row=1, column=6, columnspan=2, sticky='we', padx=6, pady=6)
        self.e_iva_superreducido.insert(0, '4')

        # Row 2: RECARGO EQUIVALENCIA checkbox (3 cols) | vacío
        lbl_re = ctk.CTkLabel(self.fiscal_params_frame, text='Recargo Equiv.', 
                              font=lbl_font, text_color=self.colors.get('text'))
        lbl_re.grid(row=2, column=0, sticky='w', padx=6, pady=6)
        self.chk_re_activo = ctk.CTkCheckBox(self.fiscal_params_frame, text='Activar', 
                             fg_color=self.colors.get('secondary', '#F57C00'),
                             font=get_font('label', module=module_name))
        self.chk_re_activo.grid(row=2, column=1, columnspan=2, sticky='w', padx=6, pady=6)

        # Row 3: RE GENERAL (3 cols) | RE REDUCIDO (2 cols) | RE SUPERREDUCIDO (3 cols)
        lbl_re_gen = ctk.CTkLabel(self.fiscal_params_frame, text='RE General (%)', 
                                  font=lbl_font, text_color=self.colors.get('text'))
        lbl_re_gen.grid(row=3, column=0, sticky='w', padx=6, pady=6)
        self.e_re_general = ctk.CTkEntry(self.fiscal_params_frame, **entry_kwargs)
        self.e_re_general.grid(row=3, column=1, columnspan=2, sticky='we', padx=6, pady=6)
        self.e_re_general.insert(0, '5.2')

        lbl_re_red = ctk.CTkLabel(self.fiscal_params_frame, text='RE Red. (%)', 
                                  font=lbl_font, text_color=self.colors.get('text'))
        lbl_re_red.grid(row=3, column=3, sticky='w', padx=6, pady=6)
        self.e_re_reducido = ctk.CTkEntry(self.fiscal_params_frame, **entry_kwargs)
        self.e_re_reducido.grid(row=3, column=4, sticky='we', padx=6, pady=6)
        self.e_re_reducido.insert(0, '1.4')

        lbl_re_super = ctk.CTkLabel(self.fiscal_params_frame, text='RE Superred. (%)', 
                                    font=lbl_font, text_color=self.colors.get('text'))
        lbl_re_super.grid(row=3, column=5, sticky='w', padx=6, pady=6)
        self.e_re_superreducido = ctk.CTkEntry(self.fiscal_params_frame, **entry_kwargs)
        self.e_re_superreducido.grid(row=3, column=6, columnspan=2, sticky='we', padx=6, pady=6)
        self.e_re_superreducido.insert(0, '0.5')

        # Row 0: NOMBRE FISCAL
        lbl_fiscal_name = ctk.CTkLabel(self.fiscal_frame, text='NOMBRE FISCAL', font=lbl_font, text_color=self.colors.get('text'))
        lbl_fiscal_name.grid(row=0, column=0, sticky='w', padx=6, pady=6)
        self.e_fiscal_name = ctk.CTkEntry(self.fiscal_frame, **entry_kwargs)
        self.e_fiscal_name.grid(row=0, column=1, columnspan=7, sticky='we', padx=6, pady=6)
        self.e_fiscal_name.insert(0, '')

        # Row 1: NIF/CIF (cols 1-2) | otros (cols 3-7 unused for now)
        lbl_nif = ctk.CTkLabel(self.fiscal_frame, text='NIF/CIF', font=lbl_font, text_color=self.colors.get('text'))
        lbl_nif.grid(row=1, column=0, sticky='w', padx=6, pady=6)
        self.e_nif = ctk.CTkEntry(self.fiscal_frame, **entry_kwargs)
        self.e_nif.grid(row=1, column=1, columnspan=2, sticky='we', padx=6, pady=6)
        self.e_nif.insert(0, '')

        # Row 2: Direccion fiscal
        lbl_address = ctk.CTkLabel(self.fiscal_frame, text='Dirección fiscal', font=lbl_font, text_color=self.colors.get('text'))
        lbl_address.grid(row=2, column=0, sticky='w', padx=6, pady=6)
        self.e_address = ctk.CTkEntry(self.fiscal_frame, **entry_kwargs)
        self.e_address.grid(row=2, column=1, columnspan=7, sticky='we', padx=6, pady=6)
        self.e_address.insert(0, '')

        # (Logo field removed per spec)

        # Bottom buttons frame
        self.btn_frame = ctk.CTkFrame(self.container, fg_color=bg)
        self.btn_frame.pack(side='bottom', fill='x', padx=12, pady=12)

        try:
            from kool_tpv.utils.config_loader import create_action_button
            btn_save = create_action_button(self.btn_frame, 'guardar', self._on_save)
            if btn_save is None:
                raise Exception('create_action_button returned None')
        except Exception:
            btn_save = ctk.CTkButton(self.btn_frame, text='GUARDAR', command=self._on_save, fg_color=self.colors.get('primary', '#FF9800'), font=get_font('button', module=module_name))

        try:
            btn_save.pack(side='left', padx=8)
        except Exception:
            try:
                btn_save.grid(row=0, column=0)
            except Exception:
                pass

        # Load existing values
        try:
            self._load_data()
        except Exception:
            logging.exception('Error llamando a _load_data en ConfigGeneralUI')

    def get_widget(self):
        return self.container

    def _load_data(self):
        """Cargar valores desde tabla configuracion al iniciar."""
        if not self.db:
            return

        claves = ['shop_name', 'shop_web', 'shop_phone', 'shop_email',
              'fiscal_name', 'fiscal_nif', 'fiscal_address',
              'iva_general', 'iva_reducido', 'iva_superreducido',
              're_activo', 're_general', 're_reducido', 're_superreducido']

        try:
            for clave in claves:
                query = "SELECT valor FROM configuracion WHERE clave = ?"
                row = self.db.fetch_one(query, (clave,))
                valor = row[0] if row else ''

                # Mapear clave a widget Entry correspondiente
                widget_map = {
                    'shop_name': 'e_name',
                    'shop_web': 'e_web',
                    'shop_phone': 'e_phone',
                    'shop_email': 'e_email',
                    'fiscal_name': 'e_fiscal_name',
                    'fiscal_nif': 'e_nif',
                    'fiscal_address': 'e_address',
                    'iva_general': 'e_iva_general',
                    'iva_reducido': 'e_iva_reducido',
                    'iva_superreducido': 'e_iva_superreducido',
                    're_general': 'e_re_general',
                    're_reducido': 'e_re_reducido',
                    're_superreducido': 'e_re_superreducido',
                }

                widget_name = widget_map.get(clave)
                widget = getattr(self, widget_name, None)
                if widget and hasattr(widget, 'delete') and hasattr(widget, 'insert'):
                    widget.delete(0, 'end')
                    widget.insert(0, valor or '')
        except Exception:
            logging.exception('Error cargando datos de configuracion')

        # Checkbox RE activo (manejo especial)
        try:
            query_re = "SELECT valor FROM configuracion WHERE clave = 're_activo'"
            row_re = self.db.fetch_one(query_re)
            re_val = row_re[0] if row_re else '0'
            if hasattr(self, 'chk_re_activo'):
                try:
                    if re_val == '1':
                        self.chk_re_activo.select()
                    else:
                        self.chk_re_activo.deselect()
                except Exception:
                    pass
        except Exception:
            logging.exception('Error cargando checkbox RE')

    def _on_save(self):
        """Guardar todos los campos en tabla configuracion."""
        if not self.db:
            return

        campos = {
            'e_name': 'shop_name',
            'e_web': 'shop_web',
            'e_phone': 'shop_phone',
            'e_email': 'shop_email',
            'e_fiscal_name': 'fiscal_name',
            'e_nif': 'fiscal_nif',
            'e_address': 'fiscal_address',
            'e_iva_general': 'iva_general',
            'e_iva_reducido': 'iva_reducido',
            'e_iva_superreducido': 'iva_superreducido',
            'e_re_general': 're_general',
            'e_re_reducido': 're_reducido',
            'e_re_superreducido': 're_superreducido',
        }

        try:
            conn = self.db.connection
            cur = conn.cursor()
            cur.execute('BEGIN')

            for entry_attr, clave_bd in campos.items():
                widget = getattr(self, entry_attr, None)
                if widget:
                    valor = ''
                    try:
                        valor = widget.get().strip()
                    except Exception:
                        try:
                            valor = str(widget.get())
                        except Exception:
                            valor = ''
                    cur.execute(
                        "INSERT OR REPLACE INTO configuracion (clave, valor) VALUES (?, ?)",
                        (clave_bd, valor)
                    )

            # Guardar checkbox RE activo
            try:
                re_activo = '1' if getattr(self, 'chk_re_activo', None) and self.chk_re_activo.get() else '0'
                cur.execute(
                    "INSERT OR REPLACE INTO configuracion (clave, valor) VALUES (?, ?)",
                    ('re_activo', re_activo)
                )
            except Exception:
                logging.exception('Error guardando re_activo')

            conn.commit()

            from kool_tpv.utils.custom_dialog import show_success
            show_success(self.container, 'Guardado', 'Configuración guardada correctamente')

        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            logging.exception('Error guardando configuracion')
            from kool_tpv.utils.custom_dialog import show_error
            show_error(self.container, 'Error', 'No se pudo guardar')


