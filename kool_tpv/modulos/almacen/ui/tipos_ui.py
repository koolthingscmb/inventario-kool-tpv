"""UI de Tipos - estética Matrix, grid 8 columnas.

Permite listar, crear, editar y borrar tipos.
"""
from typing import Optional
import logging
import tkinter as tk
import customtkinter as ctk

from kool_tpv.base_datos.tipo_service import TipoService
from kool_tpv.utils.utils import COLOR_BG_TERMINAL, COLOR_MATRIX, FONT_TERMINAL, FONT_BUTTONS


class TiposUI:
    def __init__(self, parent, db=None):
        self.parent = parent
        self.db = db
        self.service = TipoService(db)
        self.container = ctk.CTkFrame(self.parent, fg_color=COLOR_BG_TERMINAL)

        # Header removed — breadcrumb is provided by BaseModuleView

        # Grid area
        self.grid_frame = ctk.CTkFrame(self.container, fg_color='transparent')
        self.grid_frame.pack(fill='both', expand=True, padx=12, pady=6)

        for c in range(8):
            self.grid_frame.grid_columnconfigure(c, weight=1)
        # Ensure the row that holds the chips expands to fill remaining vertical space
        try:
            self.grid_frame.grid_rowconfigure(4, weight=1)
        except Exception:
            pass

        lbl_font = FONT_TERMINAL

        # Fila 1: ID | NOMBRE
        ctk.CTkLabel(self.grid_frame, text='ID:', text_color=COLOR_MATRIX, font=lbl_font).grid(row=0, column=0, sticky='w', padx=6, pady=6)
        self.e_id = ctk.CTkEntry(self.grid_frame, placeholder_text='ID', state='disabled', fg_color=COLOR_BG_TERMINAL, text_color='#666666')
        self.e_id.grid(row=0, column=1, columnspan=1, sticky='ew', padx=6, pady=6)

        ctk.CTkLabel(self.grid_frame, text='NOMBRE:', text_color=COLOR_MATRIX, font=lbl_font).grid(row=0, column=2, sticky='w', padx=6, pady=6)
        self.e_nombre = ctk.CTkEntry(self.grid_frame, placeholder_text='Nombre del tipo', fg_color='#000000', text_color='#00FF00', border_width=2, border_color='#00FF00')
        self.e_nombre.grid(row=0, column=3, columnspan=5, sticky='ew', padx=6, pady=6)

        # Fila 2: DESCRIPCION label
        ctk.CTkLabel(self.grid_frame, text='DESCRIPCIÓN:', text_color=COLOR_MATRIX, font=lbl_font).grid(row=1, column=0, columnspan=8, sticky='w', padx=6, pady=6)

        # Fila 3: descripcion textbox (8 col)
        try:
            self.txt_descripcion = ctk.CTkTextbox(self.grid_frame, width=900, height=120, fg_color='#000000', text_color='#00FF00', border_width=2, border_color='#00FF00')
            self.txt_descripcion.grid(row=2, column=0, columnspan=8, sticky='nsew', padx=6, pady=6)
        except Exception:
            frame = ctk.CTkFrame(self.grid_frame, fg_color='#000000', border_width=2, border_color='#00FF00')
            self.txt_descripcion = tk.Text(frame, bg='#000000', fg='#00FF00')
            self.txt_descripcion.pack(fill='both', expand=True)
            frame.grid(row=2, column=0, columnspan=8, sticky='nsew', padx=6, pady=6)

        # Fila 4: % TESORO
        ctk.CTkLabel(self.grid_frame, text='% TESORO:', text_color=COLOR_MATRIX, font=lbl_font).grid(row=3, column=0, sticky='w', padx=6, pady=6)
        self.e_fide = ctk.CTkEntry(self.grid_frame, placeholder_text='0.0', fg_color='#000000', text_color='#00FF00', border_width=2, border_color='#00FF00')
        self.e_fide.grid(row=3, column=1, columnspan=2, sticky='ew', padx=6, pady=6)

        # Chips area (list of tipos) inside a scrollable frame
        self.chips_frame = ctk.CTkScrollableFrame(self.grid_frame, fg_color=COLOR_BG_TERMINAL)
        self.chips_frame.grid(row=4, column=0, columnspan=8, sticky='nsew', padx=6, pady=6)

        # Footer buttons
        self.footer = ctk.CTkFrame(self.container, fg_color='transparent')
        self.footer.pack(side='bottom', fill='x', padx=12, pady=12)
        self.btn_nuevo = ctk.CTkButton(self.footer, text='NUEVO / LIMPIAR', fg_color='#7f8c8d', command=self.clear)
        self.btn_nuevo.pack(side='left', padx=8)
        self.btn_guardar = ctk.CTkButton(self.footer, text='GUARDAR', fg_color='#2ecc71', command=self.save)
        self.btn_guardar.pack(side='left', padx=8)
        self.btn_eliminar = ctk.CTkButton(self.footer, text='ELIMINAR', fg_color='#e74c3c', command=self.delete)
        self.btn_eliminar.pack(side='left', padx=8)

        # load tipos
        self.selected_chip = None
        self._load_tipos()

    def get_widget(self):
        return self.container

    def _load_tipos(self):
        try:
            # clear existing chips
            for w in list(self.chips_frame.winfo_children()):
                try:
                    w.destroy()
                except Exception:
                    pass
            tipos = self.service.get_all_tipos()
            # layout in a 6-column grid to allow wrapping without empty columns
            for i, t in enumerate(tipos):
                row = i // 6
                col = i % 6
                name = t.get('nombre') or ''
                btn = ctk.CTkButton(self.chips_frame, text=name, fg_color='transparent', text_color=COLOR_MATRIX, border_width=2, border_color=COLOR_MATRIX, height=28)
                btn.grid(row=row, column=col, padx=5, pady=5, sticky='w')
                # bind single and double click
                btn.bind('<Button-1>', lambda e, btn=btn: self._select_chip(btn))
                btn.bind('<Double-Button-1>', lambda e, tipo=t: self._load_tipo_into_form(tipo))
                # attach tipo id on widget for reference
                setattr(btn, '_tipo_data', t)
        except Exception:
            logging.exception('Error cargando chips de tipos')

    def _select_chip(self, btn):
        try:
            # visual select: toggle border color brighter
            if self.selected_chip is not None:
                try:
                    self.selected_chip.configure(border_color='#00FF00')
                except Exception:
                    pass
            self.selected_chip = btn
            try:
                btn.configure(border_color='#00FFFF')
            except Exception:
                pass
        except Exception:
            pass

    def _load_tipo_into_form(self, tipo: dict):
        try:
            # tipo is dict with id,nombre,descripcion,fide_porcentaje
            self.e_id.configure(state='normal')
            self.e_id.delete(0, 'end')
            self.e_id.insert(0, str(tipo.get('id') or ''))
            self.e_id.configure(state='disabled')
            self.e_nombre.delete(0, 'end')
            self.e_nombre.insert(0, tipo.get('nombre') or '')
            # descripcion
            try:
                self.txt_descripcion.delete('1.0', 'end')
                self.txt_descripcion.insert('1.0', tipo.get('descripcion') or '')
            except Exception:
                try:
                    self.txt_descripcion.delete(0, 'end')
                    self.txt_descripcion.insert(0, tipo.get('descripcion') or '')
                except Exception:
                    pass
            # fide_porcentaje
            try:
                self.e_fide.delete(0, 'end')
                self.e_fide.insert(0, str(tipo.get('fide_porcentaje') or 0))
            except Exception:
                pass
            # focus name
            try:
                self.e_nombre.focus_set()
            except Exception:
                pass
            # change guardar button text to indicate update
            try:
                self.btn_guardar.configure(text='ACTUALIZAR')
            except Exception:
                pass
        except Exception:
            logging.exception('Error cargando tipo en formulario')

    def clear(self):
        try:
            self.e_id.configure(state='normal')
            self.e_id.delete(0, 'end')
            self.e_id.configure(state='disabled')
            self.e_nombre.delete(0, 'end')
            try:
                self.txt_descripcion.delete('1.0', 'end')
            except Exception:
                try:
                    self.txt_descripcion.delete(0, 'end')
                except Exception:
                    pass
            self.e_fide.delete(0, 'end')
            try:
                self.btn_guardar.configure(text='GUARDAR')
            except Exception:
                pass
        except Exception:
            logging.exception('Error limpiando formulario tipos')

    def save(self):
        try:
            nombre = (self.e_nombre.get() or '').strip()
            if not nombre:
                return
            descripcion = ''
            try:
                descripcion = self.txt_descripcion.get('1.0', 'end-1c').strip()
            except Exception:
                try:
                    descripcion = self.txt_descripcion.get().strip()
                except Exception:
                    descripcion = ''
            fide_raw = (self.e_fide.get() or '').strip()
            try:
                fide = float(fide_raw.replace(',', '.')) if fide_raw else 0.0
            except Exception:
                fide = 0.0

            id_val = None
            try:
                id_text = self.e_id.get()
                id_val = int(id_text) if id_text else None
            except Exception:
                id_val = None

            if id_val:
                ok = self.service.update_tipo(id_val, nombre, descripcion, fide)
                if ok:
                    self.clear()
                    self._load_tipos()
            else:
                new_id = self.service.save_tipo(nombre, descripcion, fide)
                if new_id:
                    self.clear()
                    self._load_tipos()
        except Exception:
            logging.exception('Error guardando tipo')

    def delete(self):
        try:
            try:
                id_text = self.e_id.get()
                id_val = int(id_text) if id_text else None
            except Exception:
                id_val = None
            if not id_val:
                return
            ok = self.service.delete_tipo(id_val)
            if ok:
                self.clear()
                self._load_tipos()
        except Exception:
            logging.exception('Error eliminando tipo')

