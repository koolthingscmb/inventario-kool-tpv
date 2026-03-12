"""UI de Categorías - estética Matrix, grid 8 columnas.

Formulario CRUD para categorias con chips dinámicos.
"""
from typing import Optional
import logging
import tkinter as tk
import customtkinter as ctk

from kool_tpv.base_datos.categoria_service import CategoriaService
from kool_tpv.utils.utils import COLOR_BG_TERMINAL, COLOR_MATRIX, FONT_TERMINAL
from kool_tpv.utils.font_loader import get_font
from kool_tpv.utils.config_loader import create_action_button, load_colors
from kool_tpv.utils.factories.button_factory import ButtonFactory


class CategoriasUI:
    def __init__(self, parent, db=None, module_name: str = 'almacen'):
        self.parent = parent
        self.db = db
        self.module_name = module_name
        try:
            self.colors = load_colors(module_name)
        except Exception:
            self.colors = {'text': COLOR_MATRIX, 'primary': COLOR_MATRIX, 'secondary': COLOR_MATRIX}
        self.service = CategoriaService(db)
        self.container = ctk.CTkFrame(self.parent, fg_color=self.colors.get('background', COLOR_BG_TERMINAL))
        # defaults
        default_entry_kw = {
            'fg_color': self.colors.get('background', COLOR_BG_TERMINAL),
            'text_color': self.colors.get('text', COLOR_MATRIX),
            'border_color': self.colors.get('border', self.colors.get('primary')),
            'height': 32
        }
        # buttons palette
        _buttons_cfg = self.colors.get('buttons', {})
        self._primary_btn = _buttons_cfg.get('primary', {})

        # Header removed — breadcrumb is provided by BaseModuleView

        self.grid_frame = ctk.CTkFrame(self.container, fg_color='transparent')
        self.grid_frame.pack(fill='both', expand=True, padx=12, pady=6)
        for c in range(8):
            self.grid_frame.grid_columnconfigure(c, weight=1)
        # Ensure the row that contains the chips expands to fill available vertical space
        try:
            self.grid_frame.grid_rowconfigure(4, weight=1)
        except Exception:
            pass

        lbl_font = get_font('label', module=self.module_name)

        # Fila 1: ID (2 col) | NOMBRE (6 col)
        ctk.CTkLabel(self.grid_frame, text='ID:', text_color=self.colors['text'], font=lbl_font).grid(row=0, column=0, sticky='w', padx=6, pady=6)
        e_id_kw = default_entry_kw.copy()
        e_id_kw.update({'state': 'disabled', 'text_color': self.colors.get('light', '#666666')})
        self.e_id = ctk.CTkEntry(self.grid_frame, placeholder_text='ID', **e_id_kw)
        self.e_id.grid(row=0, column=1, columnspan=1, sticky='ew', padx=6, pady=6)

        ctk.CTkLabel(self.grid_frame, text='NOMBRE:', text_color=self.colors['text'], font=lbl_font).grid(row=0, column=2, sticky='w', padx=6, pady=6)
        nome_kw = default_entry_kw.copy()
        nome_kw.update({'border_width': 2})
        self.e_nombre = ctk.CTkEntry(self.grid_frame, placeholder_text='Nombre de la categoría', **nome_kw)
        self.e_nombre.grid(row=0, column=3, columnspan=5, sticky='ew', padx=6, pady=6)

        # Fila 2: DESCRIPCION label
        ctk.CTkLabel(self.grid_frame, text='DESCRIPCIÓN:', text_color=self.colors['text'], font=lbl_font).grid(row=1, column=0, columnspan=8, sticky='w', padx=6, pady=6)

        # Fila 3: descripcion textbox (8 col)
        try:
            self.txt_descripcion = ctk.CTkTextbox(
                self.grid_frame,
                width=900,
                height=120,
                fg_color=self.colors.get('background', '#000000'),
                text_color=self.colors.get('text', COLOR_MATRIX),
                border_width=2,
                border_color=self.colors.get('border', self.colors.get('primary'))
            )
            self.txt_descripcion.grid(row=2, column=0, columnspan=8, sticky='nsew', padx=6, pady=6)
        except Exception:
            frame = ctk.CTkFrame(self.grid_frame, fg_color=self.colors.get('background', '#000000'), border_width=2, border_color=self.colors.get('border', self.colors.get('primary')))
            self.txt_descripcion = tk.Text(frame, bg=self.colors.get('background', '#000000'), fg=self.colors.get('text', COLOR_MATRIX))
            self.txt_descripcion.pack(fill='both', expand=True)
            frame.grid(row=2, column=0, columnspan=8, sticky='nsew', padx=6, pady=6)

        # Fila 4: SHOPIFY_TAXONOMY (5 col) | % TESORO (3 col)
        ctk.CTkLabel(self.grid_frame, text='SHOPIFY_TAXONOMY:', text_color=self.colors['text'], font=lbl_font).grid(row=3, column=0, sticky='w', padx=6, pady=6)
        tax_kw = default_entry_kw.copy()
        tax_kw.update({'placeholder_text': 'shopify_taxonomy', 'border_width': 2})
        self.e_taxonomy = ctk.CTkEntry(self.grid_frame, **tax_kw)
        self.e_taxonomy.grid(row=3, column=1, columnspan=5, sticky='ew', padx=6, pady=6)

        ctk.CTkLabel(self.grid_frame, text='% TESORO:', text_color=self.colors['text'], font=lbl_font).grid(row=3, column=6, sticky='w', padx=6, pady=6)
        fide_kw = default_entry_kw.copy()
        fide_kw.update({'placeholder_text': '0.0', 'border_width': 2})
        self.e_fide = ctk.CTkEntry(self.grid_frame, **fide_kw)
        self.e_fide.grid(row=3, column=7, columnspan=1, sticky='ew', padx=6, pady=6)

        # Chips area inside a scrollable frame so many items can be browsed
        self.chips_frame = ctk.CTkScrollableFrame(self.grid_frame, fg_color=self.colors.get('background', COLOR_BG_TERMINAL))
        self.chips_frame.grid(row=4, column=0, columnspan=8, sticky='nsew', padx=6, pady=6)

        # Footer buttons (desde config)
        self.footer = ctk.CTkFrame(self.container, fg_color='transparent')
        self.footer.pack(side='bottom', fill='x', padx=12, pady=12)
        self.btn_nuevo = create_action_button(self.footer, 'nuevo_limpiar', self.clear)
        self.btn_nuevo.pack(side='left', padx=8)
        self.btn_guardar = create_action_button(self.footer, 'guardar', self.save)
        self.btn_guardar.pack(side='left', padx=8)
        self.btn_eliminar = create_action_button(self.footer, 'eliminar', self.delete)
        self.btn_eliminar.pack(side='left', padx=8)

        self.selected_chip = None
        self._load_categorias()

    def get_widget(self):
        return self.container

    def _load_categorias(self):
        try:
            for w in list(self.chips_frame.winfo_children()):
                try:
                    w.destroy()
                except Exception:
                    pass
            cats = self.service.get_all()
            for i, c in enumerate(cats):
                row = i // 6
                col = i % 6
                name = c.get('nombre') or ''
                btn = ButtonFactory.create_button(
                    parent=self.chips_frame,
                    text=name,
                    command=None,
                    style_key="chip_default"
                )
                btn.grid(row=row, column=col, padx=5, pady=5, sticky='w')
                btn.bind('<Button-1>', lambda e, btn=btn: self._select_chip(btn))
                btn.bind('<Double-Button-1>', lambda e, cat=c: self._load_categoria_into_form(cat))
                setattr(btn, '_cat_data', c)
        except Exception:
            logging.exception('Error cargando chips de categorias')

    def _select_chip(self, btn):
        try:
            if self.selected_chip is not None:
                ButtonFactory.apply_style(self.selected_chip, "chip_default")

            self.selected_chip = btn
            ButtonFactory.apply_style(btn, "chip_selected")

        except Exception:
            logging.exception("Error aplicando estilos de selección de chip")

    def _load_categoria_into_form(self, cat: dict):
        try:
            self.e_id.configure(state='normal')
            self.e_id.delete(0, 'end')
            self.e_id.insert(0, str(cat.get('id') or ''))
            self.e_id.configure(state='disabled')
            self.e_nombre.delete(0, 'end')
            self.e_nombre.insert(0, cat.get('nombre') or '')
            try:
                self.txt_descripcion.delete('1.0', 'end')
                self.txt_descripcion.insert('1.0', cat.get('descripcion') or '')
            except Exception:
                try:
                    self.txt_descripcion.delete(0, 'end')
                    self.txt_descripcion.insert(0, cat.get('descripcion') or '')
                except Exception:
                    pass
            try:
                self.e_taxonomy.delete(0, 'end')
                self.e_taxonomy.insert(0, cat.get('shopify_taxonomy') or '')
            except Exception:
                pass
            try:
                self.e_fide.delete(0, 'end')
                self.e_fide.insert(0, str(cat.get('fide_porcentaje') or 0))
            except Exception:
                pass
            try:
                self.e_nombre.focus_set()
            except Exception:
                pass
            try:
                self.btn_guardar.configure(text='ACTUALIZAR')
            except Exception:
                pass
        except Exception:
            logging.exception('Error cargando categoría en formulario')

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
            self.e_taxonomy.delete(0, 'end')
            self.e_fide.delete(0, 'end')
            try:
                self.btn_guardar.configure(text='GUARDAR')
            except Exception:
                pass
        except Exception:
            logging.exception('Error limpiando formulario categorias')

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
            taxonomy = (self.e_taxonomy.get() or '').strip()
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
                ok = self.service.update(id_val, nombre, descripcion, taxonomy, fide)
                if ok:
                    self.clear()
                    self._load_categorias()
            else:
                new_id = self.service.save(nombre, descripcion, taxonomy, fide)
                if new_id:
                    self.clear()
                    self._load_categorias()
        except Exception:
            logging.exception('Error guardando categoría')

    def delete(self):
        try:
            try:
                id_text = self.e_id.get()
                id_val = int(id_text) if id_text else None
            except Exception:
                id_val = None
            if not id_val:
                return
            ok = self.service.delete(id_val)
            if ok:
                self.clear()
                self._load_categorias()
        except Exception:
            logging.exception('Error eliminando categoría')
