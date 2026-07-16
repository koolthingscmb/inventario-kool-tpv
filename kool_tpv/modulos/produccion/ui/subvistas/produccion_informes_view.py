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
from kool_tpv.modulos.produccion.ui.subvistas.config_helper import cargar_config_produccion, get_chip_config, get_chip_style, get_font as get_prod_font


class ProduccionInformesView:
    def __init__(self, parent, db, colors=None, km=None):
        self.parent = parent
        self.db = db
        self.colors = colors or load_colors('produccion')
        self.km = km
        self.service = ProduccionInformesService(db)
        
        # Repositorios para filtros
        from kool_tpv.modulos.produccion.repositories.produccion_colecciones_repository import ProduccionColeccionesRepository
        from kool_tpv.modulos.produccion.repositories.produccion_sufijos_repository import ProduccionSufijosRepository
        self.colecciones_repo = ProduccionColeccionesRepository(db)
        self.sufijos_repo = ProduccionSufijosRepository(db)

        # Estado del informe actual
        self.current_report_data = None
        self._filtros_diseno = {
            "coleccion_ids": [],
            "sufijo_ids": []
        }
        
        # Cargar configuración de producción
        self.prod_config = cargar_config_produccion()
        
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
            "Producción de diseños"
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
        
        # --- Frame de Chips (Filtros dinámicos) ---
        self.chips_frame_main = ctk.CTkFrame(self.container, fg_color='transparent')
        # Se packea solo cuando se necesita
        
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
        """Ocultar/Mostrar fechas y chips según el tipo de informe."""
        # Resetear filtros al cambiar de informe
        self._filtros_diseno = {"coleccion_ids": [], "sufijo_ids": []}

        if "Stock" in value:
            self.dates_frame.pack_forget()
        else:
            self.dates_frame.pack(side='left', after=self.cb_tipo_informe)
            
        if value == "Producción de diseños":
            self.chips_frame_main.pack(fill='x', padx=20, pady=(0, 10), after=self.filters_frame)
            self._render_chips_filtros()
        else:
            self.chips_frame_main.pack_forget()
            
    def _render_chips_filtros(self):
        """Renderizar los chips de Colección y Sufijo usando config_helper."""
        for w in self.chips_frame_main.winfo_children():
            w.destroy()
            
        # Config de chips desde config_helper (igual que diseno_nuevo)
        chip_cfg = get_chip_config(self.prod_config, "diseno")
        default_cfg = get_chip_style(chip_cfg, "default")
        selected_cfg = get_chip_style(chip_cfg, "selected")
        font_key = chip_cfg.get("font_key", "label")
        chip_font = get_prod_font(self.prod_config, font_key)
        chip_height = chip_cfg.get("height", 40)
        chip_radius = chip_cfg.get("corner_radius", 8)
        chip_padx = chip_cfg.get("padx", 6)
        chip_pady = chip_cfg.get("pady", 4)
        
        # Contenedor para Colecciones
        f_col = ctk.CTkFrame(self.chips_frame_main, fg_color='transparent')
        f_col.pack(fill='x', pady=2)
        ctk.CTkLabel(f_col, text="Colecciones:", font=get_font('label_small'), text_color=self.colors.get('text_secondary')).pack(side='left', padx=5)
        col_grid = ctk.CTkFrame(f_col, fg_color='transparent')
        col_grid.pack(fill='x', side='left')
        cols = 20
        for c in range(cols):
            col_grid.grid_columnconfigure(c, weight=1)
        
        # Contenedor para Sufijos
        f_suf = ctk.CTkFrame(self.chips_frame_main, fg_color='transparent')
        f_suf.pack(fill='x', pady=2)
        suf_grid = ctk.CTkFrame(f_suf, fg_color='transparent')
        suf_grid.pack(fill='x', side='left')
        for c in range(cols):
            suf_grid.grid_columnconfigure(c, weight=1)
        ctk.CTkLabel(suf_grid, text="Sufijos:", font=get_font('label_small'), text_color=self.colors.get('text_secondary')).grid(row=0, column=0, padx=5, sticky='w')
        
        # Pintar Colecciones
        for idx, c in enumerate(self.colecciones_repo.get_activas()):
            is_sel = c.id in self._filtros_diseno["coleccion_ids"]
            style = selected_cfg if is_sel else default_cfg
            
            btn = ctk.CTkButton(
                col_grid, text=c.nombre, width=0, height=chip_height, corner_radius=chip_radius,
                fg_color=style.get("bg", "#1a1a2e"),
                text_color=style.get("text", "#e0e0e0"),
                border_color=style.get("border", "#552583"),
                border_width=style.get("border_width", 1),
                hover_color=style.get("hover", "#C77BFF"),
                font=chip_font,
                command=lambda cid=c.id: self._toggle_filtro("coleccion_ids", cid)
            )
            btn.grid(row=idx // cols, column=idx % cols, padx=chip_padx, pady=chip_pady, sticky="ew")
            
        # Pintar Sufijos
        for idx, s in enumerate(self.sufijos_repo.get_activos()):
            is_sel = s.id in self._filtros_diseno["sufijo_ids"]
            style = selected_cfg if is_sel else default_cfg
            
            btn = ctk.CTkButton(
                suf_grid, text=s.nombre, width=0, height=chip_height, corner_radius=chip_radius,
                fg_color=style.get("bg", "#1a1a2e"),
                text_color=style.get("text", "#e0e0e0"),
                border_color=style.get("border", "#552583"),
                border_width=style.get("border_width", 1),
                hover_color=style.get("hover", "#C77BFF"),
                font=chip_font,
                command=lambda sid=s.id: self._toggle_filtro("sufijo_ids", sid)
            )
            col = (idx % (cols - 1)) + 1
            row = idx // (cols - 1)
            btn.grid(row=row, column=col, padx=chip_padx, pady=chip_pady, sticky="ew")

    def _toggle_filtro(self, key, item_id):
        if item_id in self._filtros_diseno[key]:
            self._filtros_diseno[key].remove(item_id)
        else:
            self._filtros_diseno[key].append(item_id)
        self._render_chips_filtros()
            
    def _on_generar_click(self):
        try:
            tipo = self.cb_tipo_informe.get()
            fi = self.entry_desde.get()
            ff = self.entry_hasta.get()
            
            if "Stock" not in tipo and fi > ff:
                ToastWidget.show(self.container, 'LA FECHA DE INICIO NO PUEDE SER POSTERIOR A LA DE FIN', tipo='warning')
                return
            
            # Llamar al service según el tipo
            if tipo == "Resumen de producción":
                report_data = self.service.get_informe_resumen_produccion(fi, ff)
            elif tipo == "Producción por tipo":
                report_data = self.service.get_informe_produccion_por_tipo(fi, ff)
            elif tipo == "Producción de diseños":
                report_data = self.service.get_informe_produccion_detallada_disenos(
                    fi, ff, 
                    coleccion_ids=self._filtros_diseno["coleccion_ids"],
                    sufijo_ids=self._filtros_diseno["sufijo_ids"]
                )
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
        """Renderizar el informe como lista legible (formato bloques)."""
        self.result_textbox.delete('1.0', 'end')

        # Cabecera
        self.result_textbox.insert('end', f"{report_data['titulo']}\n")
        self.result_textbox.insert('end', f"Generado: {report_data['fecha_generacion']}\n\n")

        # Items como bloques: primera columna = nombre, resto = atributos
        headers = report_data.get('headers', [])
        items = report_data.get('items', [])

        for row in items:
            name = str(row[0]) if row else ''
            self.result_textbox.insert('end', f"  '{name}':\n")
            attrs = []
            for i, h in enumerate(headers[1:], start=1):
                if i < len(row):
                    attrs.append(f"{h}: {row[i]}")
            if attrs:
                self.result_textbox.insert('end', f"    {'  |  '.join(attrs)}\n")
            self.result_textbox.insert('end', '\n')

        # Resumen al final
        resumen = report_data.get('resumen')
        if resumen:
            self.result_textbox.insert('end', "─" * 50 + "\n")
            self.result_textbox.insert('end', "RESUMEN:\n")
            for k, v in resumen.items():
                self.result_textbox.insert('end', f"  {k}: {v}\n")

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
