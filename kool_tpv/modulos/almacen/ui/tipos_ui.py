"""UI de Tipos - estética Matrix, grid 8 columnas.

Permite listar, crear, editar y borrar tipos.
"""
from typing import Optional
import logging
import tkinter as tk
import customtkinter as ctk

from kool_tpv.base_datos.tipo_service import TipoService
from kool_tpv.utils.utils import COLOR_BG_TERMINAL, COLOR_MATRIX
from kool_tpv.utils.font_loader import get_font
from kool_tpv.utils.config_loader import create_action_button
from kool_tpv.utils.factories.button_factory import ButtonFactory


class TiposUI:
    def __init__(self, parent, db=None, module_name: str = 'almacen'):
        self.parent = parent
        self.db = db
        self.module_name = module_name
        from kool_tpv.utils.config_loader import load_colors
        try:
            self.colors = load_colors(module_name)
        except Exception:
            self.colors = {'text': COLOR_MATRIX, 'primary': COLOR_MATRIX, 'secondary': COLOR_MATRIX}
        self.service = TipoService(db)
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

        # Grid area
        self.grid_frame = ctk.CTkFrame(self.container, fg_color='transparent')
        self.grid_frame.pack(fill='x', padx=12, pady=6)

        for c in range(8):
            self.grid_frame.grid_columnconfigure(c, weight=1)

        lbl_font = get_font('label', module=self.module_name)

        # Fila 1: ID | NOMBRE | COLOR | % TESORO
        ctk.CTkLabel(self.grid_frame, text='ID:', text_color=self.colors['text'], font=lbl_font).grid(row=0, column=0, sticky='w', padx=6, pady=6)
        e_id_kw = default_entry_kw.copy()
        e_id_kw.update({'state': 'disabled', 'text_color': self.colors.get('light', '#666666'), 'width': 60})
        self.e_id = ctk.CTkEntry(self.grid_frame, placeholder_text='ID', **e_id_kw)
        self.e_id.grid(row=0, column=1, sticky='ew', padx=6, pady=6)

        ctk.CTkLabel(self.grid_frame, text='NOMBRE:', text_color=self.colors['text'], font=lbl_font).grid(row=0, column=2, sticky='w', padx=6, pady=6)
        nome_kw = default_entry_kw.copy()
        nome_kw.update({'border_width': 2})
        self.e_nombre = ctk.CTkEntry(self.grid_frame, placeholder_text='Nombre del tipo', **nome_kw)
        self.e_nombre.grid(row=0, column=3, columnspan=1, sticky='ew', padx=6, pady=6)

        ctk.CTkLabel(self.grid_frame, text='COLOR:', text_color=self.colors['text'], font=lbl_font).grid(row=0, column=4, sticky='w', padx=6, pady=6)
        color_frame = ctk.CTkFrame(self.grid_frame, fg_color='transparent')
        color_frame.grid(row=0, column=5, sticky='ew', padx=6, pady=6)
        
        color_kw = default_entry_kw.copy()
        color_kw.update({'placeholder_text': '#RRGGBB', 'border_width': 2, 'width': 80})
        self.e_color = ctk.CTkEntry(color_frame, **color_kw)
        self.e_color.pack(side='left', fill='x', expand=True)
        self.e_color.bind('<KeyRelease>', lambda e: self._update_color_preview())

        self.btn_pick_color = ctk.CTkButton(
            color_frame,
            text="🎨",
            width=32,
            height=32,
            fg_color="transparent",
            border_width=1,
            border_color=self.colors.get('border', self.colors.get('primary')),
            command=self._open_color_picker
        )
        self.btn_pick_color.pack(side='right', padx=(4, 0))

        ctk.CTkLabel(self.grid_frame, text='% TESORO:', text_color=self.colors['text'], font=lbl_font).grid(row=0, column=6, sticky='w', padx=6, pady=6)
        fide_kw = default_entry_kw.copy()
        fide_kw.update({'placeholder_text': '0.0', 'border_width': 2, 'width': 60})
        self.e_fide = ctk.CTkEntry(self.grid_frame, **fide_kw)
        self.e_fide.grid(row=0, column=7, sticky='ew', padx=6, pady=6)

        # Fila 2: ICONO
        ctk.CTkLabel(self.grid_frame, text='ICONO:', text_color=self.colors['text'], font=lbl_font).grid(row=1, column=0, sticky='w', padx=6, pady=6)
        icono_frame = ctk.CTkFrame(self.grid_frame, fg_color='transparent')
        icono_frame.grid(row=1, column=1, columnspan=7, sticky='ew', padx=6, pady=6)

        self.e_icono = ctk.CTkEntry(icono_frame, placeholder_text='Nombre del archivo del icono', **default_entry_kw)
        self.e_icono.pack(side='left', fill='x', expand=True)
        self.e_icono.configure(state='disabled')

        self.btn_subir_icono = ctk.CTkButton(
            icono_frame,
            text="📁 SUBIR ICONO",
            width=140,
            height=32,
            fg_color="transparent",
            border_width=1,
            border_color=self.colors.get('border', self.colors.get('primary')),
            command=self._subir_icono
        )
        self.btn_subir_icono.pack(side='right', padx=(4, 0))

        self.btn_limpiar_icono = ctk.CTkButton(
            icono_frame,
            text="🗑️",
            width=32,
            height=32,
            fg_color="transparent",
            border_width=1,
            border_color=self.colors.get('error', '#FF0000'),
            command=self._limpiar_icono
        )
        self.btn_limpiar_icono.pack(side='right', padx=(4, 0))

        # Fila 2b: COSTE BASE | ORDEN | ACTIVO | GÉNERO | COLOR | TALLA (TODO EN UNA FILA)
        ctk.CTkLabel(self.grid_frame, text='COSTE:', text_color=self.colors['text'], font=lbl_font).grid(row=2, column=0, sticky='w', padx=6, pady=6)
        coste_kw = default_entry_kw.copy()
        coste_kw.update({'placeholder_text': '0.00', 'border_width': 2, 'width': 60})
        self.e_coste = ctk.CTkEntry(self.grid_frame, **coste_kw)
        self.e_coste.grid(row=2, column=1, sticky='ew', padx=6, pady=6)

        ctk.CTkLabel(self.grid_frame, text='ORDEN:', text_color=self.colors['text'], font=lbl_font).grid(row=2, column=2, sticky='w', padx=6, pady=6)
        orden_kw = default_entry_kw.copy()
        orden_kw.update({'placeholder_text': '0', 'border_width': 2, 'width': 40})
        self.e_orden = ctk.CTkEntry(self.grid_frame, **orden_kw)
        self.e_orden.grid(row=2, column=3, sticky='ew', padx=6, pady=6)

        # Checkboxes en los huecos restantes
        self.chk_activo = ctk.CTkCheckBox(self.grid_frame, text='ACTIVO', text_color=self.colors['text'], font=lbl_font, width=20)
        self.chk_activo.grid(row=2, column=4, sticky='w', padx=6, pady=6)

        self.chk_color = ctk.CTkCheckBox(self.grid_frame, text='COLOR', text_color=self.colors['text'], font=lbl_font, width=20)
        self.chk_color.grid(row=2, column=6, sticky='w', padx=6, pady=6)

        self.chk_talla = ctk.CTkCheckBox(self.grid_frame, text='TALLA', text_color=self.colors['text'], font=lbl_font, width=20)
        self.chk_talla.grid(row=2, column=7, sticky='w', padx=6, pady=6)

        # Fila 3: DESCRIPCION
        ctk.CTkLabel(self.grid_frame, text='DESCRIPCIÓN:', text_color=self.colors['text'], font=lbl_font).grid(row=3, column=0, sticky='nw', padx=6, pady=6)
        try:
            self.txt_descripcion = ctk.CTkTextbox(
                self.grid_frame,
                height=40,
                fg_color=self.colors.get('background', '#000000'),
                text_color=self.colors.get('text', COLOR_MATRIX),
                border_width=2,
                border_color=self.colors.get('border', self.colors.get('primary'))
            )
            self.txt_descripcion.grid(row=3, column=1, columnspan=7, sticky='nsew', padx=6, pady=6)
        except Exception:
            frame = ctk.CTkFrame(self.grid_frame, fg_color=self.colors.get('background', '#000000'), border_width=2, border_color=self.colors.get('border', self.colors.get('primary')))
            self.txt_descripcion = tk.Text(frame, bg=self.colors.get('background', '#000000'), fg=self.colors.get('text', COLOR_MATRIX), height=4)
            self.txt_descripcion.pack(fill='both', expand=True)
            frame.grid(row=3, column=1, columnspan=7, sticky='nsew', padx=6, pady=6)

        # Chips area — fuera del grid, frame independiente con pack
        self.chips_frame = ctk.CTkScrollableFrame(self.container, fg_color=self.colors.get('background', COLOR_BG_TERMINAL))
        self.chips_frame.pack(fill='both', expand=True, padx=12, pady=6)

        # Footer buttons (desde config)
        self.footer = ctk.CTkFrame(self.container, fg_color='transparent')
        self.footer.pack(side='bottom', fill='x', padx=12, pady=12)
        self.btn_nuevo = create_action_button(self.footer, 'nuevo_limpiar', self.clear)
        self.btn_nuevo.pack(side='left', padx=8)
        self.btn_guardar = create_action_button(self.footer, 'guardar', self.save)
        self.btn_guardar.pack(side='left', padx=8)
        self.btn_eliminar = create_action_button(self.footer, 'eliminar', self.delete)
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
            # layout in a 8-column grid to match form
            for c in range(8):
                self.chips_frame.grid_columnconfigure(c, weight=1)

            for i, t in enumerate(tipos):
                row = i // 8
                col = i % 8
                name = t.get('nombre') or ''
                btn = ButtonFactory.create_button(
                    parent=self.chips_frame,
                    text=name,
                    command=None,
                    style_key="chip_default"
                )
                btn.grid(row=row, column=col, padx=5, pady=5, sticky='nsew')
                # bind single and double click
                btn.bind('<Button-1>', lambda e, btn=btn: self._select_chip(btn))
                btn.bind('<Double-Button-1>', lambda e, tipo=t: self._load_tipo_into_form(tipo))
                # attach tipo id on widget for reference
                setattr(btn, '_tipo_data', t)
        except Exception:
            logging.exception('Error cargando chips de tipos')

    def _select_chip(self, btn):
        try:
            # Validar que el botón aún existe antes de operar
            if not btn.winfo_exists():
                return

            # Si había chip seleccionado previamente, restaurar estilo default
            if self.selected_chip is not None:
                try:
                    if self.selected_chip.winfo_exists():
                        ButtonFactory.apply_style(self.selected_chip, "chip_default")
                except Exception:
                    pass

            # Marcar nuevo seleccionado
            self.selected_chip = btn

            # Aplicar estilo seleccionado
            ButtonFactory.apply_style(btn, "chip_selected")

        except Exception:
            logging.exception("Error aplicando estilos de selección de chip")

    def _load_tipo_into_form(self, tipo: dict):
        try:
            # tipo is dict with id,nombre,descripcion,fide_porcentaje,color
            self.e_id.configure(state='normal')
            self.e_id.delete(0, 'end')
            self.e_id.insert(0, str(tipo.get('id') or ''))
            self.e_id.configure(state='disabled')
            self.e_nombre.delete(0, 'end')
            self.e_nombre.insert(0, tipo.get('nombre') or '')
            
            self.e_icono.configure(state='normal')
            self.e_icono.delete(0, 'end')
            self.e_icono.insert(0, tipo.get('icono') or '')
            self.e_icono.configure(state='disabled')

            self.e_color.delete(0, 'end')
            self.e_color.insert(0, tipo.get('color') or '')
            self._update_color_preview()
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
            # coste_base
            try:
                self.e_coste.delete(0, 'end')
                self.e_coste.insert(0, str(tipo.get('coste_base') or 0))
            except Exception:
                pass
            # orden
            try:
                self.e_orden.delete(0, 'end')
                self.e_orden.insert(0, str(tipo.get('orden') or 0))
            except Exception:
                pass
            # checkboxes
            self.chk_activo.select() if tipo.get('activo', 1) == 1 else self.chk_activo.deselect()
            self.chk_color.select() if tipo.get('requiere_color', 0) == 1 else self.chk_color.deselect()
            self.chk_talla.select() if tipo.get('requiere_talla', 0) == 1 else self.chk_talla.deselect()
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
            self.e_icono.configure(state='normal')
            self.e_icono.delete(0, 'end')
            self.e_icono.configure(state='disabled')
            self.e_color.delete(0, 'end')
            self._update_color_preview()
            try:
                self.txt_descripcion.delete('1.0', 'end')
            except Exception:
                try:
                    self.txt_descripcion.delete(0, 'end')
                except Exception:
                    pass
            self.e_fide.delete(0, 'end')
            self.e_coste.delete(0, 'end')
            self.e_orden.delete(0, 'end')
            self.chk_activo.select()
            self.chk_color.deselect()
            self.chk_talla.deselect()
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
            color = (self.e_color.get() or '').strip()
            icono = (self.e_icono.get() or '').strip()
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

            coste_raw = (self.e_coste.get() or '').strip()
            try:
                coste_base = float(coste_raw.replace(',', '.')) if coste_raw else 0.0
            except Exception:
                coste_base = 0.0

            orden_raw = (self.e_orden.get() or '').strip()
            try:
                orden = int(orden_raw) if orden_raw else 0
            except Exception:
                orden = 0

            requiere_color = 1 if self.chk_color.get() else 0
            requiere_talla = 1 if self.chk_talla.get() else 0
            activo = 1 if self.chk_activo.get() else 0

            id_val = None
            try:
                id_text = self.e_id.get()
                id_val = int(id_text) if id_text else None
            except Exception:
                id_val = None

            if id_val:
                ok = self.service.update_tipo(id_val, nombre, descripcion, fide, color=color, icono=icono, coste_base=coste_base, requiere_talla=requiere_talla, requiere_color=requiere_color, activo=activo, orden=orden)
                if ok:
                    self.clear()
                    self._load_tipos()
            else:
                new_id = self.service.save_tipo(nombre, descripcion, fide, color=color, icono=icono, coste_base=coste_base, requiere_talla=requiere_talla, requiere_color=requiere_color, activo=activo, orden=orden)
                if new_id:
                    self.clear()
                    self._load_tipos()
        except Exception as e:
            logging.exception('Error guardando tipo')
            # Mostrar Toast warning si es error de UNIQUE constraint
            if 'UNIQUE constraint failed' in str(e):
                from kool_tpv.utils.widgets.notificaciones import ToastWidget
                ToastWidget.show(self.container, 'Ya existe un tipo con ese nombre', tipo='warning')

    def _update_color_preview(self):
        """Actualizar el color del borde del entry para previsualizar el color."""
        try:
            color = self.e_color.get().strip()
            if color and (color.startswith('#') and len(color) in (4, 7)):
                self.e_color.configure(border_color=color)
                self.btn_pick_color.configure(border_color=color)
            else:
                self.e_color.configure(border_color=self.colors.get('border', self.colors.get('primary')))
                self.btn_pick_color.configure(border_color=self.colors.get('border', self.colors.get('primary')))
        except Exception:
            pass

    def _open_color_picker(self):
        """Abrir el diálogo de selección de color."""
        from kool_tpv.utils.dialogs.color_picker import ColorPickerDialog
        
        current = self.e_color.get().strip() or "#333333"
        
        def on_color_selected(color):
            if color:
                self.e_color.delete(0, 'end')
                self.e_color.insert(0, color)
                self._update_color_preview()

        ColorPickerDialog(self.container, initial_color=current, callback=on_color_selected)

    def _subir_icono(self):
        """Abrir diálogo para subir un icono y copiarlo a assets."""
        from tkinter import filedialog
        import os
        import shutil
        from pathlib import Path

        file_types = [('Imágenes', '*.png *.jpg *.jpeg *.svg')]
        file_path = filedialog.askopenfilename(title="Seleccionar icono", filetypes=file_types)
        
        if not file_path:
            return

        try:
            # Asegurar que la carpeta existe
            dest_dir = Path(__file__).resolve().parent.parent.parent / "assets" / "iconos"
            dest_dir.mkdir(parents=True, exist_ok=True)

            # Nombre destino: tipo_id_nombre.ext o solo nombre.ext si es nuevo
            ext = os.path.splitext(file_path)[1].lower()
            nombre_limpio = (self.e_nombre.get() or "nuevo").strip().lower().replace(" ", "_")
            id_val = self.e_id.get() or "temp"
            
            dest_filename = f"tipo_{id_val}_{nombre_limpio}{ext}"
            dest_path = dest_dir / dest_filename

            # Copiar archivo
            shutil.copy2(file_path, dest_path)

            # Actualizar entry
            self.e_icono.configure(state='normal')
            self.e_icono.delete(0, 'end')
            self.e_icono.insert(0, dest_filename)
            self.e_icono.configure(state='disabled')

            from kool_tpv.utils.widgets.notificaciones import ToastWidget
            ToastWidget.show(self.container, f'ICONO GUARDADO COMO: {dest_filename}', tipo='success')

        except Exception:
            logging.exception("Error subiendo icono")
            from kool_tpv.utils.widgets.notificaciones import ToastWidget
            ToastWidget.show(self.container, 'NO SE PUDO SUBIR EL ICONO', tipo='error')

    def _limpiar_icono(self):
        """Limpiar el icono seleccionado."""
        self.e_icono.configure(state='normal')
        self.e_icono.delete(0, 'end')
        self.e_icono.configure(state='disabled')

    def delete(self):
        try:
            try:
                id_text = self.e_id.get()
                id_val = int(id_text) if id_text else None
            except Exception:
                id_val = None
            if not id_val:
                return
            
            ok, msg = self.service.delete_tipo(id_val)
            
            from kool_tpv.utils.widgets.notificaciones import ToastWidget
            if ok:
                ToastWidget.show(self.container, msg, tipo='success')
                self.clear()
                self._load_tipos()
            else:
                ToastWidget.show(self.container, msg, tipo='error')
                
        except Exception:
            logging.exception('Error eliminando tipo')

