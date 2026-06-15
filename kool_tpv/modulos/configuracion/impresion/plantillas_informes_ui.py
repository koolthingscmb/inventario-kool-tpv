"""PlantillasInformesUI: configuracion plantilla visual para PDF de informes."""
import logging
import shutil
from pathlib import Path
from tkinter import filedialog
import customtkinter as ctk
from PIL import Image
from kool_tpv.utils.config_loader import load_colors
from kool_tpv.utils.factories.button_factory import ButtonFactory
from kool_tpv.utils.font_loader import get_font
from kool_tpv.base_datos.configuracion_repository import ConfiguracionRepository
from kool_tpv.utils.widgets.notificaciones import ToastWidget

ASSETS_DIR = Path(__file__).resolve().parents[3] / 'assets'
LOGO_PDF_FILENAME = 'logo_pdf.png'

CLAVES_PLANTILLA = {
    'informes_pdf_titulo': 'INFORME DE VENTAS',
    'informes_pdf_color_primario': '#1F6AA5',
    'informes_pdf_color_secundario': '#4A90A4',
    'informes_pdf_mostrar_logo': '0',
    'logo_pdf_filename': '',
}


class PlantillasInformesUI:
    def __init__(self, parent, db, module_name='config'):
        self.parent = parent
        self.db = db
        self.config_repo = ConfiguracionRepository(db)
        try:
            self.colors = load_colors(module_name)
        except Exception:
            logging.exception('Error cargando colores')
            self.colors = {}

        bg = self.colors.get('background', '#1a1a2e')
        lbl_font = get_font('label', module=module_name)
        entry_kwargs = {
            'fg_color': bg,
            'text_color': self.colors.get('text', '#FFFFFF'),
            'border_width': 2,
            'border_color': self.colors.get('border', self.colors.get('primary')),
            'corner_radius': 4,
            'font': get_font('entry', module=module_name),
        }

        self.container = ctk.CTkFrame(parent, fg_color=bg)

        ctk.CTkLabel(
            self.container,
            text='PLANTILLA PDF — INFORMES',
            font=get_font('title', module=module_name),
            text_color=self.colors.get('primary', '#1F6AA5')
        ).pack(anchor='w', padx=16, pady=(16, 4))

        ctk.CTkLabel(
            self.container,
            text='Configura el aspecto visual de los PDFs exportados desde Informes.',
            font=get_font('body', module=module_name),
            text_color=self.colors.get('text_secondary', self.colors.get('text'))
        ).pack(anchor='w', padx=16, pady=(0, 16))

        self.fields_frame = ctk.CTkFrame(self.container, fg_color=bg)
        self.fields_frame.pack(fill='x', padx=16, pady=4)

        for c in range(4):
            self.fields_frame.grid_columnconfigure(c, weight=1, uniform='col')

        ctk.CTkLabel(self.fields_frame, text='Titulo del documento',
                     font=lbl_font, text_color=self.colors.get('text')).grid(row=0, column=0, sticky='w', padx=8, pady=8)
        self.e_titulo = ctk.CTkEntry(self.fields_frame, **entry_kwargs)
        self.e_titulo.grid(row=0, column=1, columnspan=3, sticky='we', padx=8, pady=8)

        ctk.CTkLabel(self.fields_frame, text='Color primario (hex)',
                     font=lbl_font, text_color=self.colors.get('text')).grid(row=1, column=0, sticky='w', padx=8, pady=8)
        self.e_color_primario = ctk.CTkEntry(self.fields_frame, **entry_kwargs)
        self.e_color_primario.grid(row=1, column=1, sticky='we', padx=8, pady=8)

        ctk.CTkLabel(self.fields_frame, text='Color secundario (hex)',
                     font=lbl_font, text_color=self.colors.get('text')).grid(row=2, column=0, sticky='w', padx=8, pady=8)
        self.e_color_secundario = ctk.CTkEntry(self.fields_frame, **entry_kwargs)
        self.e_color_secundario.grid(row=2, column=1, sticky='we', padx=8, pady=8)

        ctk.CTkLabel(self.fields_frame, text='Mostrar logo',
                     font=lbl_font, text_color=self.colors.get('text')).grid(row=3, column=0, sticky='w', padx=8, pady=8)
        self.var_mostrar_logo = ctk.StringVar(value='0')
        self.switch_logo = ctk.CTkSwitch(
            self.fields_frame, text='', variable=self.var_mostrar_logo,
            onvalue='1', offvalue='0',
            progress_color=self.colors.get('primary'),
            button_color=self.colors.get('secondary'))
        self.switch_logo.grid(row=3, column=1, sticky='w', padx=8, pady=8)

        ctk.CTkLabel(self.fields_frame, text='Logo PDF',
                     font=lbl_font, text_color=self.colors.get('text')).grid(row=4, column=0, sticky='w', padx=8, pady=8)
        logo_row = ctk.CTkFrame(self.fields_frame, fg_color='transparent')
        logo_row.grid(row=4, column=1, columnspan=3, sticky='we', padx=8, pady=8)

        self.lbl_logo_path = ctk.CTkLabel(
            logo_row, text='Sin logo seleccionado',
            font=get_font('body', module=module_name),
            text_color=self.colors.get('text_secondary', self.colors.get('text')))
        self.lbl_logo_path.pack(side='left', padx=(0, 8))

        ButtonFactory.create_button(
            parent=logo_row, text='Seleccionar...',
            command=self._on_seleccionar_logo, style_key='action_secondary').pack(side='left', padx=(0, 8))
        ButtonFactory.create_button(
            parent=logo_row, text='Quitar',
            command=self._on_quitar_logo, style_key='action_secondary').pack(side='left')

        self.lbl_logo_preview = ctk.CTkLabel(self.fields_frame, text='', image=None)
        self.lbl_logo_preview.grid(row=5, column=1, columnspan=2, sticky='w', padx=8, pady=4)

        self.buttons_frame = ctk.CTkFrame(self.container, fg_color=bg)
        self.buttons_frame.pack(anchor='w', padx=16, pady=16)
        ButtonFactory.create_button(
            parent=self.buttons_frame, text='GUARDAR',
            command=self._on_guardar, style_key='action_primary').pack(side='left', padx=(0, 8))
        ButtonFactory.create_button(
            parent=self.buttons_frame, text='RESTAURAR DEFECTO',
            command=self._on_restaurar, style_key='action_secondary').pack(side='left')

        self._cargar_valores()

    def _cargar_valores(self):
        try:
            cfg = self.config_repo.obtener_multiples(list(CLAVES_PLANTILLA.keys()))
        except Exception:
            logging.exception('Error leyendo plantilla')
            cfg = {}

        def _val(clave):
            return cfg.get(clave, CLAVES_PLANTILLA[clave])

        self.e_titulo.delete(0, 'end')
        self.e_titulo.insert(0, _val('informes_pdf_titulo'))
        self.e_color_primario.delete(0, 'end')
        self.e_color_primario.insert(0, _val('informes_pdf_color_primario'))
        self.e_color_secundario.delete(0, 'end')
        self.e_color_secundario.insert(0, _val('informes_pdf_color_secundario'))
        self.var_mostrar_logo.set(_val('informes_pdf_mostrar_logo'))

        logo_file = _val('logo_pdf_filename')
        logo_path = ASSETS_DIR / logo_file if logo_file else None
        if logo_path and logo_path.exists():
            self.lbl_logo_path.configure(text=logo_file)
            self._mostrar_preview_logo(logo_path)
        else:
            self.lbl_logo_path.configure(text='Sin logo seleccionado')
            self.lbl_logo_preview.configure(image=None, text='')

    def _on_seleccionar_logo(self):
        try:
            ruta = filedialog.askopenfilename(
                parent=self.container,
                title='Seleccionar logo PDF',
                filetypes=[('Imagenes', '*.png *.jpg *.jpeg *.gif *.bmp'), ('Todos', '*.*')])
            if not ruta:
                return
            ASSETS_DIR.mkdir(parents=True, exist_ok=True)
            destino = ASSETS_DIR / LOGO_PDF_FILENAME
            shutil.copy2(ruta, destino)
            self.config_repo.guardar_multiples({'logo_pdf_filename': LOGO_PDF_FILENAME})
            self.lbl_logo_path.configure(text=LOGO_PDF_FILENAME)
            self._mostrar_preview_logo(destino)
        except Exception:
            logging.exception('Error seleccionando logo')
            from kool_tpv.utils.custom_dialog import show_error
            show_error(self.container, 'Error', 'No se pudo cargar el logo')

    def _on_quitar_logo(self):
        try:
            self.config_repo.guardar_multiples({'logo_pdf_filename': ''})
            self.lbl_logo_path.configure(text='Sin logo seleccionado')
            self.lbl_logo_preview.configure(image=None, text='')
        except Exception:
            logging.exception('Error quitando logo')

    def _mostrar_preview_logo(self, path):
        try:
            img = Image.open(path)
            img.thumbnail((120, 60))
            self._logo_ctk_image = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
            self.lbl_logo_preview.configure(image=self._logo_ctk_image, text='')
        except Exception:
            logging.exception('Error mostrando preview')
            self.lbl_logo_preview.configure(image=None, text='(preview no disponible)')

    def _on_guardar(self):
        campos = {
            'informes_pdf_titulo': self.e_titulo.get().strip(),
            'informes_pdf_color_primario': self.e_color_primario.get().strip(),
            'informes_pdf_color_secundario': self.e_color_secundario.get().strip(),
            'informes_pdf_mostrar_logo': self.var_mostrar_logo.get(),
        }
        try:
            self.config_repo.guardar_multiples(campos)
            ToastWidget.show(self.parent, 'Plantilla guardada', tipo='success')
        except Exception:
            logging.exception('Error guardando plantilla')
            from kool_tpv.utils.custom_dialog import show_error
            show_error(self.container, 'Error', 'No se pudo guardar la plantilla')

    def _on_restaurar(self):
        try:
            self.config_repo.guardar_multiples(CLAVES_PLANTILLA)
            self._cargar_valores()
            ToastWidget.show(self.parent, 'Valores por defecto restaurados', tipo='success')
        except Exception:
            logging.exception('Error restaurando plantilla')


