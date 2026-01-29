import customtkinter as ctk
import tkinter.messagebox as messagebox
from datetime import datetime, date, timedelta
from typing import List

try:
    from tkcalendar import DateEntry
except Exception:
    DateEntry = None

from modulos.tpv.cierre_service import CierreService
from modulos.exportar_importar.exportar_service import ExportarService
from tkinter import filedialog


class EstadisticasView(ctk.CTkFrame):
    """Vista inicial de Estadísticas.

    Panel izquierdo: selectores de fecha + lista de análisis + botones de export.
    Panel derecho: visor de tabla/texto con resultados.
    """

    OPTIONS = [
        ("por_tipo", "Por Tipo"),
        ("por_categoria", "Por Categoría"),
        ("por_articulo", "Por Artículo"),
        ("por_cajero", "Por Cajero"),
        ("por_proveedor", "Por Proveedor"),
        ("fidelizacion", "Fidelización"),
    ]

    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.pack(fill="both", expand=True, padx=12, pady=12)

        self._selected_options = set()
        self._option_buttons = {}
        self._current_columns: List[str] = []
        self._current_rows: List[List[str]] = []

        # layout containers
        main = ctk.CTkFrame(self)
        main.pack(fill="both", expand=True)

        left = ctk.CTkFrame(main, width=300, fg_color="#1a1a1a")
        left.pack(side="left", fill="y", padx=(0,12), pady=6)
        right = ctk.CTkFrame(main, fg_color="#0f0f0f")
        right.pack(side="right", fill="both", expand=True, pady=6)

        # Header: left (back) + center (title)
        # TEMPORARY: make header vivid red to diagnose visual plate origin
        header = ctk.CTkFrame(self, fg_color="red")
        header.place(relx=0.5, rely=0.02, anchor="n")
        header_left = ctk.CTkFrame(header, fg_color="transparent")
        header_left.pack(side='left')
        header_center = ctk.CTkFrame(header, fg_color="transparent")
        header_center.pack(side='left', expand=True)
        ctk.CTkLabel(header_center, text="ESTADÍSTICAS", font=(None, 20, "bold")).pack(pady=6)
        # Hide the header frame entirely to avoid overlapping/plate issues
        try:
            header.place_forget()
        except Exception:
            pass

        # Move the main title into the right panel header area to avoid overlay
        try:
            # replace the 'Área de visualización' label with the main title
            # find existing label creation below; we will create a clear title here
            title_lbl = ctk.CTkLabel(right, text="ESTADÍSTICAS", font=(None, 20, "bold"))
            title_lbl.pack(anchor="nw", padx=12, pady=(6, 2))
        except Exception:
            pass

        # Left: filtros
        ctk.CTkLabel(left, text="Opciones", font=(None, 14, "bold"), text_color="gray").pack(anchor="nw", padx=8, pady=(8, 4))
        ctk.CTkLabel(left, text="Desde").pack(anchor="w", padx=8, pady=(6, 0))
        if DateEntry:
            self.ent_desde = DateEntry(left, width=18)
        else:
            self.ent_desde = ctk.CTkEntry(left, width=260)
        self.ent_desde.pack(padx=8, pady=(0, 6))
        ctk.CTkLabel(left, text="Hasta").pack(anchor="w", padx=8)
        if DateEntry:
            self.ent_hasta = DateEntry(left, width=18)
        else:
            self.ent_hasta = ctk.CTkEntry(left, width=260)
        self.ent_hasta.pack(padx=8, pady=(0, 8))

        # Quick ranges
        quick_frame = ctk.CTkFrame(left, fg_color="#161616")
        quick_frame.pack(fill="x", padx=8, pady=(0, 8))
        ctk.CTkButton(quick_frame, text="Hoy", width=80, command=lambda: self._set_quick_range('today')).pack(side='left', padx=4, pady=4)
        ctk.CTkButton(quick_frame, text="7 días", width=80, command=lambda: self._set_quick_range('7days')).pack(side='left', padx=4, pady=4)
        ctk.CTkButton(quick_frame, text="Este mes", width=90, command=lambda: self._set_quick_range('month')).pack(side='left', padx=4, pady=4)
        ctk.CTkButton(quick_frame, text="Este año", width=90, command=lambda: self._set_quick_range('year')).pack(side='left', padx=4, pady=4)

        # Apply button
        ctk.CTkButton(left, text="Aplicar", width=260, fg_color="#5aa0d8", command=self._apply_filters).pack(padx=8, pady=(4, 8))

        # Options buttons container
        ctk.CTkLabel(left, text="Análisis", font=(None, 12, "bold"), text_color="gray").pack(anchor="w", padx=8, pady=(6, 4))
        btn_frame = ctk.CTkFrame(left, fg_color="#161616")
        btn_frame.pack(fill="both", expand=False, padx=8, pady=(0, 8))

        for key, label in self.OPTIONS:
            btn = ctk.CTkButton(btn_frame, text=label, width=260, fg_color="#2b2b2b",
                                command=lambda k=key: self._on_option_toggled(k))
            btn.pack(fill="x", pady=4)
            self._option_buttons[key] = btn

        # Spacer
        ctk.CTkLabel(left, text="", height=12, fg_color="transparent").pack(expand=True)

        # export buttons will be placed at bottom of right viewer; placeholder here

        # Right: visor
        ctk.CTkLabel(right, text="Área de visualización", font=(None, 14, "bold"), text_color="gray").pack(anchor="nw", padx=12, pady=12)
        self.visual_area = ctk.CTkTextbox(right, width=800, height=400)
        try:
            self.visual_area.configure(font=("Courier", 17))  # tamaño de fuente ajustado aquí
        except Exception:
            pass
        self.visual_area.pack(fill="both", expand=True, padx=12, pady=6)

        # services
        try:
            self.svc = getattr(self.controller, 'cierre_service', None) or CierreService()
        except Exception:
            self.svc = CierreService()
        try:
            self.exporter = ExportarService()
        except Exception:
            self.exporter = ExportarService()

        # Header left is left empty now; Back button moved to footer

        # initial help
        self._write_text(["Aquí aparecerán los desgloses y gráficos de ventas.", "Selecciona uno o más análisis a la izquierda y pulsa Aplicar."])

        # --- add footer controls under the viewer ---
        export_frame = ctk.CTkFrame(right, fg_color="#0f0f0f")
        export_frame.pack(side='bottom', fill='x', padx=12, pady=8)
        # Move 'Volver' here on the left and keep Exportar PDF on the right
        self.btn_volver = ctk.CTkButton(export_frame, text="← Volver", width=140, fg_color="#4b4b4b",
                    command=self._volver_inicio)
        self.btn_volver.pack(side='left', padx=8)
        self.btn_export_pdf = ctk.CTkButton(export_frame, text="Exportar PDF", width=140, fg_color="#3b6ea8",
                    command=self._export_pdf)
        self.btn_export_pdf.pack(side='right', padx=8)


    # --- UI helpers ---
    def _on_option_toggled(self, key: str):
        # toggle selection for multi-select
        if key in self._selected_options:
            self._selected_options.remove(key)
            try:
                self._option_buttons[key].configure(fg_color="#2b2b2b")
            except Exception:
                pass
        else:
            self._selected_options.add(key)
            try:
                self._option_buttons[key].configure(fg_color="#3b6ea8")
            except Exception:
                pass


    def _parse_dates(self):
        desde = self.ent_desde.get().strip() or None
        hasta = self.ent_hasta.get().strip() or None
        return desde, hasta

    def _load_data_for_option(self, key: str):
        desde, hasta = self._parse_dates()
        # Dispatch to service methods; handle missing methods gracefully
        try:
            if key == 'por_cajero':
                rows = self.svc.ventas_por_cajero(desde, hasta) or []
                cols = ['Cajero', 'Cajero ID', 'Total Ventas']
                data = [[r.get('nombre',''), str(r.get('cajero_id') or ''), f"{r.get('total_ventas',0):.2f}"] for r in rows]
            elif key in ('por_tipo', 'por_categoria', 'por_articulo'):
                desglose = getattr(self.svc, 'desglose_ventas')(desde, hasta)
                if key == 'por_tipo':
                    rows = desglose.get('por_tipo', [])
                    cols = ['Tipo', 'Cantidad', 'Total']
                    data = [[r.get('tipo',''), str(r.get('qty',0)), f"{r.get('total',0):.2f}"] for r in rows]
                elif key == 'por_categoria':
                    rows = desglose.get('por_categoria', [])
                    cols = ['Categoría', 'Cantidad', 'Total']
                    data = [[r.get('categoria',''), str(r.get('qty',0)), f"{r.get('total',0):.2f}"] for r in rows]
                else:
                    rows = desglose.get('por_articulo', [])
                    cols = ['Artículo', 'Cantidad', 'Total']
                    data = [[r.get('nombre',''), str(r.get('qty',0)), f"{r.get('total',0):.2f}"] for r in rows]
            elif key == 'por_proveedor':
                # try specific method, else try to use desglose o producto service
                if hasattr(self.svc, 'ventas_por_proveedor'):
                    rows = self.svc.ventas_por_proveedor(desde, hasta) or []
                    cols = ['Proveedor', 'Proveedor ID', 'Total Ventas']
                    data = [[r.get('proveedor',''), str(r.get('proveedor_id') or ''), f"{r.get('total_ventas',0):.2f}"] for r in rows]
                else:
                    # fallback: no direct method
                    cols = ['Proveedor', 'Total Ventas']
                    data = [["(no implementado)", "0.00"]]
            elif key == 'fidelizacion':
                try:
                    from modulos.tpv.fidelizacion_service import FidelizacionService
                    fid = FidelizacionService()
                    resumen = fid.desglose_puntos_periodo(desde, hasta)
                    cols = ['Tipo', 'Cliente', 'Cliente ID', 'Puntos']
                    data = []
                    data.append(['OTORGADOS', '', '', str(resumen.get('puntos_otorgados',0))])
                    for c in resumen.get('clientes_otorgados', []):
                        data.append(['OTORGADOS', c.get('nombre',''), str(c.get('cliente_id') or ''), str(c.get('puntos',0))])
                    data.append(['', '', '', ''])
                    data.append(['GASTADOS', '', '', str(resumen.get('puntos_gastados',0))])
                    for c in resumen.get('clientes_gastados', []):
                        data.append(['GASTADOS', c.get('nombre',''), str(c.get('cliente_id') or ''), str(c.get('puntos',0))])
                except Exception:
                    cols = ['Info']
                    data = [["Servicio de fidelización no disponible"]]
            else:
                cols = ['Info']
                data = [["Opción no reconocida"]]

            # store current table
            self._current_columns = cols
            self._current_rows = data
            return (cols, data)
        except Exception as e:
            self._write_text([f"Error cargando datos: {e}"])

    def _load_all_selected(self):
        # load all selected options and render combined
        all_sections = []
        try:
            # preserve OPTIONS order when rendering
            for key, _label in self.OPTIONS:
                if key not in self._selected_options:
                    continue
                section = self._load_data_for_option(key)
                if section:
                    all_sections.append((key, section[0], section[1]))
            if not all_sections:
                self._write_text(["No hay análisis seleccionados."])
                return
            # render combined
            lines = []
            for key, cols, rows in all_sections:
                # heading
                label = dict(self.OPTIONS).get(key, key)
                lines.append(f"=== {label} ===")
                # format table
                if not rows:
                    lines.append('No hay información disponible para este análisis en el período seleccionado.')
                    lines.append('')
                    continue
                col_widths = [max(len(c), 12) for c in cols]
                for r in rows:
                    for i, v in enumerate(r):
                        col_widths[i] = max(col_widths[i], len(str(v)))
                fmt = '  '.join('{:'+str(w)+'}' for w in col_widths)
                lines.append(fmt.format(*cols))
                lines.append('-' * (sum(col_widths) + 2 * (len(col_widths)-1)))
                for r in rows:
                    row = [str(x) for x in r] + [''] * max(0, len(cols) - len(r))
                    lines.append(fmt.format(*row[:len(cols)]))
                lines.append('')
            self._write_text(lines)
            # store flattened current state for exports
            self._current_columns = None
            self._current_rows = all_sections
        except Exception as e:
            self._write_text([f"Error cargando análisis combinados: {e}"])

    # --- rendering / export ---
    def _render_table(self, columns: List[str], rows: List[List[str]]):
        # Simple monospaced table in textbox
        try:
            col_widths = [max(len(c), 12) for c in columns]
            for r in rows:
                for i, v in enumerate(r):
                    col_widths[i] = max(col_widths[i], len(str(v)))

            fmt = '  '.join('{:'+str(w)+'}' for w in col_widths)
            lines = []
            lines.append(fmt.format(*columns))
            lines.append('-' * sum(col_widths) + '-' * (2 * (len(col_widths)-1)))
            for r in rows:
                # ensure row length matches columns
                row = [str(x) for x in r] + [''] * max(0, len(columns) - len(r))
                lines.append(fmt.format(*row[:len(columns)]))

            self._write_text(lines)
        except Exception as e:
            self._write_text([f"Error renderizando tabla: {e}"])

    def _write_text(self, lines: List[str]):
        try:
            self.visual_area.delete('0.0', 'end')
            for l in lines:
                self.visual_area.insert('end', l + '\n')
        except Exception:
            pass

    def _export_csv(self):
        if not self._selected_options:
            messagebox.showinfo('Exportar', 'Selecciona primero uno o más análisis a exportar')
            return
        desde, hasta = self._parse_dates()
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        nombre = f"estadisticas_{'_'.join(sorted(self._selected_options))}_{ts}.csv"
        try:
            # write combined CSV for all selected analyses
            import csv
            with open(nombre, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f, delimiter=';')
                # for each section in OPTIONS order, write header and rows
                for key, _label in self.OPTIONS:
                    if key not in self._selected_options:
                        continue
                    section = self._load_data_for_option(key)
                    if not section:
                        continue
                    cols, rows = section
                    writer.writerow([f"SECCION: {dict(self.OPTIONS).get(key, key)}"])
                    if not rows:
                        writer.writerow(["No hay información disponible para este análisis en el período seleccionado."])
                        writer.writerow([])
                        continue
                    writer.writerow(cols)
                    for r in rows:
                        writer.writerow(r)
                    writer.writerow([])
            messagebox.showinfo('Exportar CSV', f'CSV exportado: {nombre}')
        except Exception as e:
            messagebox.showerror('Exportar CSV', f'Error: {e}')

    def _export_pdf(self):
        if not self._selected_options:
            messagebox.showinfo('Exportar', 'Selecciona primero uno o más análisis a exportar')
            return
        desde, hasta = self._parse_dates()
        # normalize simple YYYY-MM-DD to full-day ISO timestamps expected by services
        def _norm_ts(d, is_start=True):
            if not d:
                return d
            if 'T' in d:
                return d
            # assume YYYY-MM-DD
            return (d + 'T00:00:00') if is_start else (d + 'T23:59:59')
        desde_ts = _norm_ts(desde, True)
        hasta_ts = _norm_ts(hasta, False)
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        nombre = f"estadisticas_{'_'.join(sorted(self._selected_options))}_{ts}.pdf"
        try:
            # PDF export: only support some combined exports via ExportarService where possible
            # If single selection and supported, delegate; else notify not implemented
            if len(self._selected_options) == 1:
                key = next(iter(self._selected_options))
                if key == 'por_cajero' and hasattr(self.exporter, 'exportar_ventas_por_cajero_pdf'):
                    ok = self.exporter.exportar_ventas_por_cajero_pdf(nombre, desde_ts, hasta_ts)
                    if ok:
                        messagebox.showinfo('Exportar PDF', f'PDF exportado: {nombre}')
                        return
                if key in ('por_tipo','por_categoria','por_articulo') and hasattr(self.exporter, 'exportar_desglose_ventas_pdf'):
                    ok = self.exporter.exportar_desglose_ventas_pdf(nombre, desde_ts, hasta_ts)
                    if ok:
                        messagebox.showinfo('Exportar PDF', f'PDF exportado: {nombre}')
                        return
            # If multiple options selected (or exporter-specific methods not available),
            # attempt to build a combined PDF from the current viewer content.
            # Ensure current data is loaded
            if not self._current_rows:
                # try to load current view (this will write to visual_area)
                self._load_all_selected()

            # _current_rows for combined rendering is a list of (key, columns, rows)
            combined = self._current_rows
            if combined:
                # Ask for destination file
                file_path = filedialog.asksaveasfilename(defaultextension='.pdf', filetypes=[('PDF Files','*.pdf')], title='Guardar archivo PDF')
                if not file_path:
                    return

                ok = self.exporter.exportar_estadisticas_pdf(file_path, combined, desde_ts, hasta_ts)
                if ok:
                    messagebox.showinfo('Exportar PDF', f'PDF exportado: {file_path}')
                    return

            # fallback message if nothing could be exported
            messagebox.showinfo('Exportar PDF', 'Export PDF no implementado para la selección actual — use CSV')
        except Exception as e:
            messagebox.showerror('Exportar PDF', f'Error: {e}')

    def _set_quick_range(self, kind: str):
        today = date.today()
        if kind == 'today':
            desde = hasta = today
        elif kind == '7days':
            desde = today - timedelta(days=6)
            hasta = today
        elif kind == 'month':
            desde = today.replace(day=1)
            hasta = today
        elif kind == 'year':
            desde = today.replace(month=1, day=1)
            hasta = today
        else:
            return
        if DateEntry:
            try:
                self.ent_desde.set_date(desde)
                self.ent_hasta.set_date(hasta)
            except Exception:
                self.ent_desde.delete(0, 'end'); self.ent_desde.insert(0, str(desde))
                self.ent_hasta.delete(0, 'end'); self.ent_hasta.insert(0, str(hasta))
        else:
            self.ent_desde.delete(0, 'end'); self.ent_desde.insert(0, str(desde))
            self.ent_hasta.delete(0, 'end'); self.ent_hasta.insert(0, str(hasta))

    def _apply_filters(self):
        # apply date filters and reload all selected analyses
        self._load_all_selected()

    def _volver_inicio(self):
        try:
            self.controller.mostrar_inicio()
        except Exception:
            pass
