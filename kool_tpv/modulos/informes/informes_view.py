"""Informes module main view.

Minimal scaffold for the Informes module. Shows a centered placeholder
label in the central area provided by BaseModuleView.
"""
from typing import Optional
import customtkinter as ctk
import logging

from kool_tpv.utils.config_loader import load_colors, create_action_button
from kool_tpv.utils.templates.base_module_view import BaseModuleView
from kool_tpv.utils.utils import FONT_TERMINAL
from kool_tpv.utils.widgets.date_picker_entry import DatePickerEntry
from kool_tpv.modulos.informes.informes_service import InformesService
from kool_tpv.utils.formatter_service import FormatterService


class InformesView(BaseModuleView):
    """Main view for the Informes module (placeholder).

    This class is intentionally minimal: it provides the UI shell and a
    centered message indicating the module is under construction. No
    business logic or database queries are performed here.
    """

    def __init__(self, parent, db, keyboard_manager: Optional[object] = None):
        # Initialize BaseModuleView using module key 'informes' so the
        # sidebar palette and menu are loaded according to config.
        super().__init__(parent, config_section='informes')

        # Store commonly used references
        try:
            self.db = db
            self.keyboard_manager = keyboard_manager
        except Exception:
            self.db = db
            self.keyboard_manager = None

        # Load colors for the module (used by future UIs)
        try:
            self.colors = load_colors('informes') or {}
        except Exception:
            logging.exception('Error loading colors for informes')
            self.colors = {}

        # Update breadcrumb to module root (display only)
        try:
            self.actualizar_ruta('INFORMES')
        except Exception:
            logging.exception('Error updating breadcrumb in InformesView')

        # Show generator immediately when entering the module
        try:
            self.show_generar()
        except Exception:
            logging.exception('Error auto-opening generador en InformesView')

    def get_widget(self):
        return self

    def show_generar(self):
        """Mostrar el generador de informes (placeholder).

        Crea un frame simple con un label centrado y actualiza la ruta.
        """
        try:
            colors = self.colors or {}
            primary_btn = (colors.get('buttons') or {}).get('primary', {})
            btn_bg = primary_btn.get('bg', colors.get('primary', '#00A4DF'))
            btn_hover = primary_btn.get('hover', primary_btn.get('bg', '#6FCFF5'))
            btn_text = primary_btn.get('text', colors.get('text', '#FFFFFF'))

            # Main content frame
            content_frame = ctk.CTkFrame(self.central_area, fg_color=colors.get('background', 'transparent'))

            # HEADER
            header_frame = ctk.CTkFrame(content_frame, fg_color='transparent')
            header_frame.pack(fill='x', padx=12, pady=(12, 8))

            title_lbl = ctk.CTkLabel(header_frame, text='GENERADOR DE INFORMES', font=FONT_TERMINAL, text_color=colors.get('text'))
            title_lbl.pack(anchor='w', padx=6, pady=(0, 6))

            # Filters row
            filters_frame = ctk.CTkFrame(header_frame, fg_color='transparent')
            filters_frame.pack(fill='x', padx=6, pady=(4, 6))

            lbl_tipo = ctk.CTkLabel(filters_frame, text='Tipo:', font=FONT_TERMINAL, text_color=colors.get('text'))
            lbl_tipo.pack(side='left', padx=(0, 6))
            self.cb_tipo_informe = ctk.CTkComboBox(filters_frame, values=['Ventas por rango de fechas'], state='readonly', width=220)
            self.cb_tipo_informe.pack(side='left', padx=(0, 12))

            lbl_desde = ctk.CTkLabel(filters_frame, text='Desde:', font=FONT_TERMINAL, text_color=colors.get('text'))
            lbl_desde.pack(side='left', padx=(0, 6))
            self.entry_fecha_inicio = DatePickerEntry(filters_frame, module_name='informes', width=140, allow_future=False)
            self.entry_fecha_inicio.pack(side='left', padx=(0, 12))

            lbl_hasta = ctk.CTkLabel(filters_frame, text='Hasta:', font=FONT_TERMINAL, text_color=colors.get('text'))
            lbl_hasta.pack(side='left', padx=(0, 6))
            self.entry_fecha_fin = DatePickerEntry(filters_frame, module_name='informes', width=140, allow_future=False)
            self.entry_fecha_fin.pack(side='left', padx=(0, 12))

            self.btn_generar = ctk.CTkButton(filters_frame, text='GENERAR', width=140, height=32,
                                             fg_color=btn_bg, hover_color=btn_hover, text_color=btn_text,
                                             command=self._on_generar_click, font=FONT_TERMINAL)
            self.btn_generar.pack(side='left', padx=(6, 0))

            # BODY
            result_frame = ctk.CTkFrame(content_frame, fg_color='transparent')
            result_frame.pack(fill='both', expand=True, padx=12, pady=(6, 12))

            self.result_textbox = ctk.CTkTextbox(result_frame)
            self.result_textbox.pack(fill='both', expand=True)
            try:
                self.result_textbox.configure(state='disabled')
            except Exception:
                pass

            # FOOTER (placeholder)
            footer_frame = ctk.CTkFrame(content_frame, fg_color='transparent')
            footer_frame.pack(fill='x', padx=12, pady=(0, 12))

            # Export button (use central create_action_button for consistent styling)
            try:
                btn_export = create_action_button(
                    footer_frame,
                    'exportar',
                    self._on_exportar_click
                )
                btn_export.pack(side='left', padx=8)
            except Exception:
                logging.exception('Error creando botón Exportar en InformesView')

            navigated = False
            try:
                navigated = self.set_central_content(content_frame)
            except Exception:
                logging.exception('Error pasando content_frame a set_central_content en show_generar')

            if navigated:
                try:
                    self.actualizar_ruta('INFORMES / GENERAR')
                except Exception:
                    pass

        except Exception:
            logging.exception('Error en show_generar de InformesView')

    def _on_generar_click(self):
        try:
            fecha_inicio = self.entry_fecha_inicio.get()
            fecha_fin = self.entry_fecha_fin.get()

            from kool_tpv.utils.custom_dialog import show_warning

            if not fecha_inicio or not fecha_fin:
                try:
                    show_warning(self.central_area, 'Fechas requeridas', 'Debes seleccionar ambas fechas')
                except Exception:
                    pass
                return

            if fecha_inicio > fecha_fin:
                try:
                    show_warning(self.central_area, 'Rango inválido', 'La fecha inicio no puede ser mayor que la fecha fin')
                except Exception:
                    pass
                return

            try:
                service = InformesService(self.db)
                report_data = service.get_informe_ventas_por_rango(fecha_inicio, fecha_fin)
                self._render_report(report_data)
            except Exception:
                logging.exception('Error generando informe')

        except Exception:
            logging.exception('Error en _on_generar_click')

    def _render_report(self, report_data: dict):
        try:
            from kool_tpv.utils.formatter_service import FormatterService
            formatter = FormatterService()

            try:
                self.result_textbox.configure(state='normal')
                self.result_textbox.delete('1.0', 'end')
            except Exception:
                pass

            # Title
            self.result_textbox.insert('end', f"{report_data.get('title', '')}\n")

            # Metadata
            generated_at = report_data.get('generated_at')
            if generated_at:
                try:
                    self.result_textbox.insert('end', f"Generado: {formatter.format_fecha(generated_at)}\n")
                except Exception:
                    self.result_textbox.insert('end', f"Generado: {generated_at}\n")

            rango = report_data.get('range', {})
            if rango:
                start = rango.get('start')
                end = rango.get('end')
                if start and end:
                    try:
                        self.result_textbox.insert('end',
                            f"Rango: {formatter.format_fecha(start + ' 00:00:00')} → {formatter.format_fecha(end + ' 00:00:00')}\n"
                        )
                    except Exception:
                        self.result_textbox.insert('end', f"Rango: {start} → {end}\n")

            self.result_textbox.insert('end', '-' * 40 + "\n\n")

            # Sections
            for section in report_data.get('sections', []):

                # Determine which columns are monetary (indexes)
                money_columns = section.get('money_columns', []) or []

                if section.get('title'):
                    self.result_textbox.insert('end', f"{section.get('title')}\n")

                headers = section.get('headers', [])
                rows = section.get('rows', [])

                if section.get('type') == 'summary':
                    self.result_textbox.insert('end', '-' * 40 + "\n")
                    if headers and rows:
                        vals = rows[0]
                        for col_index, (header, value) in enumerate(zip(headers, vals)):
                            try:
                                if col_index in money_columns and isinstance(value, (int, float)):
                                    value_fmt = formatter.format_precio(value)
                                else:
                                    value_fmt = str(value)
                            except Exception:
                                value_fmt = str(value)
                            self.result_textbox.insert('end', f"{header:<20} : {value_fmt}\n")
                    self.result_textbox.insert('end', "\n")

                elif section.get('type') == 'table':
                    self.result_textbox.insert('end', '-' * 40 + "\n")
                    if headers:
                        self.result_textbox.insert('end', " | ".join(headers) + "\n")
                    for row in rows:
                        formatted_row = []
                        for col_index, value in enumerate(row):
                            try:
                                if col_index in money_columns and isinstance(value, (int, float)):
                                    formatted_row.append(formatter.format_precio(value))
                                else:
                                    formatted_row.append(str(value))
                            except Exception:
                                formatted_row.append(str(value))
                        self.result_textbox.insert('end', " | ".join(formatted_row) + "\n")
                    self.result_textbox.insert('end', "\n")

            try:
                self.result_textbox.configure(state='disabled')
            except Exception:
                pass

        except Exception:
            import logging
            logging.exception('Error renderizando informe')

    def _on_exportar_click(self):
        try:
            # Read selected dates
            fecha_inicio = self.entry_fecha_inicio.get()
            fecha_fin = self.entry_fecha_fin.get()

            from kool_tpv.utils.custom_dialog import show_warning, show_error, show_success

            if not fecha_inicio or not fecha_fin:
                try:
                    show_warning(self.central_area, 'Fechas requeridas', 'Debes seleccionar ambas fechas antes de exportar')
                except Exception:
                    pass
                return

            # Build the generic report data using the service
            try:
                service = InformesService(self.db)
                report_data = service.get_informe_ventas_por_rango(fecha_inicio, fecha_fin)
            except Exception:
                logging.exception('Error obteniendo datos para exportar informe')
                try:
                    show_error(self.central_area, 'Error', 'No se pudieron obtener los datos para exportar. Revisa logs.')
                except Exception:
                    pass
                return

            # Ask save path
            try:
                from tkinter import filedialog as fd
                path = fd.asksaveasfilename(
                    defaultextension='.csv',
                    filetypes=[('CSV files', '*.csv'), ('PDF files', '*.pdf')],
                    title='Guardar informe',
                    parent=self.central_area
                )
            except Exception:
                logging.exception('Error abriendo diálogo de guardar')
                path = None

            if not path:
                return

            # Dispatch to ExportService using the generic report_data
            try:
                from kool_tpv.modulos.impresion.export_service import ExportService
                export_service = ExportService(self.db)

                try:
                    if path.lower().endswith('.csv'):
                        export_service.export_report_csv(report_data, path)
                    elif path.lower().endswith('.pdf'):
                        export_service.export_report_pdf(report_data, path)
                    else:
                        try:
                            show_warning(self.central_area, 'Formato no soportado', 'Elige .csv o .pdf')
                        except Exception:
                            pass
                        return

                    try:
                        show_success(self.central_area, 'Exportado', f'Informe guardado en: {path}')
                    except Exception:
                        pass

                except PermissionError:
                    try:
                        show_error(
                            self.central_area,
                            'No se pudo guardar el archivo',
                            'El archivo está abierto o no tienes permisos.\nCiérralo e inténtalo de nuevo.'
                        )
                    except Exception:
                        logging.exception('Error mostrando diálogo PermissionError en exportar informe')

                except Exception:
                    try:
                        show_error(
                            self.central_area,
                            'Error al exportar',
                            'Ocurrió un error inesperado al generar el archivo.'
                        )
                    except Exception:
                        logging.exception('Error mostrando diálogo general en exportar informe')

            except Exception:
                logging.exception('Error durante exportación del informe')
                try:
                    show_error(self.central_area, 'Error', 'Fallo al exportar el informe. Revisa logs.')
                except Exception:
                    pass
        except Exception:
            logging.exception('Error en _on_exportar_click')
