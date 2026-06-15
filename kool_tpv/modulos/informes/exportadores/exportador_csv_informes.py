"""Exportador de informes a formato CSV."""
import csv
import logging
from datetime import datetime
from tkinter import filedialog
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class ExportadorCSVInformes:
    """Genera archivos CSV con datos de informes."""

    def exportar(self, report_data: Dict[str, Any], parent_widget=None) -> Optional[str]:
        """Exportar informe a CSV.

        Args:
            report_data: Dict con los datos del informe (title, items, range, etc.)
            parent_widget: Widget padre para el diálogo de guardar

        Returns:
            Ruta del archivo generado o None si se canceló
        """
        if not report_data:
            logger.warning("No hay datos de informe para exportar")
            return None

        # Diálogo para guardar archivo
        fecha_hora = datetime.now().strftime('%Y%m%d_%H%M%S')
        titulo_limpio = report_data.get('title', 'informe').replace(' ', '_').replace('/', '_')
        default_filename = f"{titulo_limpio}_{fecha_hora}.csv"

        file_path = filedialog.asksaveasfilename(
            parent=parent_widget,
            defaultextension=".csv",
            filetypes=[("Archivos CSV", "*.csv"), ("Todos los archivos", "*.*")],
            initialfile=default_filename,
            title="Guardar CSV"
        )

        if not file_path:
            logger.info("Exportación CSV cancelada por el usuario")
            return None

        try:
            self._escribir_csv(file_path, report_data)
            logger.info(f"CSV exportado correctamente: {file_path}")
            return file_path
        except Exception:
            logger.exception("Error exportando CSV")
            return None

    def _escribir_csv(self, file_path: str, report_data: Dict[str, Any]):
        """Escribir datos del informe al archivo CSV."""
        with open(file_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f, delimiter=';', quoting=csv.QUOTE_MINIMAL)

            # Cabecera del informe
            title = report_data.get('title', 'INFORME')
            writer.writerow([title])
            writer.writerow([])

            # Metadatos
            generated_at = report_data.get('generated_at', '')
            if generated_at:
                writer.writerow(["Generado:", generated_at])

            rng = report_data.get('range', {})
            if rng:
                start = rng.get('start', '')
                end = rng.get('end', '')
                writer.writerow(["Rango:", f"{start} → {end}"])

            writer.writerow([])

            # Items del informe
            items = report_data.get('items', [])
            if items:
                # Detectar formato según tipo de items
                display_subformat = report_data.get('display_subformat', '')
                self._escribir_items(writer, items, display_subformat)

    def _escribir_items(self, writer, items: list, display_subformat: str):
        """Escribir items según el formato del informe."""
        # Headers según subformato
        if display_subformat in ('cajero', 'categoria', 'tipo', 'producto'):
            writer.writerow(["Grupo", "Fecha", "Tickets", "Uds", "Total"])
            writer.writerow([])

            grupo_actual = None
            for item in items:
                tipo_item = item.get('tipo', '')
                nombre = item.get('nombre', '')
                tickets = item.get('tickets', 0)
                uds = item.get('uds', 0)
                euros = item.get('euros', 0.0)

                if tipo_item == 'linea_grupo' or tipo_item == 'linea_cajero':
                    fecha_raw = item.get('fecha', '')
                    try:
                        fecha_fmt = datetime.strptime(fecha_raw, '%Y-%m-%d').strftime('%d-%m-%Y')
                    except Exception:
                        fecha_fmt = fecha_raw
                    if nombre != grupo_actual:
                        grupo_actual = nombre
                    writer.writerow([nombre, fecha_fmt, tickets, uds, f"{euros:.2f}"])
                elif tipo_item == 'subtotal_grupo' or tipo_item == 'subtotal_cajero':
                    writer.writerow(['TOTAL', '', tickets, uds, f"{euros:.2f}"])
                    writer.writerow([])
                elif tipo_item == 'total_global':
                    writer.writerow([nombre, '', tickets, uds, f"{euros:.2f}"])

        elif display_subformat == 'daily':
            writer.writerow(["Fecha", "Tickets", "Uds", "Total"])
            writer.writerow([])
            total_tk = total_u = 0
            total_e = 0.0
            for item in items:
                nombre = item.get('nombre', '')
                try:
                    fecha_fmt = datetime.strptime(nombre, '%Y-%m-%d').strftime('%d-%m-%Y')
                except Exception:
                    fecha_fmt = nombre
                tickets = item.get('tickets', 0)
                uds = item.get('uds', 0)
                euros = item.get('euros', 0.0)
                writer.writerow([fecha_fmt, tickets, uds, f"{euros:.2f}"])
                total_tk += tickets
                total_u += uds
                total_e += euros
            writer.writerow([])
            writer.writerow(['TOTAL', total_tk, total_u, f"{total_e:.2f}"])

        else:
            # Formato genérico (Resumen de ventas, etc.)
            writer.writerow(["Concepto", "Valor"])
            writer.writerow([])
            for item in items:
                nombre = item.get('nombre', '')
                euros = item.get('euros', 0.0)
                if nombre == 'Total Tickets':
                    uds = item.get('uds', 0)
                    writer.writerow([nombre, uds])
                else:
                    writer.writerow([nombre, f"{euros:.2f}"])
