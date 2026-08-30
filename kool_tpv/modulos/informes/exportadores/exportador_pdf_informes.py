"""Exportador de informes a PDF."""
import logging
from datetime import datetime
from pathlib import Path
from tkinter import filedialog
from typing import Dict, Any, List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, HRFlowable

from kool_tpv.base_datos.configuracion_repository import ConfiguracionRepository
from kool_tpv.paths import ASSETS_DIR

logger = logging.getLogger(__name__)

CLAVES_PLANTILLA = {
    'informes_pdf_titulo': 'INFORME DE VENTAS',
    'informes_pdf_color_primario': '#1F6AA5',
    'informes_pdf_color_secundario': '#4A90A4',
    'informes_pdf_mostrar_logo': '0',
    'logo_pdf_filename': '',
}


class ExportadorPDFInformes:

    def __init__(self, db):
        self.db = db
        self.config_repo = ConfiguracionRepository(db)
        self._cargar_plantilla()

    def _cargar_plantilla(self):
        try:
            cfg = self.config_repo.obtener_multiples(list(CLAVES_PLANTILLA.keys()))
        except Exception:
            cfg = {}
        def _v(k):
            return cfg.get(k, CLAVES_PLANTILLA[k])

        self.titulo_plantilla = _v('informes_pdf_titulo')
        self.color_primario = _v('informes_pdf_color_primario')
        self.color_secundario = _v('informes_pdf_color_secundario')
        self.mostrar_logo = _v('informes_pdf_mostrar_logo') == '1'
        logo_file = _v('logo_pdf_filename')
        logo_path = ASSETS_DIR / logo_file if logo_file else None
        self.logo_path = logo_path if (logo_path and logo_path.exists()) else None
        logger.info(
            "Plantilla informes cargada: mostrar_logo=%s, logo_filename=%s",
            self.mostrar_logo, logo_file
        )

    def exportar(self, report_data: Dict[str, Any], parent_widget=None) -> Optional[str]:
        if not report_data:
            return None
        fecha = datetime.now().strftime('%Y%m%d_%H%M%S')
        titulo = report_data.get('title', 'informe').replace(' ', '_').replace('/', '_')
        file_path = filedialog.asksaveasfilename(
            parent=parent_widget,
            defaultextension=".pdf",
            filetypes=[("Archivos PDF", "*.pdf")],
            initialfile=f"{titulo}_{fecha}.pdf",
            title="Guardar PDF",
        )
        if not file_path:
            return None
        try:
            self._generar(file_path, report_data)
            return file_path
        except Exception:
            logger.exception("Error generando PDF de informe")
            return None

    # ── GENERACIÓN ────────────────────────────────────────────────────────────

    def _generar(self, filepath: str, report_data: Dict[str, Any]):
        doc = SimpleDocTemplate(
            filepath, pagesize=A4,
            rightMargin=2*cm, leftMargin=2*cm,
            topMargin=2*cm, bottomMargin=2*cm,
        )
        elements = self._build_elements(report_data)
        doc.build(elements)

    def _build_elements(self, report_data: Dict[str, Any]) -> list:
        c_primario = colors.HexColor(self.color_primario)
        c_secundario = colors.HexColor(self.color_secundario)
        styles = getSampleStyleSheet()

        style_titulo = ParagraphStyle(
            'InformeTitulo', parent=styles['Heading1'],
            fontSize=18, textColor=c_primario, spaceAfter=4,
        )
        style_meta = ParagraphStyle(
            'InformeMeta', parent=styles['Normal'],
            fontSize=9, textColor=colors.HexColor('#555555'), spaceAfter=2,
        )
        style_grupo = ParagraphStyle(
            'InformeGrupo', parent=styles['Normal'],
            fontSize=11, textColor=c_secundario, fontName='Helvetica-Bold',
            spaceBefore=8, spaceAfter=2,
        )
        style_normal = ParagraphStyle(
            'InformeNormal', parent=styles['Normal'],
            fontSize=10, textColor=colors.black,
        )
        style_destacado = ParagraphStyle(
            'InformeDestacado', parent=styles['Normal'],
            fontSize=11, textColor=c_primario, fontName='Helvetica-Bold',
            spaceBefore=6,
        )

        elements = []

        # Logo
        if self.mostrar_logo and self.logo_path:
            try:
                elements.append(Image(str(self.logo_path), width=4*cm, height=2*cm, kind='proportional'))
                elements.append(Spacer(1, 0.2*cm))
                logger.info("PDF export: logo added successfully")
            except Exception:
                logger.warning("PDF export: no se pudo cargar el logo")

        # Título del informe (del report_data, no de la plantilla)
        elements.append(Paragraph(report_data.get('title', self.titulo_plantilla), style_titulo))
        elements.append(HRFlowable(width="100%", thickness=1.5, color=c_primario, spaceAfter=4))

        # Metadatos
        generated_at = report_data.get('generated_at', '')
        if generated_at:
            elements.append(Paragraph(f"<b>Generado:</b> {generated_at}", style_meta))
        rng = report_data.get('range') or {}
        if rng:
            elements.append(Paragraph(
                f"<b>Rango:</b> {rng.get('start', '')} → {rng.get('end', '')}", style_meta
            ))
        
        # Metadatos extra de Presencia
        if report_data.get('display_subformat') == 'presencia':
            u = report_data.get('usuario_header', 'TODOS')
            regs = report_data.get('total_registros', 0)
            tiempo = report_data.get('total_tiempo', '0h 0m')
            elements.append(Paragraph(f"<b>USUARIO:</b> {u}", style_meta))
            elements.append(Paragraph(f"<b>Total Registros:</b> {regs}", style_meta))
            elements.append(Paragraph(f"<b>Tiempo Total Acumulado:</b> {tiempo}", style_meta))

        elements.append(Spacer(1, 0.4*cm))

        # Cuerpo según secciones (nuevo formato pro) o subformato (formato antiguo)
        sections = report_data.get('sections')
        subformat = report_data.get('display_subformat', '')
        items = report_data.get('items', [])

        if sections:
            self._add_sections(elements, sections, style_normal, style_destacado, c_primario, c_secundario)
        elif subformat in ('cajero', 'categoria', 'tipo', 'producto'):
            self._add_items_grupo(elements, items, style_grupo, style_normal, style_destacado, c_primario, c_secundario)
        elif subformat == 'daily':
            self._add_items_daily(elements, items, style_normal, style_destacado, c_primario)
        elif subformat == 'presencia':
            self._add_items_presencia(elements, items, style_normal, style_destacado, c_primario)
        else:
            self._add_items_resumen(elements, items, style_normal, style_destacado, c_primario)

        return elements

    # ── NUEVO FORMATO POR SECCIONES ──────────────────────────────────────────

    def _add_sections(self, elements, sections, style_normal, style_destacado, c_primario, c_secundario):
        """Renderiza una lista de secciones genéricas (summary, table, blocks)."""
        for section in sections:
            sec_type = section.get('type')
            
            if sec_type == 'summary':
                self._add_section_summary(elements, section, c_primario)
            elif sec_type == 'table':
                self._add_section_table(elements, section, c_primario)
            elif sec_type == 'blocks':
                self._add_section_blocks(elements, section, c_primario, c_secundario)
            
            elements.append(Spacer(1, 0.5*cm))

    def _add_section_summary(self, elements, section, c_primario):
        headers = section.get('headers', [])
        rows = section.get('rows', [])
        if not rows: return
        
        vals = rows[0]
        filas = []
        for i, h in enumerate(headers):
            val = vals[i] if i < len(vals) else ''
            filas.append([Paragraph(f"<b>{h}:</b>", style=ParagraphStyle('summary_lbl', fontSize=10)), str(val)])
            
        t = Table(filas, colWidths=[6*cm, 8*cm])
        t.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(t)

    def _add_section_table(self, elements, section, c_primario):
        title = section.get('title')
        if title:
            elements.append(Paragraph(title, ParagraphStyle('table_title', fontSize=11, fontName='Helvetica-Bold', spaceAfter=6)))
            
        headers = section.get('headers', [])
        rows = section.get('rows', [])
        
        # Preparar datos de la tabla
        data = [headers] + rows
        
        # Calcular anchos automáticos simples (o proporcionales)
        num_cols = len(headers)
        if num_cols == 0: return
        col_width = (A4[0] - 4*cm) / num_cols
        
        t = Table(data, colWidths=[col_width]*num_cols, repeatRows=1)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), c_primario),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9F9F9')]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(t)

    def _add_section_blocks(self, elements, section, c_primario, c_secundario):
        title = section.get('title')
        if title:
            elements.append(Paragraph(title, ParagraphStyle('block_title', fontSize=12, fontName='Helvetica-Bold', textColor=c_primario, spaceAfter=8)))
            
        for block in section.get('blocks', []):
            b_title = block.get('title')
            if b_title:
                elements.append(Paragraph(b_title, ParagraphStyle('b_title', fontSize=10, fontName='Helvetica-Bold', textColor=c_secundario)))
            
            for field in block.get('fields', []):
                lbl = field.get('label', '')
                val = field.get('value', '')
                elements.append(Paragraph(f"<b>{lbl}:</b> {val}", style=ParagraphStyle('f_val', fontSize=9, leftIndent=10)))
            elements.append(Spacer(1, 0.2*cm))

    # ── SUBFORMATOS ANTIGUOS ──────────────────────────────────────────────────

    def _add_items_grupo(self, elements, items, style_grupo, style_normal, style_destacado,
                          c_primario, c_secundario):
        """Cajero / categoría / tipo / producto: grupos con líneas diarias y subtotales."""
        grupo_actual = None
        tabla_filas: List[list] = []

        def _flush_tabla():
            if not tabla_filas:
                return
            t = Table(tabla_filas, colWidths=[3.5*cm, 2.5*cm, 2*cm, 2.5*cm])
            t.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#333333')),
                ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, colors.HexColor('#F5F5F5')]),
                ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#DDDDDD')),
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
                ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]))
            elements.append(t)
            tabla_filas.clear()

        for item in items:
            t = item.get('tipo', '')
            n = item.get('nombre', '')
            tk = item.get('tickets', 0)
            u = item.get('uds', 0)
            e = item.get('euros', 0.0)

            if t in ('linea_grupo', 'linea_cajero'):
                if n != grupo_actual:
                    _flush_tabla()
                    grupo_actual = n
                    elements.append(Paragraph(f"{n}", style_grupo))
                    tabla_filas.append(['Fecha', 'Tickets', 'Uds', 'Total'])
                fecha_raw = item.get('fecha', '')
                try:
                    fecha_fmt = datetime.strptime(fecha_raw, '%Y-%m-%d').strftime('%d-%m-%Y')
                except Exception:
                    fecha_fmt = fecha_raw
                tabla_filas.append([fecha_fmt, str(tk), str(u), f"{e:.2f} €"])

            elif t in ('subtotal_grupo', 'subtotal_cajero'):
                _flush_tabla()
                sub = Table(
                    [['', f"TOTAL {tk} Tickets", f"{u} Uds", f"{e:.2f} €"]],
                    colWidths=[3.5*cm, 2.5*cm, 2*cm, 2.5*cm]
                )
                sub.setStyle(TableStyle([
                    ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
                    ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor(self.color_secundario)),
                    ('LINEABOVE', (0, 0), (-1, 0), 0.5, colors.HexColor(self.color_secundario)),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ]))
                elements.append(sub)
                elements.append(Spacer(1, 0.2*cm))

            elif t == 'total_global':
                elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor(self.color_primario), spaceBefore=6, spaceAfter=4))
                tot = Table(
                    [[f"{n}", f"{tk} Tickets", f"{u} Uds", f"{e:.2f} €"]],
                    colWidths=[3.5*cm, 2.5*cm, 2*cm, 2.5*cm]
                )
                tot.setStyle(TableStyle([
                    ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 11),
                    ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
                    ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor(self.color_primario)),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ]))
                elements.append(tot)

        _flush_tabla()

    def _add_items_daily(self, elements, items, style_normal, style_destacado, c_primario):
        """Ventas diarias: tabla fecha / tickets / uds / total."""
        if not items:
            return

        filas = [['Fecha', 'Tickets', 'Uds', 'Total']]
        total_tk = total_u = 0
        total_e = 0.0
        for item in items:
            n = item.get('nombre', '')
            try:
                fecha_fmt = datetime.strptime(n, '%Y-%m-%d').strftime('%d-%m-%Y')
            except Exception:
                fecha_fmt = n
            tk = item.get('tickets', 0)
            u = item.get('uds', 0)
            e = item.get('euros', 0.0)
            filas.append([fecha_fmt, str(tk), str(u), f"{e:.2f} €"])
            total_tk += tk
            total_u += u
            total_e += e

        filas.append(['TOTAL', str(total_tk), str(total_u), f"{total_e:.2f} €"])

        t = Table(filas, colWidths=[3.5*cm, 2.5*cm, 2*cm, 2.5*cm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(self.color_primario)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#F5F5F5')]),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#E8F0F8')),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.HexColor(self.color_primario)),
            ('LINEABOVE', (0, -1), (-1, -1), 1, colors.HexColor(self.color_primario)),
            ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#DDDDDD')),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        elements.append(t)

    def _add_items_resumen(self, elements, items, style_normal, style_destacado, c_primario):
        """Resumen de ventas: tabla concepto / valor."""
        if not items:
            return

        filas_normal = []
        item_destacado = None

        for item in items:
            n = item.get('nombre', '')
            u = item.get('uds', 0)
            e = item.get('euros', 0.0)
            t = item.get('tipo', '')

            if t == 'destacado':
                item_destacado = item
                continue

            if n == 'Total Tickets':
                filas_normal.append([n, str(u)])
            else:
                filas_normal.append([n, f"{e:.2f} €"])

        if filas_normal:
            t = Table(filas_normal, colWidths=[8*cm, 5*cm])
            t.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -2), 'Helvetica'),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
                ('TEXTCOLOR', (0, -1), (-1, -1), colors.HexColor(self.color_primario)),
                ('ROWBACKGROUNDS', (0, 0), (-1, -2), [colors.white, colors.HexColor('#F5F5F5')]),
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#E8F0F8')),
                ('LINEABOVE', (0, -1), (-1, -1), 1, colors.HexColor(self.color_primario)),
                ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#DDDDDD')),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            elements.append(t)

        if item_destacado:
            elements.append(Spacer(1, 0.4*cm))
            e = item_destacado.get('euros', 0.0)
            n = item_destacado.get('nombre', '')
            dest = Table([[f"📊  {n}", f"{e:.2f} €"]], colWidths=[8*cm, 5*cm])
            dest.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor(self.color_primario)),
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#E8F0F8')),
                ('ROUNDEDCORNERS', [4, 4, 4, 4]),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            elements.append(dest)

    def _add_items_presencia(self, elements, items, style_normal, style_destacado, c_primario):
        """Informe de Presencia: lista de líneas con formato custom."""
        if not items:
            return

        for item in items:
            fecha = item.get('fecha', '')
            t_in = item.get('entrada', '')
            t_out = item.get('salida', '')
            dur = item.get('duracion', '')
            est = item.get('estado', '')
            nota = item.get('notas', '')
            
            line = f"<b>{fecha}</b>=> IN: {t_in} OUT: {t_out} TIME: {dur} = {est}"
            elements.append(Paragraph(line, style_normal))
            
            if nota:
                elements.append(Paragraph(f"&nbsp;&nbsp;&nbsp;&nbsp;<i>NOTA: {nota}</i>", style_normal))
            
            elements.append(Spacer(1, 0.15*cm))
