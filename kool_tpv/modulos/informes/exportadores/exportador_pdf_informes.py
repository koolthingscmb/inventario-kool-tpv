"""Exportador de informes a PDF."""
import logging
from datetime import datetime
from pathlib import Path
from tkinter import filedialog
from typing import Dict, Any, Optional
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from kool_tpv.base_datos.configuracion_repository import ConfiguracionRepository
from kool_tpv.utils.font_loader import load_font_config

logger = logging.getLogger(__name__)
ASSETS_DIR = Path(__file__).resolve().parents[4] / 'assets'
CLAVES = {'informes_pdf_titulo': 'INFORME', 'informes_pdf_color_primario': '#1F6AA5', 'informes_pdf_mostrar_logo': '0', 'logo_pdf_filename': ''}

class ExportadorPDFInformes:
    def __init__(self, db):
        self.db = db
        self.config_repo = ConfiguracionRepository(db)
        self._cargar_plantilla()
        font_cfg = load_font_config()
        raw = font_cfg.get('default', {}).get('family', 'Courier')
        self.font_family = {'Courier New': 'Courier', 'Arial': 'Helvetica'}.get(raw, raw)
        if ' ' in self.font_family:
            self.font_family = 'Courier'

    def _cargar_plantilla(self):
        try:
            cfg = self.config_repo.obtener_multiples(list(CLAVES.keys()))
        except Exception:
            cfg = {}
        self.titulo = cfg.get('informes_pdf_titulo', CLAVES['informes_pdf_titulo'])
        self.color = cfg.get('informes_pdf_color_primario', CLAVES['informes_pdf_color_primario'])
        self.mostrar_logo = cfg.get('informes_pdf_mostrar_logo', '0') == '1'
        logo_file = cfg.get('logo_pdf_filename', '')
        logo_path = ASSETS_DIR / logo_file if logo_file else None
        self.logo_path = logo_path if (logo_path and logo_path.exists()) else None

    def exportar(self, report_data: Dict[str, Any], parent_widget=None) -> Optional[str]:
        if not report_data:
            return None
        fecha = datetime.now().strftime('%Y%m%d_%H%M%S')
        titulo = report_data.get('title', 'informe').replace(' ', '_').replace('/', '_')
        file_path = filedialog.asksaveasfilename(
            parent=parent_widget, defaultextension=".pdf",
            filetypes=[("Archivos PDF", "*.pdf")],
            initialfile=f"{titulo}_{fecha}.pdf", title="Guardar PDF"
        )
        if not file_path:
            return None
        try:
            self._generar(file_path, report_data)
            return file_path
        except Exception:
            logger.exception("Error PDF")
            return None

    def _generar(self, filepath: str, report_data: Dict[str, Any]):
        doc = SimpleDocTemplate(filepath, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
        styles = getSampleStyleSheet()
        elements = []
        if self.mostrar_logo and self.logo_path:
            try:
                elements.append(Image(str(self.logo_path), width=4*cm, height=2*cm, kind='proportional'))
                elements.append(Spacer(1, 0.3*cm))
            except:
                pass
        ts = ParagraphStyle('T', parent=styles['Heading1'], fontSize=18, textColor=colors.HexColor(self.color), spaceAfter=12)
        elements.append(Paragraph(report_data.get('title', self.titulo), ts))
        ds = styles['Normal']
        if report_data.get('generated_at'):
            elements.append(Paragraph(f"<b>Generado:</b> {report_data['generated_at']}", ds))
        rng = report_data.get('range', {})
        if rng:
            elements.append(Paragraph(f"<b>Rango:</b> {rng.get('start', '')} → {rng.get('end', '')}", ds))
        elements.append(Spacer(1, 0.5*cm))
        self._add_items(elements, report_data.get('items', []), report_data.get('display_subformat', ''), styles)
        doc.build(elements)

    def _add_items(self, elements, items, subformat, styles):
        ns = styles['Normal']
        bs = ParagraphStyle('B', parent=styles['Normal'], fontName=f'{self.font_family}-Bold')
        grupo = None
        for item in items:
            t = item.get('tipo', '')
            n = item.get('nombre', '')
            tk, u, e = item.get('tickets', 0), item.get('uds', 0), item.get('euros', 0.0)
            if t in ('linea_grupo', 'linea_cajero'):
                if n != grupo:
                    grupo = n
                    elements.append(Spacer(1, 0.3*cm))
                    elements.append(Paragraph(f"<b>{n}:</b>", bs))
                elements.append(Paragraph(f"  {item.get('fecha', '')} - {tk} Tickets - {u} Uds: {e:.2f} €", ns))
            elif t in ('subtotal_grupo', 'subtotal_cajero'):
                elements.append(Paragraph(f"  <b>TOTAL {tk} Tickets - {u} Uds: {e:.2f} €</b>", bs))
                elements.append(Spacer(1, 0.3*cm))
            elif t == 'total_global':
                elements.append(Spacer(1, 0.3*cm))
                elements.append(Paragraph(f"<b>{n}:</b>", bs))
                elements.append(Paragraph(f"  {tk} Tickets - {u} Uds: {e:.2f} €", bs))
            elif subformat == 'daily':
                elements.append(Paragraph(f"- {n} ({tk} Tickets - {u} Uds): {e:.2f} €", ns))
            else:
                if n == 'Total Tickets':
                    elements.append(Paragraph(f"<b>{n}:</b> {u}", bs))
                else:
                    elements.append(Paragraph(f"<b>{n}:</b> {e:.2f} €", bs))
