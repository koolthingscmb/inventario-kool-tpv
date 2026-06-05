"""Servicio de impresión de albaranes."""
import logging
import os
import platform
import subprocess
import tempfile
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
)

from kool_tpv.base_datos.configuracion_service import ConfiguracionService
from kool_tpv.utils.config_loader import load_colors
from kool_tpv.utils.font_loader import load_font_config
from .logica_busqueda import BusquedaService

logger = logging.getLogger(__name__)


class ImpresionService:
    """Servicio para imprimir albaranes."""

    def __init__(self, db):
        self.db = db
        self.busqueda_service = BusquedaService(db)
        self.config_service = ConfiguracionService(db) if db else None
        
        # Cargar configuraciones
        self.colors = load_colors('almacen')
        self.fonts = load_font_config()
        self.color_primary = self.colors.get('info', '#3498db')
        self.font_family = 'Courier'

    def imprimir_albaranes(
        self,
        albaran_ids: List[int],
        parent_widget=None
    ) -> bool:
        """Imprimir albaranes seleccionados.

        Args:
            albaran_ids: Lista de IDs de albaranes a imprimir
            parent_widget: Widget padre (no usado directamente, pero para compatibilidad)

        Returns:
            True si se envió a imprimir correctamente
        """
        if not albaran_ids:
            logger.warning("No hay albaranes para imprimir")
            return False

        try:
            # Generar PDF temporal con los albaranes
            pdf_path = self._generar_pdf_temporal(albaran_ids)
            
            if not pdf_path:
                logger.error("No se pudo generar PDF temporal para impresión")
                return False

            # Enviar a impresora según el sistema operativo
            success = self._enviar_a_impresora(pdf_path)
            
            if success:
                logger.info(f"Albaranes {albaran_ids} enviados a imprimir")
            
            return success

        except Exception:
            logger.exception("Error imprimiendo albaranes")
            return False

    def _generar_pdf_temporal(self, albaran_ids: List[int]) -> Optional[str]:
        """Generar PDF temporal para imprimir.

        Args:
            albaran_ids: Lista de IDs de albaranes

        Returns:
            Ruta del PDF temporal o None si falló
        """
        try:
            # Crear archivo temporal
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            temp_dir = tempfile.gettempdir()
            pdf_path = os.path.join(temp_dir, f"albaranes_imprimir_{timestamp}.pdf")

            # Generar PDF con múltiples albaranes
            doc = SimpleDocTemplate(
                pdf_path,
                pagesize=A4,
                rightMargin=1.5*cm,
                leftMargin=1.5*cm,
                topMargin=1.5*cm,
                bottomMargin=1.5*cm
            )

            elements = []
            styles = getSampleStyleSheet()

            # Por cada albarán
            for i, alb_id in enumerate(albaran_ids):
                albaran = self._get_albaran_completo(alb_id)
                if not albaran:
                    continue

                # Nueva página después del primero
                if i > 0:
                    elements.append(Spacer(1, 20))

                # Cabecera del albarán
                self._add_cabecera_albaran(elements, styles, albaran)

                # Tabla de líneas
                lineas = albaran.get('lineas', [])
                if lineas:
                    self._add_tabla_lineas(elements, lineas)

            if not elements:
                logger.warning("No hay contenido para imprimir")
                return None

            doc.build(elements)
            return pdf_path

        except Exception:
            logger.exception("Error generando PDF temporal")
            return None

    def _get_albaran_completo(self, albaran_id: int) -> Optional[Dict[str, Any]]:
        """Obtener albarán con sus líneas."""
        try:
            from kool_tpv.base_datos.albaran_service import AlbaranService
            service = AlbaranService(self.db)
            detalle = service.get_albaran_detalle(albaran_id)
            if not detalle:
                return None
            albaran = detalle['albaran']
            albaran['lineas'] = detalle['lines']
            return albaran
        except Exception:
            logger.exception(f"Error obteniendo albarán {albaran_id}")
            return None

    def _add_cabecera_albaran(self, elements, styles, albaran: Dict[str, Any]):
        """Añadir cabecera de albarán al PDF."""
        # Título
        title_style = ParagraphStyle(
            'AlbaranTitle',
            parent=styles['Heading1'],
            fontSize=14,
            textColor=colors.HexColor(self.color_primary),
            spaceAfter=8
        )
        elements.append(Paragraph(
            f"Albarán Nº {albaran.get('num_albaran', '')}",
            title_style
        ))

        # Datos básicos
        data_style = styles['Normal']
        elements.append(Paragraph(f"<b>Fecha:</b> {albaran.get('fecha', '')}", data_style))
        elements.append(Paragraph(f"<b>Proveedor:</b> {albaran.get('proveedor_nombre', '')}", data_style))
        elements.append(Spacer(1, 0.2*cm))

        # Totales
        total_iva = (
            albaran.get('total_iva_4', 0) +
            albaran.get('total_iva_10', 0) +
            albaran.get('total_iva_21', 0)
        )
        totales_data = [
            ['Base', 'IVA', 'Total'],
            [
                f"{albaran.get('total_neto', 0):.2f} €",
                f"{total_iva:.2f} €",
                f"{albaran.get('total', 0):.2f} €"
            ]
        ]
        totales_table = Table(totales_data, colWidths=[4*cm, 4*cm, 4*cm])
        totales_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), f'{self.font_family}-Bold'),
            ('FONTNAME', (0, 1), (-1, 1), self.font_family),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(self.color_primary)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
        ]))
        elements.append(totales_table)
        elements.append(Spacer(1, 0.3*cm))

    def _add_tabla_lineas(self, elements, lineas: List[Dict[str, Any]]):
        """Añadir tabla de líneas."""
        headers = ['Producto', 'Cant.', 'Precio', 'Total']
        data = [headers]

        for linea in lineas:
            data.append([
                linea.get('nombre', '')[:30],
                str(linea.get('cantidad', 0)),
                f"{linea.get('coste', 0):.2f}",
                f"{linea.get('importe', 0):.2f}"
            ])

        table = Table(data, colWidths=[6*cm, 1.5*cm, 2*cm, 2*cm])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), f'{self.font_family}-Bold'),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(self.color_primary)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('FONTNAME', (0, 1), (-1, -1), self.font_family),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 0.3*cm))

    def _enviar_a_impresora(self, pdf_path: str) -> bool:
        """Enviar PDF a la impresora según sistema operativo.

        Args:
            pdf_path: Ruta del archivo PDF

        Returns:
            True si se envió correctamente
        """
        system = platform.system()

        try:
            if system == 'Darwin':  # macOS
                return self._imprimir_macos(pdf_path)
            elif system == 'Windows':
                return self._imprimir_windows(pdf_path)
            elif system == 'Linux':
                return self._imprimir_linux(pdf_path)
            else:
                logger.error(f"Sistema operativo no soportado: {system}")
                return False

        except Exception:
            logger.exception(f"Error enviando a impresora en {system}")
            return False

    def _imprimir_macos(self, pdf_path: str) -> bool:
        """Imprimir en macOS usando lp."""
        try:
            # Usar lp (Line Printer) para enviar a impresora predeterminada
            result = subprocess.run(
                ['lp', pdf_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                logger.info(f"Enviado a impresora macOS: {result.stdout}")
                return True
            else:
                logger.error(f"Error lp: {result.stderr}")
                # Fallback: abrir con Preview
                subprocess.run(['open', '-a', 'Preview', pdf_path], check=False)
                return True
                
        except Exception:
            logger.exception("Error imprimiendo en macOS")
            return False

    def _imprimir_windows(self, pdf_path: str) -> bool:
        """Imprimir en Windows."""
        try:
            # Intentar usar sumatraPDF si está instalado (silencioso)
            sumatra_paths = [
                r"C:\Program Files\SumatraPDF\SumatraPDF.exe",
                r"C:\Program Files (x86)\SumatraPDF\SumatraPDF.exe",
            ]
            
            for sumatra_path in sumatra_paths:
                if os.path.exists(sumatra_path):
                    subprocess.run(
                        [sumatra_path, '-print-to-default', pdf_path],
                        check=True,
                        timeout=30
                    )
                    logger.info("Enviado a impresora con SumatraPDF")
                    return True

            # Fallback: abrir con aplicación predeterminada
            os.startfile(pdf_path, 'print')
            return True

        except Exception:
            logger.exception("Error imprimiendo en Windows")
            return False

    def _imprimir_linux(self, pdf_path: str) -> bool:
        """Imprimir en Linux usando lp."""
        try:
            result = subprocess.run(
                ['lp', pdf_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                logger.info(f"Enviado a impresora Linux: {result.stdout}")
                return True
            else:
                logger.error(f"Error lp: {result.stderr}")
                return False

        except Exception:
            logger.exception("Error imprimiendo en Linux")
            return False
