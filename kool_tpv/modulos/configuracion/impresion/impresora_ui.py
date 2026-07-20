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
from kool_tpv.base_datos.configuracion_service import ConfiguracionService
from kool_tpv.utils.widgets.notificaciones import ToastWidget


class ImpresoraUI:
    def __init__(self, parent, db, module_name='config'):
        self.parent = parent
        self.db = db
        self.config_repo = ConfiguracionRepository(db)
        self.config_service = ConfiguracionService(db)
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

        # --- Fila 2: Modo impresora física (ESC/POS) ---
        try:
            lbl_modo = ctk.CTkLabel(
                self.impresora_frame,
                text='Imprimir tickets',
                text_color=self.colors.get('text', COLOR_MATRIX),
                font=get_font('label', module=module_name)
            )
            lbl_modo.grid(row=2, column=0, sticky='w', padx=6, pady=6)

            modo_frame = ctk.CTkFrame(self.impresora_frame, fg_color='transparent')
            modo_frame.grid(row=2, column=1, columnspan=6, sticky='w', padx=6, pady=6)

            self.switch_modo_fisico = ctk.CTkSwitch(
                modo_frame,
                text='',
                fg_color='#666666',  # Color apagado (gris)
                progress_color='#00AA00',  # Color encendido (verde)
                width=50,
                height=24
            )
            self.switch_modo_fisico.pack(side='left')

            self.lbl_modo_estado = ctk.CTkLabel(
                modo_frame,
                text='NO (solo simulación en pantalla)',
                text_color='#FF6666',  # Rojo apagado
                font=get_font('label', module=module_name)
            )
            self.lbl_modo_estado.pack(side='left', padx=(8, 0))

            # Callback para actualizar texto cuando cambia
            def _on_modo_change():
                if self.switch_modo_fisico.get():
                    self.lbl_modo_estado.configure(
                        text='SÍ - Enviar a impresora térmica',
                        text_color='#66FF66'  # Verde encendido
                    )
                else:
                    self.lbl_modo_estado.configure(
                        text='NO (solo simulación en pantalla)',
                        text_color='#FF6666'  # Rojo apagado
                    )

            self.switch_modo_fisico.configure(command=_on_modo_change)
        except Exception:
            logging.exception('Error creando switch modo físico en ImpresoraUI')

        # --- Fila 3: Codepage (encoding para ESC/POS) ---
        try:
            lbl_codepage = ctk.CTkLabel(
                self.impresora_frame,
                text='Juego de caracteres',
                text_color=self.colors.get('text', COLOR_MATRIX),
                font=get_font('label', module=module_name)
            )
            lbl_codepage.grid(row=3, column=0, sticky='w', padx=6, pady=6)

            self.codepage_var = ctk.StringVar(value='cp858')
            self.cb_codepage = ctk.CTkComboBox(
                self.impresora_frame,
                variable=self.codepage_var,
                values=['cp858', 'cp1252', 'cp437'],
                width=180,
                **combo_kwargs
            )
            self.cb_codepage.grid(row=3, column=1, sticky='w', padx=6, pady=6)

            # Label informativo sobre qué soporta cada codepage
            self.lbl_codepage_info = ctk.CTkLabel(
                self.impresora_frame,
                text='CP858: €, tildes (recomendado POS)',
                text_color='#888888',
                font=get_font('small', module=module_name),
                wraplength=400,
                justify='left'
            )
            self.lbl_codepage_info.grid(row=3, column=2, columnspan=6, sticky='w', padx=6, pady=6)

            # Callback para actualizar info cuando cambia
            def _on_codepage_change(choice):
                info_map = {
                    'cp858': 'CP858: €, tildes, ñ (recomendado impresoras térmicas)',
                    'cp1252': 'CP1252: €, tildes, ñ, puntos suspensivos (Windows)',
                    'cp437': 'CP437: Sin €, compatible más antiguo (DOS)'
                }
                self.lbl_codepage_info.configure(text=info_map.get(choice, ''))

            self.cb_codepage.configure(command=_on_codepage_change)
        except Exception:
            logging.exception('Error creando selector codepage en ImpresoraUI')

        # --- Fila 4: Selector y preview de logo global ---
        try:
            lbl_logo = ctk.CTkLabel(
                self.impresora_frame,
                text='Logo global en ticket',
                text_color=self.colors.get('text', COLOR_MATRIX),
                font=get_font('label', module=module_name)
            )
            lbl_logo.grid(row=4, column=0, sticky='w', padx=6, pady=6)

            self.switch_logo = ctk.CTkSwitch(
                self.impresora_frame,
                text='Activar',
                fg_color=self.colors.get('primary', '#FF9800'),
                font=get_font('label', module=module_name)
            )
            self.switch_logo.grid(row=4, column=1, sticky='w', padx=6, pady=6)

            # Botón seleccionar logo (fila 5)
            btn_seleccionar = ButtonFactory.create_button(
                parent=self.impresora_frame,
                text='SELECCIONAR LOGO',
                command=self._seleccionar_logo,
                style_key='mini_action'
            )
            btn_seleccionar.grid(row=5, column=1, sticky='w', padx=6, pady=6)

            # Fila 6: Preview del logo
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
            self.logo_preview_label.grid(row=6, column=0, columnspan=4, sticky='w', padx=6, pady=12)

            # Variable interna para filename
            self.logo_filename = None
        except Exception:
            logging.exception('Error creando controles de logo en ImpresoraUI')

        # --- Fila 7: Selector y preview de logo LEVEL UP ---
        try:
            lbl_logo_nivel = ctk.CTkLabel(
                self.impresora_frame,
                text='Logo LEVEL UP (Subida Nivel)',
                text_color=self.colors.get('text', COLOR_MATRIX),
                font=get_font('label', module=module_name)
            )
            lbl_logo_nivel.grid(row=7, column=0, sticky='w', padx=6, pady=6)

            self.switch_logo_nivel = ctk.CTkSwitch(
                self.impresora_frame,
                text='Activar',
                fg_color=self.colors.get('primary', '#FF9800'),
                font=get_font('label', module=module_name)
            )
            self.switch_logo_nivel.grid(row=7, column=1, sticky='w', padx=6, pady=6)

            # Botón seleccionar logo nivel (fila 8)
            btn_seleccionar_nivel = ButtonFactory.create_button(
                parent=self.impresora_frame,
                text='SUBIR LOGO LEVEL UP',
                command=self._seleccionar_logo_nivel,
                style_key='mini_action'
            )
            btn_seleccionar_nivel.grid(row=8, column=1, sticky='w', padx=6, pady=6)

            # Fila 9: Preview del logo nivel
            self.logo_nivel_preview_label = ctk.CTkLabel(
                self.impresora_frame,
                text='Sin logo',
                text_color=self.colors.get('text', COLOR_MATRIX),
                font=get_font('label', module=module_name),
                width=200,
                height=150,
                fg_color=self.colors.get('bg_dark', '#0d0d0d'),
                corner_radius=8
            )
            self.logo_nivel_preview_label.grid(row=9, column=0, columnspan=4, sticky='w', padx=6, pady=12)

            # Variable interna para filename nivel
            self.logo_nivel_filename = None
        except Exception:
            logging.exception('Error creando controles de logo nivel en ImpresoraUI')

        # --- Fila 10-11: QR en ticket (activar + URL) ---
        try:
            lbl_qr = ctk.CTkLabel(
                self.impresora_frame,
                text='QR en ticket',
                text_color=self.colors.get('text', COLOR_MATRIX),
                font=get_font('label', module=module_name)
            )
            lbl_qr.grid(row=10, column=0, sticky='w', padx=6, pady=6)

            self.switch_qr = ctk.CTkSwitch(
                self.impresora_frame,
                text='Activar',
                fg_color=self.colors.get('primary', '#FF9800'),
                font=get_font('label', module=module_name)
            )
            self.switch_qr.grid(row=10, column=1, sticky='w', padx=6, pady=6)

            lbl_qr_url = ctk.CTkLabel(
                self.impresora_frame,
                text='URL QR:',
                text_color=self.colors.get('text', COLOR_MATRIX),
                font=get_font('label', module=module_name)
            )
            lbl_qr_url.grid(row=11, column=0, sticky='w', padx=6, pady=6)

            self.entry_qr_url = ctk.CTkEntry(
                self.impresora_frame,
                placeholder_text='https://tutienda.com',
                **combo_kwargs
            )
            self.entry_qr_url.grid(row=11, column=1, columnspan=7, sticky='we', padx=6, pady=6)
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
        """Cargar valores usando el repositorio para mayor eficiencia y consistencia."""
        if not self.db:
            return

        try:
            claves = [
                'printer_name', 'printer_width', 'modo_impresion', 'printer_codepage',
                'logo_enabled', 'logo_filename', 'logo_nivel_enabled', 'logo_nivel_filename',
                'qr_enabled', 'qr_url'
            ]
            config = self.config_repo.obtener_multiples(claves)

            # 1. Nombre de impresora
            p_name = config.get('printer_name')
            if p_name:
                try:
                    self.cb_impresora.set(p_name)
                except Exception:
                    try:
                        self.cb_impresora.configure(values=[p_name])
                        self.cb_impresora.set(p_name)
                    except Exception:
                        pass

            # 2. Ancho papel
            p_width = config.get('printer_width')
            if p_width:
                try:
                    self.paper_width_var.set(p_width)
                except Exception:
                    pass

            # 3. Modo impresión (escpos vs texto)
            modo = config.get('modo_impresion', 'texto')
            if modo == 'escpos':
                try:
                    self.switch_modo_fisico.select()
                    self.lbl_modo_estado.configure(text='SÍ - Enviar a impresora térmica', text_color='#66FF66')
                except Exception:
                    pass
            else:
                try:
                    self.switch_modo_fisico.deselect()
                    self.lbl_modo_estado.configure(text='NO (solo simulación en pantalla)', text_color='#FF6666')
                except Exception:
                    pass

            # 4. Codepage
            cp = config.get('printer_codepage', 'cp858')
            if cp in ('cp858', 'cp1252', 'cp437'):
                try:
                    self.codepage_var.set(cp)
                    info_map = {
                        'cp858': 'CP858: €, tildes, ñ (recomendado impresoras térmicas)',
                        'cp1252': 'CP1252: €, tildes, ñ, puntos suspensivos (Windows)',
                        'cp437': 'CP437: Sin €, compatible más antiguo (DOS)'
                    }
                    self.lbl_codepage_info.configure(text=info_map.get(cp, ''))
                except Exception:
                    pass

            # 5. Logo Global
            if config.get('logo_enabled') == '1':
                try:
                    self.switch_logo.select()
                except Exception:
                    pass
            else:
                try:
                    self.switch_logo.deselect()
                except Exception:
                    pass

            self.logo_filename = config.get('logo_filename')
            if self.logo_filename:
                base_dir = Path(__file__).resolve().parents[3]
                logo_path = base_dir / 'assets' / 'logo' / self.logo_filename
                if logo_path.exists():
                    try:
                        self._mostrar_preview(logo_path)
                    except Exception:
                        pass

            # 6. Logo Level Up
            if config.get('logo_nivel_enabled') == '1':
                try:
                    self.switch_logo_nivel.select()
                except Exception:
                    pass
            else:
                try:
                    self.switch_logo_nivel.deselect()
                except Exception:
                    pass

            self.logo_nivel_filename = config.get('logo_nivel_filename')
            if self.logo_nivel_filename:
                base_dir = Path(__file__).resolve().parents[3]
                logo_path = base_dir / 'assets' / 'logo' / self.logo_nivel_filename
                if logo_path.exists():
                    try:
                        self._mostrar_preview_nivel(logo_path)
                    except Exception:
                        pass

            # 7. QR Code
            if config.get('qr_enabled') == '1':
                try:
                    self.switch_qr.select()
                except Exception:
                    pass
            else:
                try:
                    self.switch_qr.deselect()
                except Exception:
                    pass

            qr_url = config.get('qr_url', '')
            try:
                self.entry_qr_url.delete(0, 'end')
                self.entry_qr_url.insert(0, qr_url)
            except Exception:
                pass

        except Exception:
            logging.exception('Error cargando datos en ImpresoraUI via Repository')

    def _on_save(self):
        """Guardar configuración de forma atómica usando el repositorio."""
        if not self.db:
            return

        try:
            cambios = {
                'printer_name': self.cb_impresora.get(),
                'printer_width': self.paper_width_var.get(),
                'modo_impresion': 'escpos' if self.switch_modo_fisico.get() else 'texto',
                'printer_codepage': self.codepage_var.get() or 'cp858',
                'logo_enabled': '1' if self.switch_logo.get() else '0',
                'logo_nivel_enabled': '1' if self.switch_logo_nivel.get() else '0',
                'qr_enabled': '1' if self.switch_qr.get() else '0',
                'qr_url': self.entry_qr_url.get().strip()
            }

            if self.logo_filename:
                cambios['logo_filename'] = self.logo_filename
            
            if self.logo_nivel_filename:
                cambios['logo_nivel_filename'] = self.logo_nivel_filename

            self.config_repo.guardar_multiples(cambios)
            ToastWidget.show(self.parent, 'Configuración de impresora guardada', tipo='success')

        except Exception:
            logging.exception('Error en _on_save de ImpresoraUI')
            from kool_tpv.utils.custom_dialog import show_error
            show_error(self.container, 'Error', 'No se pudo guardar la configuración')

    def _test_impresion(self):
        """Imprimir ticket de prueba usando el servicio real de impresión."""
        try:
            from kool_tpv.modulos.impresion.impresora_service import ImpresoraService
            from kool_tpv.modulos.impresion.ticket_type import TicketType
            
            # Instanciar servicio (usará el modo que acabamos de guardar o el que esté en BD)
            imp_svc = ImpresoraService(db=self.db)
            
            printer_name = self.cb_impresora.get()
            if not printer_name or printer_name == 'Sin impresoras detectadas':
                ToastWidget.show(self.parent, 'Selecciona una impresora primero', tipo='warning')
                return

            # Datos dummy para el test
            test_data = {
                'num_ticket': 'TEST-0001',
                'fecha': datetime.now().strftime('%d/%m/%Y'),
                'hora': datetime.now().strftime('%H:%M'),
                'cajero': 'ADMIN'
            }
            
            items = [
                {'nombre': 'PRODUCTO TEST', 'pvp': 10.0, 'cantidad': 1, 'total_linea': 10.0}
            ]

            # Intentar imprimir usando la lógica real del sistema
            res = imp_svc.imprimir(
                ticket_type=TicketType.VENTA,
                data=test_data,
                items=items,
                printer_name=printer_name
            )

            if res:
                ToastWidget.show(self.parent, f'Ticket de prueba enviado a {printer_name}', tipo='success')
            else:
                ToastWidget.show(self.parent, 'Error al generar ticket de prueba', tipo='error')

        except Exception:
            logging.exception('Error en test de impresión')
            from kool_tpv.utils.custom_dialog import show_error
            show_error(self.container, 'Error', 'No se pudo realizar el test de impresión')

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

            ToastWidget.show(self.parent, 'Logo cargado', tipo='success')

        except Exception:
            logging.exception('Error seleccionando logo')
            from kool_tpv.utils.custom_dialog import show_error
            show_error(self.container, 'Error', 'No se pudo cargar el logo')

    def _seleccionar_logo_nivel(self):
        """Abrir diálogo, copiar imagen a assets/logo/ como logo_nivel.png y mostrar preview."""
        try:
            filepath = filedialog.askopenfilename(
                title='Seleccionar logo LEVEL UP',
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

            # Copiar archivo con nombre específico para nivel
            dest_path = logo_dir / 'logo_nivel.png'

            import shutil
            shutil.copy2(filepath, dest_path)

            # Guardar filename internamente
            self.logo_nivel_filename = 'logo_nivel.png'

            # Mostrar preview
            self._mostrar_preview_nivel(dest_path)

            ToastWidget.show(self.parent, 'Logo LEVEL UP cargado', tipo='success')

        except Exception:
            logging.exception('Error seleccionando logo nivel')
            from kool_tpv.utils.custom_dialog import show_error
            show_error(self.container, 'Error', 'No se pudo cargar el logo de nivel')

    def _mostrar_preview_nivel(self, image_path):
        """Mostrar preview del logo LEVEL UP en el label."""
        try:
            img = Image.open(image_path)

            # Redimensionar manteniendo proporción (máx 180x120)
            img.thumbnail((180, 120), Image.LANCZOS)

            # Convertir a PhotoImage
            photo = ImageTk.PhotoImage(img)

            # Actualizar label
            self.logo_nivel_preview_label.configure(image=photo, text='')
            self.logo_nivel_preview_label.image = photo  # Mantener referencia

        except Exception:
            logging.exception('Error mostrando preview logo nivel')

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
