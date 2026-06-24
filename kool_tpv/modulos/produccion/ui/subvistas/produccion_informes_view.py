"""Vista de Informes del módulo de Producción.

Clonada de InformesView pero adaptada como subvista del módulo Producción,
con sus propios colores, tipos de informe y lógica de negocio.
"""
import logging
import tkinter as tk
import customtkinter as ctk
from datetime import datetime
from typing import Optional, Dict, Any

from kool_tpv.utils.config_loader import load_colors
from kool_tpv.utils.factories.button_factory import ButtonFactory
from kool_tpv.utils.font_loader import get_font
from kool_tpv.utils.widgets.date_picker_entry import DatePickerEntry
from kool_tpv.utils.widgets.notificaciones import ToastWidget, show_warning
from kool_tpv.utils.formatter_service import FormatterService

from kool_tpv.modulos.produccion.services.produccion_informes_service import ProduccionInformesService


class ProduccionInformesView:
    def __init__(self, parent, db, colors=None, km=None):
        self.parent = parent
        self.db = db
        self.colors = colors or load_colors('produccion')
        self.km = km
        self.service = ProduccionInformesService(db)
        
        # Estado del informe actual
        self.current_report_data = None
        
        # Contenedor principal
        self.container = ctk.CTkFrame(self.parent, fg_color=self.colors.get('background', '#1a1a1a'))
        self.container.pack(fill='both', expand=True)
        
        self._build_ui()
        
    def _build_ui(self):
        # --- Cabecera con Filtros ---
        self.filters_frame = ctk.CTkFrame(self.container, fg_color='transparent', height=60)
        self.filters_frame.pack(fill='x', padx=20, pady=10)
        self.filters_frame.pack_propagate(False)
        
        # Selector de tipo de informe
        lbl_tipo = ctk.CTkLabel(self.filters_frame, text='Tipo:', font=get_font('label'), text_color=self.colors.get('text'))
        lbl_tipo.pack(side='left', padx=(0, 6))
        
        self.report_types = [
            "Resumen de producción",
            "Producción por tipo",
            "Producción por diseño",
            "Producción por colección",
            "Stock por Tipo",
            "Stock por Variante",
            "Ventas de diseños"
        ]
        
        self.cb_tipo_informe = ctk.CTkComboBox(
            self.filters_frame,
            values=self.report_types,
            state='readonly',
            width=220,
            font=get_font('entry'),
            command=self._on_tipo_changed
        )
        self.cb_tipo_informe.set(self.report_types[0])
        self.cb_tipo_informe.pack(side='left', padx=(0, 20))
        
        # Filtros de fecha
        self.dates_frame = ctk.CTkFrame(self.filters_frame, fg_color='transparent')
        self.dates_frame.pack(side='left')
        
        self.lbl_desde = ctk.CTkLabel(self.dates_frame, text='Desde:', font=get_font('label'), text_color=self.colors.get('text'))
        self.lbl_desde.pack(side='left', padx=(0, 6))
        
        self.entry_desde = DatePickerEntry(self.dates_frame, width=120, default_mode='first_day_of_month')
        self.entry_desde.pack(side='left', padx=(0, 12))
        
        self.lbl_hasta = ctk.CTkLabel(self.dates_frame, text='Hasta:', font=get_font('label'), text_color=self.colors.get('text'))
        self.lbl_hasta.pack(side='left', padx=(0, 6))
        
        self.entry_hasta = DatePickerEntry(self.dates_frame, width=120, default_mode='today')
        self.entry_hasta.pack(side='left', padx=(0, 12))
        
        # Botón Generar
        self.btn_generar = ButtonFactory.create_button(
            self.filters_frame,
            text='GENERAR',
            command=self._on_generar_click,
            style_key='action_primary'
        )
        self.btn_generar.pack(side='right', padx=10)
        
        # --- Área de Resultados (Visor) ---
        self.viewer_frame = ctk.CTkFrame(self.container, fg_color=self.colors.get('bg_dark', '#0d0d0d'), corner_radius=8)
        self.viewer_frame.pack(fill='both', expand=True, padx=20, pady=(0, 10))
        
        self.result_textbox = ctk.CTkTextbox(
            self.viewer_frame,
            font=(get_font('terminal')[0], 14),
            fg_color='transparent',
            text_color='#ffffff',
            wrap='none',
            padx=20,
            pady=20
        )
        self.result_textbox.pack(fill='both', expand=True)
        
        # --- Footer con Exportación ---
        self.footer_frame = ctk.CTkFrame(self.container, fg_color='transparent', height=50)
        self.footer_frame.pack(fill='x', padx=20, pady=(0, 10))
        
        self.btn_export_csv = ButtonFactory.create_button(
            self.footer_frame,
            text='EXPORTAR CSV',
            command=lambda: self._exportar('csv'),
            style_key='action_secondary'
        )
        self.btn_export_csv.pack(side='left', padx=10)
        self.btn_export_csv.configure(state='disabled')
        
        self.btn_export_pdf = ButtonFactory.create_button(
            self.footer_frame,
            text='EXPORTAR PDF',
            command=lambda: self._exportar('pdf'),
            style_key='action_secondary'
        )
        self.btn_export_pdf.pack(side='left', padx=10)
        self.btn_export_pdf.configure(state='disabled')
        
    def _on_tipo_changed(self, value):
        """Ocultar/Mostrar fechas según el tipo de informe."""
        if "Stock" in value:
            self.dates_frame.pack_forget()
        else:
            self.dates_frame.pack(side='left', after=self.cb_tipo_informe)
            
    def _on_generar_click(self):
        try:
            tipo = self.cb_tipo_informe.get()
            fi = self.entry_desde.get()
            ff = self.entry_hasta.get()
            
            if "Stock" not in tipo and fi > ff:
                show_warning(self.container, "Fechas inválidas", "La fecha de inicio no puede ser posterior a la de fin.")
                return
            
            # Llamar al service según el tipo
            if tipo == "Resumen de producción":
                report_data = self.service.get_informe_resumen_produccion(fi, ff)
            elif tipo == "Producción por tipo":
                report_data = self.service.get_informe_produccion_por_tipo(fi, ff)
            elif tipo == "Producción por diseño":
                report_data = self.service.get_informe_produccion_por_diseno(fi, ff)
            elif tipo == "Producción por colección":
                report_data = self.service.get_informe_produccion_por_coleccion(fi, ff)
            elif tipo == "Stock por Tipo":
                report_data = self.service.get_informe_stock_por_tipo()
            elif tipo == "Stock por Variante":
                report_data = self.service.get_informe_stock_por_variante()
            elif tipo == "Ventas de diseños":
                report_data = self.service.get_informe_ventas_disenos(fi, ff)
            else:
                return
            
            self.current_report_data = report_data
            self._render_report(report_data)
            
            # Habilitar botones de exportación
            self.btn_export_csv.configure(state='normal')
            self.btn_export_pdf.configure(state='normal')
            
        except Exception:
            logging.exception("Error generando informe de producción")
            
    def _render_report(self, report_data):
        """Renderizar el informe en el textbox."""
        self.result_textbox.delete('1.0', 'end')
        
        # Título y Fecha
        self.result_textbox.insert('end', f"{report_data['titulo']}\n")
        self.result_textbox.insert('end', f"Generado: {report_data['fecha_generacion']}\n")
        self.result_textbox.insert('end', "=" * 60 + "\n\n")
        
        # Resumen (si existe)
        resumen = report_data.get('resumen')
        if resumen:
            self.result_textbox.insert('end', "RESUMEN:\n")
            for k, v in resumen.items():
                self.result_textbox.insert('end', f"  {k:<20}: {v}\n")
            self.result_textbox.insert('end', "-" * 60 + "\n\n")
            
        # Tabla (Cabeceras)
        headers = report_data.get('headers', [])
        if headers:
            header_str = " | ".join(headers)
            self.result_textbox.insert('end', f"{header_str}\n")
            self.result_textbox.insert('end', "-" * len(header_str) + "\n")
            
        # Tabla (Filas)
        for row in report_data.get('items', []):
            row_str = " | ".join(str(x) for x in row)
            self.result_textbox.insert('end', f"{row_str}\n")
            
        self.result_textbox.insert('end', "\n\n" + "." * 60 + "\n Fin del informe.")

    def _exportar(self, formato):
        if not self.current_report_data:
            return
            
        try:
            if formato == 'csv':
                # Exportación CSV propia (mejor para tablas de producción)
                self._exportar_csv_propio(self.current_report_data)
            else:
                from kool_tpv.modulos.informes.exportadores.exportador_pdf_informes import ExportadorPDFInformes
                exportador = ExportadorPDFInformes(self.db)
                resultado = exportador.exportar(self.current_report_data, self.container.winfo_toplevel())
                
                if resultado:
                    ToastWidget.show(self.container.winfo_toplevel(), "PDF exportado correctamente", tipo="success")
                
        except Exception:
            logging.exception("Error exportando informe")

    def _exportar_csv_propio(self, data):
        import csv
        from tkinter import filedialog
        
        filename = f"Produccion_{data['titulo'].replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialfile=filename,
            filetypes=[("CSV", "*.csv")]
        )
        
        if not path:
            return
            
        with open(path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f, delimiter=';')
            writer.writerow([data['titulo']])
            writer.writerow(["Generado", data['fecha_generacion']])
            writer.writerow([])
            
            if data.get('resumen'):
                for k, v in data['resumen'].items():
                    writer.writerow([k, v])
                writer.writerow([])
            
            writer.writerow(data['headers'])
            for row in data['items']:
                writer.writerow(row)
                
        ToastWidget.show(self.container.winfo_toplevel(), "CSV exportado correctamente", tipo="success")

    def get_widget(self):
        return self.container
