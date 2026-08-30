"""ExportService: exportar cierres/tickets a CSV y PDF.

Colocado en `kool_tpv/modulos/impresion/` porque está relacionado con salida/impresión.

Notas:
- `export_cierre_csv` usa la stdlib `csv` y escribe metadatos + filas de tickets.
- `export_cierre_pdf` usa `reportlab` si está instalado; si no, lanza RuntimeError indicando la dependencia.
"""
from __future__ import annotations

import os
import csv
import json
import logging
from datetime import datetime
from typing import Optional, List

from kool_tpv.base_datos.cierre_service import CierreService
from kool_tpv.base_datos.configuracion_repository import ConfiguracionRepository


class ExportService:
    """Servicio responsable de exportar cierres/tickets a disco.

    Esta clase NO maneja UI; devuelve rutas de fichero o lanza excepciones.
    """

    def __init__(self, db, out_dir: Optional[str] = None):
        self.db = db
        self.cierre_svc = CierreService(db)
        self.config_repo = ConfiguracionRepository(db)
        base = out_dir or os.path.join(os.getcwd(), "exports")
        self.out_dir = os.path.abspath(base)
        try:
            os.makedirs(self.out_dir, exist_ok=True)
        except Exception:
            logging.exception('No se pudo crear carpeta de exports: %s', self.out_dir)

    def _obtener_plantilla_informes(self) -> dict:
        """Carga la configuración de plantilla para informes desde la BD."""
        try:
            claves = [
                'informes_pdf_titulo',
                'informes_pdf_color_primario',
                'informes_pdf_color_secundario',
                'informes_pdf_mostrar_logo',
                'logo_pdf_filename',
            ]
            cfg = self.config_repo.obtener_multiples(claves)
            result = {
                'titulo': cfg.get('informes_pdf_titulo', 'INFORME DE VENTAS'),
                'color_primario': cfg.get('informes_pdf_color_primario', '#1F6AA5'),
                'color_secundario': cfg.get('informes_pdf_color_secundario', '#4A90A4'),
                'mostrar_logo': cfg.get('informes_pdf_mostrar_logo', '0') == '1',
                'logo_filename': cfg.get('logo_pdf_filename', ''),
            }
            logging.info('Plantilla informes cargada: mostrar_logo=%s, logo_filename=%s', result['mostrar_logo'], result['logo_filename'])
            return result
        except Exception:
            logging.exception('Error cargando plantilla de informes')
            return {
                'titulo': 'INFORME DE VENTAS',
                'color_primario': '#1F6AA5',
                'color_secundario': '#4A90A4',
                'mostrar_logo': False,
                'logo_filename': '',
            }

    def _timestamped_path(self, base_name: str, ext: str) -> str:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe = base_name.replace(' ', '_')
        fn = f"{safe}_{ts}.{ext.lstrip('.')}"
        return os.path.join(self.out_dir, fn)

    def export_cierre_csv(self, cierre_id: int, path: Optional[str] = None) -> str:
        """Exporta un cierre a CSV. Devuelve la ruta generada.

        CSV contiene primero metadatos del cierre y luego una sección "tickets"
        con filas por cada ticket marcado con `cierre_id`.
        """
        cierre = self.cierre_svc.obtener_cierre_por_id(cierre_id)
        if cierre is None:
            raise ValueError(f'Cierre id={cierre_id} no encontrado')

        if path is None:
            path = self._timestamped_path(f"cierre_{cierre.get('cierre_num') or cierre_id}", "csv")

        try:
            tickets = self.db.fetch_all(
                'SELECT id, num_ventas, total, importe_efectivo, importe_tarjeta, forma_pago, descuento_euros, cajero, created_at FROM tickets WHERE cierre_id = ?',
                (cierre_id,)
            )
        except Exception:
            logging.exception('Error cargando tickets para export CSV')
            tickets = []

        try:
            with open(path, 'w', newline='', encoding='utf-8') as f:
                w = csv.writer(f, delimiter=';', quoting=csv.QUOTE_MINIMAL)

                # Metadatos
                w.writerow(['campo', 'valor'])
                w.writerow(['cierre_id', cierre.get('id')])
                w.writerow(['cierre_num', cierre.get('cierre_num')])
                try:
                    from kool_tpv.utils.time_utils import utc_str_to_local_str
                    fh = utc_str_to_local_str(cierre.get('fecha_hora'))
                except Exception:
                    fh = cierre.get('fecha_hora')
                w.writerow(['fecha_hora', fh])
                w.writerow(['cajero', cierre.get('cajero')])
                w.writerow(['total_ingresos', cierre.get('total_ingresos')])
                w.writerow(['num_ventas', cierre.get('num_ventas')])
                w.writerow(['total_descuentos', cierre.get('total_descuentos')])
                w.writerow(['iva_desglose', json.dumps(cierre.get('iva_desglose') or {}, ensure_ascii=False)])

                # Sección tickets
                w.writerow([])
                w.writerow(['tickets'])
                header = ['id', 'num_ventas', 'total', 'importe_efectivo', 'importe_tarjeta', 'forma_pago', 'descuento_euros', 'cajero', 'created_at']
                w.writerow(header)
                for r in tickets or []:
                    try:
                        try:
                            from kool_tpv.utils.time_utils import utc_str_to_local_str
                            created = utc_str_to_local_str(r[8])
                        except Exception:
                            created = r[8]
                        w.writerow([r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], created])
                    except Exception:
                        logging.exception('Error escribiendo fila ticket en CSV')

            return path
        except Exception:
            logging.exception('Error generando CSV para cierre %s', cierre_id)
            raise

    def export_informe_ventas_csv(self, resumen: dict, ventas_diarias: list,
                                   fecha_inicio: str, fecha_fin: str,
                                   path: str) -> str:
        """Exporta un informe de ventas (resumen + ventas_diarias) a CSV.

        - `resumen`: dict con claves total_tickets, total_ventas, total_base, total_iva, ticket_medio
        - `ventas_diarias`: lista de dicts con claves 'fecha' y 'total'
        - `fecha_inicio`/`fecha_fin`: strings en formato YYYY-MM-DD
        - `path`: ruta completa donde escribir el CSV (sobrescribe si existe)

        Devuelve la ruta escrita.
        """
        try:
            # Ensure path directory exists
            dirp = os.path.dirname(path) or self.out_dir
            try:
                os.makedirs(dirp, exist_ok=True)
            except Exception:
                pass

            with open(path, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f, delimiter=';', quoting=csv.QUOTE_MINIMAL)

                # Metadata
                writer.writerow(['Informe de Ventas'])
                writer.writerow(['Generado', datetime.now().isoformat()])
                writer.writerow(['Rango', fecha_inicio, fecha_fin])
                writer.writerow([])

                # Resumen
                writer.writerow(['Resumen'])
                writer.writerow(['Total tickets', resumen.get('total_tickets')])
                writer.writerow(['Total ventas', resumen.get('total_ventas')])
                writer.writerow(['Base imponible', resumen.get('total_base')])
                writer.writerow(['Total IVA', resumen.get('total_iva')])
                writer.writerow(['Ticket medio', resumen.get('ticket_medio')])
                writer.writerow([])

                # Ventas por dia
                writer.writerow(['Ventas por día'])
                writer.writerow(['Fecha', 'Total'])
                for item in ventas_diarias or []:
                    try:
                        writer.writerow([item.get('fecha'), item.get('total')])
                    except Exception:
                        logging.exception('Error escribiendo fila en export_informe_ventas_csv')

            return path
        except Exception:
            logging.exception('Error generando CSV para informe de ventas en %s', path)
            raise

    def export_report_csv(self, report_data: dict, path: str) -> str:
        """Export a generic report structure to CSV.

        The `report_data` is expected to be a dict with optional keys:
        - title: str
        - generated_at: str
        - range: dict with 'start' and 'end'
        - sections: list of sections where each section may contain
          'title', 'headers' (list) and 'rows' (list of lists)

        This method writes values as-is (no formatting) and does not add currency symbols.
        It will create parent directories for `path` if necessary and return the written path.
        """
        try:
            # Ensure parent dir exists
            dirp = os.path.dirname(path) or self.out_dir
            try:
                os.makedirs(dirp, exist_ok=True)
            except Exception:
                pass

            # Write directly so we can apply per-section formatting (e.g. money columns)
            try:
                with open(path, mode="w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f, delimiter=';', quoting=csv.QUOTE_MINIMAL)

                    # Metadata
                    writer.writerow([report_data.get("title", "")])
                    generated_at = report_data.get("generated_at")
                    if generated_at:
                        writer.writerow(["Generado", generated_at])

                    rango = report_data.get("range", {}) or {}
                    if rango:
                        writer.writerow(["Rango inicio", rango.get("start")])
                        writer.writerow(["Rango fin", rango.get("end")])

                    writer.writerow([])

                    # Sections
                    for section in report_data.get("sections", []) or []:
                        try:
                            # Title for the section
                            if section.get("title"):
                                writer.writerow([section.get("title")])

                            section_type = section.get("type")

                            if section_type == "blocks":
                                # Prefer analytic export_table if provided
                                export_table = section.get("export_table")

                                if export_table:
                                    if section.get("title"):
                                        writer.writerow([section["title"]])

                                    headers = export_table.get("headers", []) or []
                                    rows = export_table.get("rows", []) or []
                                    money_columns = export_table.get("money_columns", []) or []

                                    if headers:
                                        writer.writerow(headers)

                                    for row in rows:
                                        try:
                                            processed_row = []
                                            for col_index, value in enumerate(row):
                                                if col_index in money_columns:
                                                    try:
                                                        processed_row.append(f"{float(value):.2f}")
                                                    except Exception:
                                                        processed_row.append(value)
                                                else:
                                                    processed_row.append(value)
                                            writer.writerow(processed_row)
                                        except Exception:
                                            logging.exception('Error escribiendo fila en export_table de blocks')

                                    writer.writerow([])
                                else:
                                    # Fallback: convertir blocks a tabla horizontal
                                    blocks = section.get("blocks", []) or []
                                    if blocks:
                                        # Extract headers from first block's fields
                                        first_block = blocks[0]
                                        fields = first_block.get("fields", []) or []

                                        headers = ["Cajero"] + [f.get("label") for f in fields]
                                        writer.writerow(headers)

                                        for block in blocks:
                                            block_title = block.get("title", "")
                                            block_fields = block.get("fields", []) or []

                                            row = [block_title]
                                            for field in block_fields:
                                                value = field.get("value")
                                                is_money = field.get("is_money", False)

                                                if is_money:
                                                    try:
                                                        row.append(f"{float(value):.2f}")
                                                    except Exception:
                                                        row.append(value)
                                                else:
                                                    row.append(value)

                                            writer.writerow(row)

                                    writer.writerow([])

                            else:
                                headers = section.get("headers", []) or []
                                rows = section.get("rows", []) or []

                                if headers:
                                    writer.writerow(headers)

                                # For each row, format money columns if provided in section
                                for row in rows:
                                    try:
                                        processed_row = []
                                        money_cols = section.get("money_columns", []) or []
                                        for col_index, value in enumerate(row):
                                            if col_index in money_cols:
                                                try:
                                                    processed_row.append(f"{float(value):.2f}")
                                                except Exception:
                                                    # Fallback to original value if conversion fails
                                                    processed_row.append(value)
                                            else:
                                                processed_row.append(value)
                                        writer.writerow(processed_row)
                                    except Exception:
                                        logging.exception('Error escribiendo fila en export_report_csv')

                                writer.writerow([])
                        except Exception:
                            logging.exception('Error preparando sección en export_report_csv')

                return path
            except PermissionError:
                logging.exception('PermissionError al exportar CSV a %s', path)
                raise
            except Exception:
                logging.exception('Error inesperado escribiendo CSV para report_data en %s', path)
                raise
        except Exception:
            logging.exception('Error generando CSV para report_data en %s', path)
            raise

    def export_text_to_pdf(self, text: str, path: Optional[str] = None) -> str:
        """Generar un PDF simple a partir de texto con reportlab.

        Requiere `reportlab` instalado. Devuelve ruta.
        """
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas
        except Exception:
            raise RuntimeError('Exportar a PDF requiere instalar `reportlab` (pip install reportlab)')

        if path is None:
            path = self._timestamped_path('export', 'pdf')

        try:
            c = canvas.Canvas(path, pagesize=A4)
            width, height = A4
            margin = 40
            y = height - margin
            line_h = 12
            # Support explicit page breaks using form-feed '\f' in the text.
            for raw_line in (text or '').splitlines():
                # handle page break token inside a line
                if '\f' in raw_line:
                    parts = raw_line.split('\f')
                    for i, part in enumerate(parts):
                        if part:
                            if y < margin:
                                c.showPage()
                                y = height - margin
                            c.drawString(margin, y, str(part))
                            y -= line_h
                        # after each '\f' cause a page break
                        if i != len(parts) - 1:
                            c.showPage()
                            y = height - margin
                    continue

                if y < margin:
                    c.showPage()
                    y = height - margin
                c.drawString(margin, y, str(raw_line))
                y -= line_h
            c.save()
            return path
        except Exception:
            logging.exception('Error generando PDF en %s', path)
            raise

    def export_cierre_pdf(self, cierre_id: int, path: Optional[str] = None) -> str:
        """Exporta el `cierre_text` persistido a PDF usando `reportlab`.

        Si el `cierre_text` es None o vacío, lanza ValueError.
        """
        cierre = self.cierre_svc.obtener_cierre_por_id(cierre_id)
        if cierre is None:
            raise ValueError(f'Cierre id={cierre_id} no encontrado')

        cierre_text = cierre.get('cierre_text') or ''
        if not cierre_text:
            raise ValueError('El cierre no contiene `cierre_text` para exportar')

        if path is None:
            path = self._timestamped_path(f"cierre_{cierre.get('cierre_num') or cierre_id}", 'pdf')

        return self.export_text_to_pdf(cierre_text, path=path)

    def export_cierres_csv(self, cierre_ids: List[int], path: Optional[str] = None) -> str:
        """Exportar múltiples cierres en un único CSV.

        Cada cierre se añade como un bloque con metadatos seguido de su sección de tickets.
        """
        if not cierre_ids:
            raise ValueError('No se proporcionaron ids de cierres')

        if path is None:
            path = self._timestamped_path('cierres_export', 'csv')

        try:
            with open(path, 'w', newline='', encoding='utf-8') as f:
                w = csv.writer(f, delimiter=';', quoting=csv.QUOTE_MINIMAL)
                for cid in cierre_ids:
                    cierre = self.cierre_svc.obtener_cierre_por_id(cid)
                    if cierre is None:
                        continue
                    # header for cierre
                    w.writerow(['CIERRE_ID', cierre.get('id')])
                    w.writerow(['CIERRE_NUM', cierre.get('cierre_num')])
                    w.writerow(['FECHA_HORA', cierre.get('fecha_hora')])
                    w.writerow(['CAJERO', cierre.get('cajero')])
                    w.writerow(['TOTAL_INGRESOS', cierre.get('total_ingresos')])
                    w.writerow(['NUM_VENTAS', cierre.get('num_ventas')])
                    w.writerow(['TOTAL_DESCUENTOS', cierre.get('total_descuentos')])
                    w.writerow(['IVA_DESGLOSE', json.dumps(cierre.get('iva_desglose') or {}, ensure_ascii=False)])
                    w.writerow([])
                    w.writerow(['TICKETS'])
                    header = ['id', 'num_ventas', 'total', 'importe_efectivo', 'importe_tarjeta', 'forma_pago', 'descuento_euros', 'cajero', 'created_at']
                    w.writerow(header)
                    try:
                        rows = self.db.fetch_all('SELECT id, num_ventas, total, importe_efectivo, importe_tarjeta, forma_pago, descuento_euros, cajero, created_at FROM tickets WHERE cierre_id = ?', (cid,))
                    except Exception:
                        logging.exception('Error cargando tickets para cierre %s en export CSV', str(cid))
                        rows = []
                    for r in rows or []:
                        try:
                            w.writerow([r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8]])
                        except Exception:
                            logging.exception('Error escribiendo fila ticket en export CSV')
                    # separator between cierres
                    w.writerow([])
                    w.writerow(['----'])
                    w.writerow([])
                # After all cierres, append aggregate summary
                try:
                    agg = self._compute_aggregate_for_cierres(cierre_ids)
                    w.writerow([])
                    w.writerow(['RESUMEN_AGREGADO'])
                    w.writerow(['total_ingresos', agg.get('total_ingresos')])
                    w.writerow(['total_descuentos', agg.get('total_descuentos')])
                    w.writerow(['total_devoluciones', agg.get('total_devoluciones')])
                    w.writerow(['tesoro_ganado', agg.get('tesoro_ganado')])
                    w.writerow(['tesoro_gastado', agg.get('tesoro_gastado')])
                    # IVA desglose
                    w.writerow([])
                    w.writerow(['IVA_DESGLOSE'])
                    for rate, vals in (agg.get('iva_desglose') or {}).items():
                        try:
                            w.writerow([rate, vals.get('base'), vals.get('iva')])
                        except Exception:
                            pass
                except Exception:
                    logging.exception('Error calculando resumen agregado para export CSV')

            return path
        except Exception:
            logging.exception('Error generando CSV múltiple')
            raise

    def export_cierres_pdf(self, cierre_ids: List[int], path: Optional[str] = None) -> str:
        """Exportar múltiples cierres concatenando sus `cierre_text` en un único PDF."""
        if not cierre_ids:
            raise ValueError('No se proporcionaron ids de cierres')

        texts = []
        for cid in cierre_ids:
            cierre = self.cierre_svc.obtener_cierre_por_id(cid)
            if cierre is None:
                continue
            texts.append(cierre.get('cierre_text') or f"Cierre {cierre.get('cierre_num')}")

        if not texts:
            raise ValueError('No hay texto de cierre para exportar')

        combined = '\n\f\n'.join(texts)

        # compute aggregate summary and append as a final page (use form-feed)
        try:
            agg = self._compute_aggregate_for_cierres(cierre_ids)
            summary_lines = []
            summary_lines.append('\f')
            summary_lines.append('RESUMEN AGREGADO')
            summary_lines.append('')
            summary_lines.append(f"Total ingresos: {agg.get('total_ingresos')}")
            summary_lines.append(f"Total descuentos: {agg.get('total_descuentos')}")
            summary_lines.append(f"Total devoluciones: {agg.get('total_devoluciones')}")
            summary_lines.append(f"Tesoro ganado: {agg.get('tesoro_ganado')}")
            summary_lines.append(f"Tesoro gastado: {agg.get('tesoro_gastado')}")
            summary_lines.append('')
            summary_lines.append('DESGLOSE IVA:')
            for rate, vals in (agg.get('iva_desglose') or {}).items():
                try:
                    summary_lines.append(f"Base {rate}%: {vals.get('base')}   IVA {rate}%: {vals.get('iva')}")
                except Exception:
                    pass
            combined = combined + '\n' + '\n'.join(summary_lines)
        except Exception:
            logging.exception('Error calculando resumen agregado para export PDF')
        if path is None:
            path = self._timestamped_path('cierres_export', 'pdf')

        return self.export_text_to_pdf(combined, path=path)

    def export_report_pdf(self, report_data: dict, path: str) -> str:
        """Export a generic report structure to PDF using reportlab.

        Minimal, clean PDF output built from `report_data` (title, metadata,
        sections with headers and rows). Does not perform monetary formatting.
        """
        try:
            # Local imports to avoid hard dependency at module import time
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib.units import inch
        except Exception:
            raise RuntimeError('Exportar a PDF requiere instalar `reportlab` (pip install reportlab)')

        try:
            doc = SimpleDocTemplate(path)
            elements = []

            styles = getSampleStyleSheet()

            # Cargar plantilla de informes
            plantilla = self._obtener_plantilla_informes()
            color_primario = colors.HexColor(plantilla.get('color_primario', '#1F6AA5'))
            color_secundario = colors.HexColor(plantilla.get('color_secundario', '#4A90A4'))

            # Logo si está configurado
            logging.info('PDF export: mostrar_logo=%s, logo_filename=%s', plantilla.get('mostrar_logo'), plantilla.get('logo_filename'))
            if plantilla.get('mostrar_logo'):
                try:
                    from kool_tpv.paths import ASSETS_DIR
                    logo_path = ASSETS_DIR / plantilla.get('logo_filename', '')
                    logging.info('PDF export: logo_path=%s, exists=%s', logo_path, logo_path.exists())
                    if logo_path.exists():
                        try:
                            from reportlab.platypus import Image as RLImage
                            elements.append(RLImage(str(logo_path), width=2*inch, height=1*inch))
                            elements.append(Spacer(1, 0.2 * inch))
                            logging.info('PDF export: logo added successfully')
                        except Exception:
                            logging.exception('Error añadiendo logo al PDF')
                except Exception:
                    logging.exception('Error resolviendo path del logo')

            # Title
            title = plantilla.get('titulo', report_data.get('title', ''))
            if title:
                elements.append(Paragraph(f"<b>{title}</b>", styles['Title']))
                elements.append(Spacer(1, 0.3 * inch))

            # Metadata
            generated_at = report_data.get('generated_at')
            if generated_at:
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(generated_at)
                    fecha_fmt = dt.strftime("%d/%m/%Y %H:%M")
                    elements.append(Paragraph(f"Generado: {fecha_fmt}", styles['Normal']))
                except Exception:
                    elements.append(Paragraph(f"Generado: {generated_at}", styles['Normal']))

            rango = report_data.get('range', {}) or {}
            if rango:
                elements.append(Paragraph(f"Rango: {rango.get('start')} → {rango.get('end')}", styles['Normal']))

            elements.append(Spacer(1, 0.3 * inch))

            # Sections
            sections = report_data.get('sections', []) or []
            logging.info('PDF export: %d sections found', len(sections))
            for idx, section in enumerate(sections):
                section_type = section.get('type', 'unknown')
                section_title = section.get('title', '')
                logging.info('PDF export: section[%d] type=%s title=%s', idx, section_type, section_title)

                if section.get('title'):
                    elements.append(Paragraph(f"<b>{section.get('title')}</b>", styles.get('Heading2', styles['Heading2'])))
                    elements.append(Spacer(1, 0.2 * inch))

                if section_type == 'blocks':
                    blocks = section.get('blocks', []) or []
                    logging.info('PDF export: section[%d] has %d blocks', idx, len(blocks))

                    for block in blocks:
                        block_title = block.get('title', '')
                        elements.append(Paragraph(f"<b>{block_title}</b>", styles.get('Heading3', styles['Heading3'])))

                        block_fields = block.get('fields', []) or []
                        logging.info('PDF export: block[%s] has %d fields', block_title, len(block_fields))

                        # Build vertical table for each block
                        data = []
                        for field in block_fields:
                            label = field.get('label', '')
                            value = field.get('value')
                            is_money = field.get('is_money', False)

                            if is_money:
                                try:
                                    value_str = f"{float(value):.2f} €"
                                except Exception:
                                    value_str = str(value)
                            else:
                                value_str = str(value)

                            data.append([label, value_str])

                        if not data:
                            logging.warning('PDF export: block[%s] has no data, skipping table', block_title)
                            continue

                        table = Table(data, colWidths=[3*inch, 2*inch], hAlign="LEFT")
                        table.setStyle(TableStyle([
                            ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
                            ("BACKGROUND", (0,0), (0,-1), color_primario),
                            ("FONTNAME", (0,0), (-1,-1), "Helvetica"),
                            ("FONTSIZE", (0,0), (-1,-1), 10),
                            ("ALIGN", (1,0), (1,-1), "RIGHT"),
                            ("TEXTCOLOR", (0,0), (0,-1), colors.white),
                            ("TEXTCOLOR", (1,0), (1,-1), colors.black),
                        ]))

                        elements.append(table)
                        elements.append(Spacer(1, 0.3 * inch))

                else:
                    headers = section.get('headers', []) or []
                    rows = section.get('rows', []) or []

                    data = []
                    if headers:
                        data.append(headers)

                    for row in rows:
                        # Format money columns to exactly 2 decimals when requested by section
                        money_columns = section.get("money_columns", []) or []
                        processed_row = []
                        for col_index, cell in enumerate(row):
                            if col_index in money_columns:
                                try:
                                    processed_row.append(f"{float(cell):.2f}")
                                except Exception:
                                    processed_row.append(str(cell))
                            else:
                                processed_row.append(str(cell))

                        data.append(processed_row)

                    if data:
                        table = Table(data, hAlign='LEFT')
                        table.setStyle(TableStyle([
                            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                            ('BACKGROUND', (0, 0), (-1, 0), color_secundario),
                            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                            ('FONTSIZE', (0, 0), (-1, -1), 10),
                            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
                        ]))
                        elements.append(table)
                        elements.append(Spacer(1, 0.4 * inch))

            logging.info('PDF export: %d elements to build', len(elements))
            doc.build(elements)
            return path
        except Exception:
            logging.exception('Error generando PDF para report_data en %s', path)
            raise

    def _compute_aggregate_for_cierres(self, cierre_ids: List[int]) -> dict:
        """Compute aggregated totals across multiple cierres.

        Returns keys: total_ingresos, total_descuentos, total_devoluciones,
        tesoro_ganado, tesoro_gastado, iva_desglose (dict by rate).
        """
        agg = {
            'total_ingresos': 0.0,
            'total_descuentos': 0.0,
            'total_devoluciones': 0.0,
            'tesoro_ganado': 0.0,
            'tesoro_gastado': 0.0,
            'iva_desglose': {},
        }
        try:
            for cid in cierre_ids:
                try:
                    cierre = self.cierre_svc.obtener_cierre_por_id(cid)
                    if not cierre:
                        continue
                    agg['total_ingresos'] += float(cierre.get('total_ingresos') or 0.0)
                    agg['total_descuentos'] += float(cierre.get('total_descuentos') or 0.0)
                    agg['total_devoluciones'] += float(cierre.get('total_devoluciones') or 0.0)
                    agg['tesoro_ganado'] += float(cierre.get('tesoro_ganado') or 0.0)
                    agg['tesoro_gastado'] += float(cierre.get('tesoro_gastado') or 0.0)

                    # iva_desglose may be stored as JSON string or dict
                    iva_raw = cierre.get('iva_desglose')
                    if iva_raw:
                        try:
                            if isinstance(iva_raw, str):
                                iva_obj = json.loads(iva_raw)
                            elif isinstance(iva_raw, dict):
                                iva_obj = iva_raw
                            else:
                                iva_obj = {}
                        except Exception:
                            iva_obj = {}
                        for rate, vals in (iva_obj or {}).items():
                            try:
                                r = str(rate)
                                base = float(vals.get('base', 0) if isinstance(vals, dict) else 0)
                                iva = float(vals.get('iva', 0) if isinstance(vals, dict) else 0)
                                if r not in agg['iva_desglose']:
                                    agg['iva_desglose'][r] = {'base': 0.0, 'iva': 0.0}
                                agg['iva_desglose'][r]['base'] += base
                                agg['iva_desglose'][r]['iva'] += iva
                            except Exception:
                                pass
                except Exception:
                    logging.exception('Error agregando cierre %s', str(cid))
        except Exception:
            logging.exception('Error en _compute_aggregate_for_cierres')
        return agg
