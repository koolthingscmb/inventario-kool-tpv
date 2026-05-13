"""
Interfaz de configuración de impresora para CONFIG -> IMPRESIÓN -> IMPRESORA
"""
import logging
import tkinter as tk
import customtkinter as ctk
from pathlib import Path
from tkinter import filedialog
from PIL import Image, ImageTk
from datetime import datetime

from kool_tpv.utils.utils import COLOR_BG_TERMINAL, COLOR_MATRIX, FONT_TERMINAL
from kool_tpv.utils.config_loader import load_colors, create_action_button
from kool_tpv.utils.factories.button_factory import ButtonFactory
from kool_tpv.utils.font_loader import get_font
from kool_tpv.base_datos.configuracion_repository import ConfiguracionRepository


class ImpresoraUI:
    def __init__(self, parent, db, module_name='config'):
        self.parent = parent
        self.db = db
        self.config_repo = ConfiguracionRepository(db)
        try:
            self.colors = load_colors(module_name)
        except Exception:
            logging.exception('Error cargando colores en ImpresoraUI')
            self.colors = {}

        bg = self.colors.get('background', COLOR_BG_TERMINAL)

        # Container principal
        self.container = ctk.CTkFrame(self.parent, fg_color=bg)

        # Frame impresora
        self.impresora_frame = ctk.CTkFrame(self.container, fg_color=self.colors.get('background', bg))
        self.impresora_frame.pack(fill='both', expand=True, padx=12, pady=8)

        # Configurar 8 columnas uniformes
        for c in range(8):
            try:
                self.impresora_frame.grid_columnconfigure(c, weight=1, uniform='col')
            except Exception:
                pass

        # Entry / combo kwargs base
        combo_kwargs = {
            "fg_color": self.colors.get('background'),
            "text_color": self.colors.get('text'),
            "border_width": 2,
            "border_color": self.colors.get('border', self.colors.get('primary')),
            "corner_radius": 4,
            "font": get_font('entry', module=module_name)
        }

        _buttons_cfg = self.colors.get('buttons', {})
        _secondary_btn = _buttons_cfg.get('secondary', {})

        # Fila 0: Selector impresora
        lbl_imp = ctk.CTkLabel(self.impresora_frame, text='Impresora', text_color=self.colors.get('text', COLOR_MATRIX), font=get_font('label', module=module_name))
        lbl_imp.grid(row=0, column=0, sticky='w', padx=6, pady=6)

        self.cb_impresora = ctk.CTkComboBox(self.impresora_frame, values=[], **combo_kwargs)
        self.cb_impresora.grid(row=0, column=1, columnspan=7, sticky='we', padx=6, pady=6)

        # Fila 1: Ancho papel (radio buttons)
        lbl_width = ctk.CTkLabel(self.impresora_frame, text='Ancho papel', text_color=self.colors.get('text', COLOR_MATRIX), font=get_font('label', module=module_name))
        lbl_width.grid(row=1, column=0, sticky='w', padx=6, pady=6)

        radio_frame = ctk.CTkFrame(self.impresora_frame, fg_color='transparent')
        radio_frame.grid(row=1, column=1, columnspan=7, sticky='w', padx=6, pady=6)

        self.paper_width_var = tk.StringVar(value='80')

        radio_58 = ctk.CTkRadioButton(
            radio_frame,
            text='58mm',
            variable=self.paper_width_var,
            value='58',
            fg_color=self.colors.get('primary', '#FF9800'),
            font=get_font('label', module=module_name)
        )
        radio_58.pack(side='left', padx=12)

        radio_80 = ctk.CTkRadioButton(
            radio_frame,
            text='80mm',
            variable=self.paper_width_var,
            value='80',
            fg_color=self.colors.get('primary', '#FF9800'),
            font=get_font('label', module=module_name)
        )
        radio_80.pack(side='left', padx=12)

        # Botón TEST inline (pequeño, estilo secondary)
        try:
            btn_test_inline = ButtonFactory.create_button(
                parent=radio_frame,
                text='TEST',
                command=self._test_impresion,
                style_key='mini_action'
            )
            btn_test_inline.pack(side='left', padx=(24, 0))
        except Exception:
            pass

        # --- Fila 2: Selector y preview de logo ---
        try:
            lbl_logo = ctk.CTkLabel(
                self.impresora_frame,
                text='Logo en ticket',
                text_color=self.colors.get('text', COLOR_MATRIX),
                font=get_font('label', module=module_name)
            )
            lbl_logo.grid(row=2, column=0, sticky='w', padx=6, pady=6)

            self.switch_logo = ctk.CTkSwitch(
                self.impresora_frame,
                text='Activar',
                fg_color=self.colors.get('primary', '#FF9800'),
                font=get_font('label', module=module_name)
            )
            self.switch_logo.grid(row=2, column=1, sticky='w', padx=6, pady=6)

            # Botón seleccionar logo
            btn_seleccionar = ButtonFactory.create_button(
                parent=self.impresora_frame,
                text='SELECCIONAR LOGO',
                command=self._seleccionar_logo,
                style_key='mini_action'
            )
            btn_seleccionar.grid(row=2, column=2, columnspan=2, sticky='w', padx=6, pady=6)

            # Fila 3: Preview del logo
            self.logo_preview_label = ctk.CTkLabel(
                self.impresora_frame,
                text='Sin logo',
                text_color=self.colors.get('text', COLOR_MATRIX),
                font=get_font('label', module=module_name),
                width=200,
                height=150,
                fg_color=self.colors.get('bg_dark', '#0d0d0d'),
                corner_radius=8
            )
            self.logo_preview_label.grid(row=3, column=0, columnspan=4, sticky='w', padx=6, pady=12)

            # Variable interna para filename
            self.logo_filename = None
        except Exception:
            logging.exception('Error creando controles de logo en ImpresoraUI')
        # --- Fila 4/5: QR en ticket (activar + URL) ---
        try:
            lbl_qr = ctk.CTkLabel(
                self.impresora_frame,
                text='QR en ticket',
                text_color=self.colors.get('text', COLOR_MATRIX),
                font=get_font('label', module=module_name)
            )
            lbl_qr.grid(row=4, column=0, sticky='w', padx=6, pady=6)

            self.switch_qr = ctk.CTkSwitch(
                self.impresora_frame,
                text='Activar',
                fg_color=self.colors.get('primary', '#FF9800'),
                font=get_font('label', module=module_name)
            )
            self.switch_qr.grid(row=4, column=1, sticky='w', padx=6, pady=6)

            lbl_qr_url = ctk.CTkLabel(
                self.impresora_frame,
                text='URL QR:',
                text_color=self.colors.get('text', COLOR_MATRIX),
                font=get_font('label', module=module_name)
            )
            lbl_qr_url.grid(row=5, column=0, sticky='w', padx=6, pady=6)

            self.entry_qr_url = ctk.CTkEntry(
                self.impresora_frame,
                placeholder_text='https://tutienda.com',
                **combo_kwargs
            )
            self.entry_qr_url.grid(row=5, column=1, columnspan=7, sticky='we', padx=6, pady=6)
        except Exception:
            logging.exception('Error creando controles de QR en ImpresoraUI')

        # Botones inferiores
        self.btn_frame = ctk.CTkFrame(self.container, fg_color=self.colors.get('background', bg))
        self.btn_frame.pack(side='bottom', fill='x', padx=12, pady=12)

        # Botón Guardar (usar create_action_button)
        btn_save = create_action_button(self.btn_frame, 'guardar', self._on_save)
        btn_save.pack(side='left', padx=8)

        # (Test moved inline next to radios)

        # Cargar impresoras y datos guardados
        try:
            self._cargar_impresoras()
        except Exception:
            logging.exception('Error cargando lista de impresoras')

        try:
            self._load_data()
        except Exception:
            logging.exception('Error cargando datos iniciales en ImpresoraUI')

    def get_widget(self):
        return self.container

    def _cargar_impresoras(self):
        """Obtener lista de impresoras instaladas en el sistema."""
        try:
            impresoras = []

            # Windows
            try:
                import win32print
                impresoras = [printer[2] for printer in win32print.EnumPrinters(2)]
            except Exception:
                # Mac/Linux: usar lpstat
                try:
                    import subprocess
                    result = subprocess.run(['lpstat', '-p'], capture_output=True, text=True)
                    lines = result.stdout.strip().split('\n') if result.stdout else []
                    for line in lines:
                        if line.startswith('printer'):
                            parts = line.split()
                            if len(parts) > 1:
                                impresoras.append(parts[1])
                except Exception:
                    logging.exception('Error obteniendo impresoras en Mac/Linux')

            if not impresoras:
                impresoras = ['Sin impresoras detectadas']

            try:
                self.cb_impresora.configure(values=impresoras)
            except Exception:
                try:
                    self.cb_impresora.set(impresoras[0])
                except Exception:
                    pass

        except Exception:
            logging.exception('Error cargando impresoras del sistema')
            try:
                self.cb_impresora.configure(values=['Error cargando impresoras'])
            except Exception:
                pass

    def _load_data(self):
        """Cargar valores desde tabla configuracion."""
        if not self.db:
            return

        try:
            # Cargar printer_name
            row = self.db.fetch_one("SELECT valor FROM configuracion WHERE clave = 'printer_name'")
            if row and row[0]:
                try:
                    self.cb_impresora.set(row[0])
                except Exception:
                    try:
                        self.cb_impresora.configure(values=[row[0]])
                    except Exception:
                        pass

            # Cargar printer_width
            row = self.db.fetch_one("SELECT valor FROM configuracion WHERE clave = 'printer_width'")
            if row and row[0]:
                try:
                    self.paper_width_var.set(row[0])
                except Exception:
                    pass

            # Cargar logo_enabled
            try:
                row = self.db.fetch_one("SELECT valor FROM configuracion WHERE clave = 'logo_enabled'")
                if row and row[0] == '1':
                    try:
                        self.switch_logo.select()
                    except Exception:
                        pass
                else:
                    try:
                        self.switch_logo.deselect()
                    except Exception:
                        pass
            except Exception:
                pass

            # Cargar logo_filename y mostrar preview
            try:
                row = self.db.fetch_one("SELECT valor FROM configuracion WHERE clave = 'logo_filename'")
                if row and row[0]:
                    self.logo_filename = row[0]
                    base_dir = Path(__file__).resolve().parents[3]
                    logo_path = base_dir / 'assets' / 'logo' / self.logo_filename
                    if logo_path.exists():
                        try:
                            self._mostrar_preview(logo_path)
                        except Exception:
                            pass
            except Exception:
                pass

            # Cargar qr_enabled
            try:
                row = self.db.fetch_one("SELECT valor FROM configuracion WHERE clave = 'qr_enabled'")
                if row and row[0] == '1':
                    try:
                        self.switch_qr.select()
                    except Exception:
                        pass
                else:
                    try:
                        self.switch_qr.deselect()
                    except Exception:
                        pass
            except Exception:
                pass

            # Cargar qr_url
            try:
                row = self.db.fetch_one("SELECT valor FROM configuracion WHERE clave = 'qr_url'")
                if row and row[0]:
                    try:
                        self.entry_qr_url.delete(0, 'end')
                        self.entry_qr_url.insert(0, row[0])
                    except Exception:
                        pass
            except Exception:
                pass
        except Exception:
            logging.exception('Error cargando datos impresora')

    def _on_save(self):
        """Guardar configuración en BD."""
        if not self.db:
            return

        try:
            cambios = {}

            # printer_name
            cambios['printer_name'] = self.cb_impresora.get()

            # printer_width
            cambios['printer_width'] = self.paper_width_var.get()

            # logo_enabled
            try:
                cambios['logo_enabled'] = '1' if self.switch_logo.get() else '0'
            except Exception:
                cambios['logo_enabled'] = '0'

            # logo_filename (solo si tiene valor)
            try:
                if self.logo_filename:
                    cambios['logo_filename'] = self.logo_filename
            except Exception:
                pass

            # qr_enabled
            try:
                cambios['qr_enabled'] = '1' if self.switch_qr.get() else '0'
            except Exception:
                cambios['qr_enabled'] = '0'

            # qr_url (solo si tiene valor)
            try:
                qr_url = self.entry_qr_url.get().strip()
                if qr_url:
                    cambios['qr_url'] = qr_url
            except Exception:
                pass

            self.config_repo.guardar_multiples(cambios)

            from kool_tpv.utils.custom_dialog import show_success
            show_success(self.container, 'Guardado', 'Configuración de impresora guardada')

        except Exception:
            logging.exception('Error guardando configuración impresora')
            from kool_tpv.utils.custom_dialog import show_error
            show_error(self.container, 'Error', 'No se pudo guardar')

    def _test_impresion(self):
        """Imprimir ticket de prueba."""
        try:
            printer_name = self.cb_impresora.get()

            if not printer_name or printer_name == 'Sin impresoras detectadas':
                from kool_tpv.utils.custom_dialog import show_warning
                show_warning(self.container, 'Test', 'Selecciona una impresora primero')
                return

            # Generar ticket test
            ticket_text = f"""
            ================================
                  TEST - KOOL TPV
            ================================
            Fecha: {self._get_fecha_actual()}
            Impresora: {printer_name}
            Ancho: {self.paper_width_var.get()}mm
            --------------------------------
            Impresora funcionando OK
            ================================
            """

            # Intentar imprimir
            try:
                # Windows
                import win32print
                import win32ui

                hprinter = win32print.OpenPrinter(printer_name)
                try:
                    hdc = win32ui.CreateDC()
                    hdc.CreatePrinterDC(printer_name)
                    hdc.StartDoc('Test KOOL TPV')
                    hdc.StartPage()
                    hdc.TextOut(100, 100, ticket_text)
                    hdc.EndPage()
                    hdc.EndDoc()
                finally:
                    win32print.ClosePrinter(hprinter)

                from kool_tpv.utils.custom_dialog import show_success
                show_success(self.container, 'Test', 'Ticket de prueba enviado')

            except Exception:
                # Fallback: mostrar en consola
                logging.info(f'TEST IMPRESIÓN:\n{ticket_text}')
                from kool_tpv.utils.custom_dialog import show_warning
                show_warning(self.container, 'Test', 'Test enviado a logs (win32print no disponible)')

        except Exception:
            logging.exception('Error en test de impresión')
            from kool_tpv.utils.custom_dialog import show_error
            show_error(self.container, 'Error', 'Error en test de impresión')

    def _seleccionar_logo(self):
        """Abrir diálogo, copiar imagen a assets/logo/ y mostrar preview."""
        try:
            filepath = filedialog.askopenfilename(
                title='Seleccionar logo',
                filetypes=[
                    ('Imágenes PNG', '*.png'),
                    ('Todas las imágenes', '*.png *.jpg *.jpeg')
                ]
            )

            if not filepath:
                return

            # Validar que sea imagen
            try:
                img_test = Image.open(filepath)
                img_test.close()
            except Exception:
                from kool_tpv.utils.custom_dialog import show_error
                show_error(self.container, 'Error', 'Archivo no válido')
                return

            # Crear carpeta assets/logo si no existe
            base_dir = Path(__file__).resolve().parents[3]
            logo_dir = base_dir / 'assets' / 'logo'
            logo_dir.mkdir(parents=True, exist_ok=True)

            # Copiar archivo con nombre fijo
            dest_path = logo_dir / 'logo.png'

            import shutil
            shutil.copy2(filepath, dest_path)

            # Guardar filename internamente
            self.logo_filename = 'logo.png'

            # Mostrar preview
            self._mostrar_preview(dest_path)

            from kool_tpv.utils.custom_dialog import show_success
            show_success(self.container, 'Logo', 'Logo cargado correctamente')

        except Exception:
            logging.exception('Error seleccionando logo')
            from kool_tpv.utils.custom_dialog import show_error
            show_error(self.container, 'Error', 'No se pudo cargar el logo')

    def _mostrar_preview(self, image_path):
        """Mostrar preview del logo en el label."""
        try:
            img = Image.open(image_path)

            # Redimensionar manteniendo proporción (máx 180x120)
            img.thumbnail((180, 120), Image.LANCZOS)

            # Convertir a PhotoImage
            photo = ImageTk.PhotoImage(img)

            # Actualizar label
            self.logo_preview_label.configure(image=photo, text='')
            self.logo_preview_label.image = photo  # Mantener referencia

        except Exception:
            logging.exception('Error mostrando preview logo')

    def _get_fecha_actual(self):
        """Obtener fecha/hora actual formateada."""
        return datetime.now().strftime('%d/%m/%Y %H:%M')
