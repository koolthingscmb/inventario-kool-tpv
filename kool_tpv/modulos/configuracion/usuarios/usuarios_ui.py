"""UI de gestión de usuarios (clon de ProveedoresUI simplificado)."""
from typing import Optional
import logging
import re
import tkinter as tk
import customtkinter as ctk

from kool_tpv.base_datos.usuario_service import UsuarioService
from kool_tpv.utils.config_loader import create_action_button, load_colors
from kool_tpv.utils.custom_dialog import show_success, show_error
from kool_tpv.utils.font_loader import get_font
from kool_tpv.utils.utils import COLOR_BG_TERMINAL


class UsuariosUI:
    def __init__(self, parent, db=None, owner=None, module_name: str = 'config'):
        self.parent = parent
        self.db = db
        self.owner = owner
        self.module_name = module_name
        try:
            self.colors = load_colors(module_name)
        except Exception:
            self.colors = {'text': '#FFFFFF', 'background': COLOR_BG_TERMINAL, 'buttons': {}}

        # primary button style for chips and action buttons
        try:
            self._primary_btn = self.colors.get('buttons', {}).get('primary', {})
        except Exception:
            self._primary_btn = {}

        self.service = UsuarioService(db)
        self.container = ctk.CTkFrame(self.parent, fg_color=self.colors.get('background', COLOR_BG_TERMINAL))

        # grid
        self.grid_frame = ctk.CTkFrame(self.container, fg_color='transparent')
        self.grid_frame.pack(fill='both', expand=True, padx=12, pady=6)
        for c in range(8):
            self.grid_frame.grid_columnconfigure(c, weight=1)

        # use dynamic font loader for labels
        entry_kw = {
            'fg_color': self.colors.get('background', COLOR_BG_TERMINAL),
            'text_color': self.colors.get('text', '#FFFFFF'),
            'border_width': 2,
            'height': 32
        }

        # Row 0: ID | FECHA ALTA | NOMBRE
        ctk.CTkLabel(self.grid_frame, text='ID:', text_color=self.colors.get('text'), font=get_font('label', module='config')).grid(row=0, column=0, sticky='w', padx=6, pady=6)
        self.e_id = ctk.CTkEntry(self.grid_frame, placeholder_text='ID', state='disabled', **entry_kw)
        self.e_id.grid(row=0, column=1, sticky='ew', padx=6, pady=6)

        ctk.CTkLabel(self.grid_frame, text='FECHA ALTA:', text_color=self.colors.get('text'), font=get_font('label', module='config')).grid(row=0, column=2, sticky='w', padx=6, pady=6)
        self.e_fecha = ctk.CTkEntry(self.grid_frame, placeholder_text='Fecha alta', state='disabled', **entry_kw)
        self.e_fecha.grid(row=0, column=3, sticky='ew', padx=6, pady=6)

        ctk.CTkLabel(self.grid_frame, text='NOMBRE:', text_color=self.colors.get('text'), font=get_font('label', module='config')).grid(row=0, column=4, sticky='w', padx=6, pady=6)
        self.e_nombre = ctk.CTkEntry(self.grid_frame, placeholder_text='Nombre', **entry_kw)
        self.e_nombre.grid(row=0, column=5, columnspan=3, sticky='ew', padx=6, pady=6)

        # Row1: TELEFONO | EMAIL
        ctk.CTkLabel(self.grid_frame, text='TELÉFONO:', text_color=self.colors.get('text'), font=get_font('label', module='config')).grid(row=1, column=0, sticky='w', padx=6, pady=6)
        self.e_telefono = ctk.CTkEntry(self.grid_frame, placeholder_text='Teléfono', **entry_kw)
        self.e_telefono.grid(row=1, column=1, columnspan=3, sticky='ew', padx=6, pady=6)

        ctk.CTkLabel(self.grid_frame, text='EMAIL:', text_color=self.colors.get('text'), font=get_font('label', module='config')).grid(row=1, column=4, sticky='w', padx=6, pady=6)
        self.e_email = ctk.CTkEntry(self.grid_frame, placeholder_text='email@ejemplo.com', **entry_kw)
        self.e_email.grid(row=1, column=5, columnspan=3, sticky='ew', padx=6, pady=6)

        # Row2: PASSWORD | ROL
        ctk.CTkLabel(self.grid_frame, text='PASSWORD:', text_color=self.colors.get('text'), font=get_font('label', module='config')).grid(row=2, column=0, sticky='w', padx=6, pady=6)
        self.e_password = ctk.CTkEntry(self.grid_frame, placeholder_text='••••••••', show='*', **entry_kw)
        self.e_password.grid(row=2, column=1, columnspan=4, sticky='ew', padx=6, pady=6)

        ctk.CTkLabel(self.grid_frame, text='ROL:', text_color=self.colors.get('text'), font=get_font('label', module='config')).grid(row=2, column=5, sticky='w', padx=6, pady=6)
        self.cb_rol = ctk.CTkComboBox(self.grid_frame, values=['Cajero', 'Admin'])
        self.cb_rol.grid(row=2, column=6, columnspan=2, sticky='ew', padx=6, pady=6)

        # Row3: Label PERMISOS:
        ctk.CTkLabel(self.grid_frame, text='PERMISOS:', text_color=self.colors.get('text'), font=get_font('label', module='config')).grid(row=3, column=0, sticky='w', padx=6, pady=6)

        # Row4: Switches
        self.sw_cierre = ctk.CTkSwitch(self.grid_frame, text='Cierre caja')
        self.sw_cierre.grid(row=4, column=0, columnspan=2, padx=6, pady=6, sticky='w')
        self.sw_descuento = ctk.CTkSwitch(self.grid_frame, text='Descuento')
        self.sw_descuento.grid(row=4, column=2, columnspan=2, padx=6, pady=6, sticky='w')
        self.sw_devolucion = ctk.CTkSwitch(self.grid_frame, text='Devolución')
        self.sw_devolucion.grid(row=4, column=4, columnspan=2, padx=6, pady=6, sticky='w')
        self.sw_tickets = ctk.CTkSwitch(self.grid_frame, text='Ver Tickets')
        self.sw_tickets.grid(row=4, column=6, columnspan=2, padx=6, pady=6, sticky='w')

        # Row5: Chips area
        self.grid_frame.grid_rowconfigure(5, weight=1)
        self.chips_frame = ctk.CTkScrollableFrame(self.grid_frame, fg_color=self.colors.get('background'))
        self.chips_frame.grid(row=5, column=0, columnspan=8, sticky='nsew', padx=6, pady=6)

        # Footer buttons
        self.footer = ctk.CTkFrame(self.container, fg_color='transparent')
        self.footer.pack(side='bottom', fill='x', padx=12, pady=12)

        self.btn_nuevo = create_action_button(self.footer, 'nuevo_limpiar', self.clear)
        self.btn_nuevo.pack(side='left', padx=8)

        self.btn_guardar = create_action_button(self.footer, 'guardar', self.save)
        self.btn_guardar.pack(side='left', padx=8)

        self.btn_eliminar = create_action_button(self.footer, 'eliminar', self.delete)
        self.btn_eliminar.pack(side='left', padx=8)

        # state
        self.selected_chip = None
        self._load_usuarios()

    def get_widget(self):
        return self.container

    def _load_usuarios(self):
        try:
            for w in list(self.chips_frame.winfo_children()):
                try:
                    w.destroy()
                except Exception:
                    pass
            usuarios = self.service.get_all_usuarios()
            if not usuarios:
                try:
                    ctk.CTkLabel(self.chips_frame, text='No hay usuarios', text_color=self.colors.get('text')).grid(row=0, column=0, padx=6, pady=6)
                except Exception:
                    pass
                return

            for i, u in enumerate(usuarios):
                row = i // 6
                col = i % 6
                name = u.get('nombre') or ''
                btn = ctk.CTkButton(
                    self.chips_frame,
                    text=name,
                    fg_color=self._primary_btn.get('bg', 'transparent'),
                    text_color=self._primary_btn.get('text', self.colors.get('text', '#FFFFFF')),
                    border_width=2,
                    border_color=self._primary_btn.get('border', self.colors.get('border', self.colors.get('primary'))),
                    hover_color=self._primary_btn.get('hover', self.colors.get('secondary')),
                    height=28
                )
                btn.grid(row=row, column=col, padx=5, pady=5, sticky='w')
                btn.bind('<Button-1>', lambda e, btn=btn: self._select_chip(btn))
                btn.bind('<Double-Button-1>', lambda e, usr=u: self._load_usuario_into_form(usr))
                setattr(btn, '_usr_data', u)
        except Exception:
            logging.exception('Error cargando chips de usuarios')

    def _select_chip(self, btn):
        try:
            if getattr(self, 'selected_chip', None) is not None:
                try:
                    self.selected_chip.configure(border_color=self._primary_btn.get('border', self.colors.get('border')))
                except Exception:
                    pass
            self.selected_chip = btn
            try:
                btn.configure(border_color=self._primary_btn.get('hover', self.colors.get('secondary')))
            except Exception:
                pass
            # Also load the usuario data attached to the chip when selected
            try:
                usr = getattr(btn, '_usr_data', None)
                if usr:
                    self._load_usuario_into_form(usr)
            except Exception:
                pass
        except Exception:
            pass

    def _load_usuario_into_form(self, usr: dict):
        try:
            self.e_id.configure(state='normal')
            self.e_id.delete(0, 'end')
            self.e_id.insert(0, str(usr.get('id') or ''))
            self.e_id.configure(state='disabled')

            self.e_fecha.configure(state='normal')
            self.e_fecha.delete(0, 'end')
            self.e_fecha.insert(0, str(usr.get('created_at') or ''))
            self.e_fecha.configure(state='disabled')

            self.e_nombre.delete(0, 'end')
            self.e_nombre.insert(0, usr.get('nombre') or '')

            self.e_telefono.delete(0, 'end')
            self.e_telefono.insert(0, usr.get('telefono') or '')

            self.e_email.delete(0, 'end')
            self.e_email.insert(0, usr.get('email') or '')

            # Always clear password field when loading
            self.e_password.delete(0, 'end')

            # Normalize role values to match combobox entries
            rol = (usr.get('rol') or 'Cajero')
            try:
                rlow = str(rol).strip().lower()
                if rlow == 'admin' or rlow == 'administrator':
                    self.cb_rol.set('Admin')
                else:
                    # default to Cajero for any non-admin
                    self.cb_rol.set('Cajero')
            except Exception:
                try:
                    self.cb_rol.set('Cajero')
                except Exception:
                    pass

            # Robustly set switches even if DB returns strings like '0'/'1'
            def _set_switch(sw_widget, value):
                try:
                    v = int(value)
                except Exception:
                    try:
                        sval = str(value).strip().lower()
                        v = 1 if sval in ('1', 'true', 't', 'yes', 'y') else 0
                    except Exception:
                        v = 0
                try:
                    if v:
                        sw_widget.select()
                    else:
                        sw_widget.deselect()
                except Exception:
                    pass

            _set_switch(self.sw_cierre, usr.get('permiso_cierre'))
            _set_switch(self.sw_descuento, usr.get('permiso_descuento'))
            _set_switch(self.sw_devolucion, usr.get('permiso_devolucion'))
            _set_switch(self.sw_tickets, usr.get('permiso_tickets'))

            self.btn_guardar.configure(text='ACTUALIZAR')
        except Exception:
            logging.exception('Error cargando usuario en formulario')

    def clear(self):
        try:
            self.e_id.configure(state='normal')
            self.e_id.delete(0, 'end')
            self.e_id.configure(state='disabled')

            self.e_fecha.configure(state='normal')
            self.e_fecha.delete(0, 'end')
            self.e_fecha.configure(state='disabled')

            self.e_nombre.delete(0, 'end')
            self.e_telefono.delete(0, 'end')
            self.e_email.delete(0, 'end')
            self.e_password.delete(0, 'end')
            try:
                self.cb_rol.set('Cajero')
            except Exception:
                pass
            try:
                self.sw_cierre.deselect()
            except Exception:
                pass
            try:
                self.sw_descuento.deselect()
            except Exception:
                pass
            try:
                self.sw_devolucion.deselect()
            except Exception:
                pass
            try:
                self.sw_tickets.deselect()
            except Exception:
                pass

            self.btn_guardar.configure(text='GUARDAR')
        except Exception:
            logging.exception('Error limpiando formulario usuarios')

    def _validate_email(self, email: str) -> bool:
        if not email:
            return True
        pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
        return re.match(pattern, email) is not None

    def save(self):
        try:
            nombre = self.e_nombre.get().strip()
            if not nombre:
                logging.warning('UsuariosUI.save: nombre vacío')
                return

            email = self.e_email.get().strip()
            if not self._validate_email(email):
                logging.warning('UsuariosUI.save: email inválido')
                return

            telefono = self.e_telefono.get().strip()
            password = self.e_password.get()
            rol = (self.cb_rol.get() or 'Cajero')

            permiso_cierre = 1 if self.sw_cierre.get() else 0
            permiso_descuento = 1 if self.sw_descuento.get() else 0
            permiso_devolucion = 1 if self.sw_devolucion.get() else 0
            permiso_tickets = 1 if self.sw_tickets.get() else 0

            id_val = None
            try:
                id_text = self.e_id.get()
                id_val = int(id_text) if id_text else None
            except Exception:
                id_val = None

            if id_val:
                # Update: if password empty -> do not update password
                data = {
                    'nombre': nombre,
                    'email': email,
                    'telefono': telefono,
                    'rol': rol,
                    'permiso_cierre': permiso_cierre,
                    'permiso_descuento': permiso_descuento,
                    'permiso_devolucion': permiso_devolucion,
                    'permiso_tickets': permiso_tickets,
                }
                if password:
                    data['password'] = password
                ok = self.service.update_usuario(id_val, **data)
            else:
                # New user: password mandatory
                if not password:
                    parent = None
                    try:
                        parent = self.container.winfo_toplevel()
                    except Exception:
                        parent = self.parent
                    try:
                        show_error(parent, 'ERROR', 'Campo Password obligado')
                    except Exception:
                        logging.warning('UsuariosUI.save: password obligatorio para nuevo usuario')
                    return
                ok = self.service.save_usuario(nombre, email=email, telefono=telefono, password=password, rol=rol,
                                               permiso_cierre=permiso_cierre, permiso_descuento=permiso_descuento,
                                               permiso_devolucion=permiso_devolucion, permiso_tickets=permiso_tickets)

            if ok:
                # Mostrar diálogo de éxito según operación
                parent = None
                try:
                    parent = self.container.winfo_toplevel()
                except Exception:
                    parent = self.parent

                if id_val:
                    try:
                        show_success(parent, 'USUARIO ACTUALIZADO', f'Usuario {nombre} actualizado correctamente')
                    except Exception:
                        pass
                else:
                    try:
                        show_success(parent, 'USUARIO CREADO', f'Usuario {nombre} creado correctamente')
                    except Exception:
                        pass

                self.clear()
                self._load_usuarios()
        except Exception:
            logging.exception('Error guardando usuario')

    def delete(self):
        try:
            id_text = self.e_id.get()
            id_val = int(id_text) if id_text else None
            if not id_val:
                return
            ok = self.service.delete_usuario(id_val)
            if ok:
                try:
                    parent = self.container.winfo_toplevel()
                except Exception:
                    parent = self.parent
                try:
                    show_success(parent, 'USUARIO ELIMINADO', f'Usuario eliminado correctamente')
                except Exception:
                    pass
                self.clear()
                self._load_usuarios()
        except Exception:
            logging.exception('Error eliminando usuario')
