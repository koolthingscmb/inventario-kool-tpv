"""Exportador de albaranes a formato PDF."""
import logging
import os
from datetime import datetime
from pathlib import Path
from tkinter import filedialog
from typing import List, Dict, Any, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image as RLImage
)
from reportlab.lib.utils import ImageReader

from .logica_busqueda import BusquedaService
from kool_tpv.utils.font_loader import load_font_config

logger = logging.getLogger(__name__)


class ExportadorPDF:
    """Genera archivos PDF con datos de albaranes."""

    def __init__(self, db):
        self.db = db
        self.busqueda_service = BusquedaService(db)

        # Cargar plantilla desde BD (con defaults si no existe)
        plantilla = self.busqueda_service.obtener_plantilla_albaran()
        self.color_primary = plantilla.get('albaran_pdf_color_primario', '#1F6AA5')
        self.color_secondary = plantilla.get('albaran_pdf_color_secundario', '#4A90A4')
        self.titulo_documento = plantilla.get('albaran_pdf_titulo', 'ALBARÁN DE ENTRADA')
        self.mostrar_tienda = plantilla.get('albaran_pdf_mostrar_tienda', '1') == '1'
        self.mostrar_logo = plantilla.get('albaran_pdf_mostrar_logo', '0') == '1'

        logo_file = plantilla.get('logo_pdf_filename', '')
        assets_dir = Path(__file__).resolve().parents[5] / 'assets'
        logo_path = assets_dir / logo_file if logo_file else None
        self.logo_path = logo_path if (logo_path and logo_path.exists()) else None

        # Cargar fuente desde configuración (mapear a nombres ReportLab compatibles)
        font_cfg = load_font_config()
        default_font = font_cfg.get('default', {})
        raw_family = default_font.get('family', 'Courier')
        _reportlab_map = {
            'Courier New': 'Courier',
            'Courier': 'Courier',
            'Helvetica': 'Helvetica',
            'Arial': 'Helvetica',
            'Times New Roman': 'Times-Roman',
        }
        self.font_family = _reportlab_map.get(raw_family, raw_family)
        # Si tiene espacio y no está mapeado, fallback a Courier
        if ' ' in self.font_family:
            self.font_family = 'Courier'

    def exportar_individual(
        self,
        albaran_ids: List[int],
        incluir_cabecera_tienda: bool = False,
        parent_widget=None
    ) -> Optional[str]:
        """Exportar cada albarán en un PDF separado.

        Args:
            albaran_ids: Lista de IDs de albaranes
            incluir_cabecera_tienda: Si True, incluye datos de la tienda
            parent_widget: Widget padre para el diálogo

        Returns:
            Ruta de la carpeta donde se guardaron los PDFs
        """
        if not albaran_ids:
            logger.warning("No hay albaranes para exportar")
            return None

        # Si es un solo albarán, diálogo de guardar archivo; si son varios, seleccionar carpeta
        fecha_hora = datetime.now().strftime('%Y%m%d_%H%M%S')

        if len(albaran_ids) == 1:
            file_path = filedialog.asksaveasfilename(
                parent=parent_widget,
                defaultextension=".pdf",
                filetypes=[("Archivos PDF", "*.pdf"), ("Todos los archivos", "*.*")],
                initialfile=f"albaran_{fecha_hora}.pdf",
                title="Guardar PDF"
            )
            if not file_path:
                logger.info("Exportación PDF cancelada")
                return None
            folder = os.path.dirname(file_path)
            filepaths = {albaran_ids[0]: file_path}
        else:
            folder = filedialog.askdirectory(
                parent=parent_widget,
                title="Seleccionar carpeta para guardar PDFs"
            )
            if not folder:
                logger.info("Exportación PDF cancelada")
                return None
            filepaths = None

        try:
            for alb_id in albaran_ids:
                albaran = self._get_albaran_completo(alb_id)
                if not albaran:
                    continue

                if filepaths:
                    filepath = filepaths[alb_id]
                else:
                    filename = f"albaran_{albaran.get('num_albaran', alb_id)}_{fecha_hora}.pdf"
                    filepath = os.path.join(folder, filename)

                self._generar_pdf_albaran(
                    filepath,
                    albaran,
                    incluir_cabecera_tienda
                )

            logger.info(f"PDFs exportados en: {folder}")
            return folder

        except Exception:
            logger.exception("Error exportando PDFs individuales")
            return None

    def exportar_agrupado(
        self,
        albaran_ids: List[int],
        incluir_cabecera_tienda: bool = False,
        parent_widget=None
    ) -> Optional[str]:
        """Exportar todos los albaranes en un solo PDF agrupado por proveedor.

        Args:
            albaran_ids: Lista de IDs de albaranes
            incluir_cabecera_tienda: Si True, incluye portada con datos de tienda
            parent_widget: Widget padre para el diálogo

        Returns:
            Ruta del archivo PDF generado
        """
        if not albaran_ids:
            logger.warning("No hay albaranes para exportar")
            return None

        # Diálogo guardar
        fecha_hora = datetime.now().strftime('%Y%m%d_%H%M%S')
        default_filename = f"albaranes_agrupados_{fecha_hora}.pdf"

        file_path = filedialog.asksaveasfilename(
            parent=parent_widget,
            defaultextension=".pdf",
            filetypes=[("Archivos PDF", "*.pdf"), ("Todos los archivos", "*.*")],
            initialfile=default_filename,
            title="Guardar PDF agrupado"
        )

        if not file_path:
            logger.info("Exportación PDF agrupado cancelada")
            return None

        try:
            # Obtener albaranes completos
            albaranes = []
            for alb_id in albaran_ids:
                albaran = self._get_albaran_completo(alb_id)
                if albaran:
                    albaranes.append(albaran)

            # Agrupar por proveedor
            por_proveedor = {}
            for alb in albaranes:
                prov = alb.get('proveedor_nombre', 'Sin proveedor')
                if prov not in por_proveedor:
                    por_proveedor[prov] = []
                por_proveedor[prov].append(alb)

            # Generar PDF
            self._generar_pdf_agrupado(
                file_path,
                por_proveedor,
                incluir_cabecera_tienda
            )

            logger.info(f"PDF agrupado exportado: {file_path}")
            return file_path

        except Exception:
            logger.exception("Error exportando PDF agrupado")
            return None

    def _get_albaran_completo(self, albaran_id: int) -> Optional[Dict[str, Any]]:
        """Obtener albarán con todas sus líneas."""
        return self.busqueda_service.obtener_albaran_completo(albaran_id)

    def _build_elements_albaran(
        self,
        albaran: Dict[str, Any],
        incluir_cabecera_tienda: bool,
        styles
    ) -> list:
        """Construir lista de elements ReportLab para un albarán."""
        elements = []

        # Logo
        if self.mostrar_logo and self.logo_path:
            try:
                logo_img = RLImage(str(self.logo_path), width=4*cm, height=2*cm, kind='proportional')
                elements.append(logo_img)
                elements.append(Spacer(1, 0.3*cm))
            except Exception:
                logger.warning(f"No se pudo insertar el logo: {self.logo_path}")

        # Cabecera tienda
        if incluir_cabecera_tienda:
            self._add_cabecera_tienda(elements, styles)
            elements.append(Spacer(1, 0.5*cm))

        # Título albarán
        title_style = ParagraphStyle(
            'AlbaranTitle',
            parent=styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor(self.color_primary),
            spaceAfter=12
        )
        elements.append(Paragraph(
            f"{self.titulo_documento} Nº {albaran.get('num_albaran', '')}",
            title_style
        ))

        # Datos del albarán
        data_style = styles['Normal']
        elements.append(Paragraph(f"<b>Fecha:</b> {albaran.get('fecha', '')}", data_style))
        elements.append(Paragraph(f"<b>Proveedor:</b> {albaran.get('proveedor_nombre', '')}", data_style))
        elements.append(Spacer(1, 0.3*cm))

        # Tabla de líneas
        lineas = albaran.get('lineas', [])
        if lineas:
            self._add_tabla_lineas(elements, lineas)
            elements.append(Spacer(1, 0.5*cm))

        # Tabla de totales
        total_iva = (
            albaran.get('total_iva_4', 0) +
            albaran.get('total_iva_10', 0) +
            albaran.get('total_iva_21', 0)
        )
        totales_data = [
            ['Base Imponible', f"{albaran.get('total_neto', 0):.2f} €"],
            ['Total IVA', f"{total_iva:.2f} €"],
            ['TOTAL', f"{albaran.get('total', 0):.2f} €"]
        ]
        totales_table = Table(totales_data, colWidths=[6*cm, 4*cm])
        totales_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), self.font_family),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor(self.color_primary)),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.white),
            ('FONTNAME', (0, -1), (-1, -1), f'{self.font_family}-Bold'),
        ]))
        elements.append(totales_table)
        return elements

    def _generar_pdf_albaran(
        self,
        filepath: str,
        albaran: Dict[str, Any],
        incluir_cabecera_tienda: bool
    ):
        """Generar PDF de un solo albarán."""
        doc = SimpleDocTemplate(
            filepath,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )
        styles = getSampleStyleSheet()
        elements = self._build_elements_albaran(albaran, incluir_cabecera_tienda, styles)
        doc.build(elements)

    def _generar_pdf_agrupado(
        self,
        filepath: str,
        por_proveedor: Dict[str, List[Dict[str, Any]]],
        incluir_cabecera_tienda: bool
    ):
        """Generar PDF con todos los albaranes en un solo archivo."""
        doc = SimpleDocTemplate(
            filepath,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )
        styles = getSampleStyleSheet()
        elements = []

        first = True
        for albaranes in por_proveedor.values():
            for albaran in albaranes:
                if not first:
                    elements.append(PageBreak())
                first = False
                elements.extend(
                    self._build_elements_albaran(albaran, incluir_cabecera_tienda, styles)
                )

        doc.build(elements)

    def _add_cabecera_tienda(self, elements, styles):
        """Añadir cabecera con datos de la tienda."""
        try:
            cfg = self.busqueda_service.obtener_config_tienda()
            nombre = cfg.get('shop_name', '')
            direccion = cfg.get('fiscal_address', '')
            cif = cfg.get('fiscal_nif', '')

            title_style = ParagraphStyle(
                'TiendaTitle',
                parent=styles['Heading1'],
                fontSize=20,
                textColor=colors.HexColor(self.color_primary),
                alignment=1  # Center
            )
            elements.append(Paragraph(nombre, title_style))

            if direccion:
                elements.append(Paragraph(direccion, styles['Normal']))
            if cif:
                elements.append(Paragraph(f"CIF: {cif}", styles['Normal']))

        except Exception:
            logger.exception("Error añadiendo cabecera de tienda")

    def _add_tabla_lineas(self, elements, lineas: List[Dict[str, Any]]):
        """Añadir tabla completa de líneas."""
        wrap_style = ParagraphStyle('WrapCell', fontName=self.font_family, fontSize=9, leading=11)
        headers = ['Producto', 'Cant.', 'P.Coste', 'Total']
        data = [headers]

        for linea in lineas:
            nombre = linea.get('nombre', '') or ''
            cantidad = linea.get('cantidad', 0)
            coste = linea.get('coste', 0)
            total_linea = cantidad * coste
            data.append([
                Paragraph(nombre, wrap_style),
                str(cantidad),
                f"{coste:.2f}",
                f"{total_linea:.2f}"
            ])

        table = Table(data, colWidths=[8*cm, 1.5*cm, 2.5*cm, 3*cm])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), f'{self.font_family}-Bold'),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(self.color_primary)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('FONTNAME', (0, 1), (-1, -1), self.font_family),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(table)

