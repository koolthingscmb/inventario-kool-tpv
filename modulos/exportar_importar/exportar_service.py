import csv
import logging
import os
from typing import List, Any

logger = logging.getLogger(__name__)

try:
    from fpdf import FPDF
except Exception:
    FPDF = None


class ExportarService:
    """Servicio responsable de exportar datos a CSV y PDF."""

    def exportar_a_csv(self, nombre_archivo: str, columnas: List[str], datos: List[Any]) -> bool:
        """Exporta datos a un archivo CSV con encoding utf-8-sig y delimitador ';'.

        `datos` puede ser una lista de listas (filas) o una lista de diccionarios.
        Si son diccionarios, se seguirá el orden de `columnas`.
        """
        try:
            # asegurar que el directorio existe
            os.makedirs(os.path.dirname(nombre_archivo) or '.', exist_ok=True)
            with open(nombre_archivo, mode='w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.writer(csvfile, delimiter=';')
                writer.writerow(columnas)

                if not datos:
                    logger.info('CSV exportado (sin filas): %s', nombre_archivo)
                    return True

                # detectar si las filas son dicts
                first = datos[0]
                if isinstance(first, dict):
                    for row in datos:
                        try:
                            writer.writerow([row.get(c, '') for c in columnas])
                        except Exception:
                            logger.exception('Error escribiendo fila en CSV: %s', row)
                            # continuar con siguientes filas
                    return True

                # asumir lista/iterable de valores
                try:
                    writer.writerows(datos)
                except Exception:
                    # escribir fila a fila si writerows falla
                    for row in datos:
                        try:
                            writer.writerow(row)
                        except Exception:
                            logger.exception('Error escribiendo fila en CSV: %s', row)
                    # aunque alguna fila falle, consideramos la operación hecha
                logger.info('CSV exportado correctamente: %s', nombre_archivo)
                return True
        except Exception:
            logger.exception('Error al exportar a CSV')
            return False

    def exportar_a_pdf(self, nombre_archivo: str, columnas: List[str], datos: List[Any]) -> bool:
        """Exporta datos a un archivo PDF en formato tabla.

        Genera múltiples páginas si hay más filas de las que caben en una.
        Usa `fpdf` (fpdf2)."""
        if FPDF is None:
            logger.error('FPDF no está disponible. Instale la dependencia `fpdf2`.')
            return False

        try:
            # parámetros de página A4
            pdf = FPDF(orientation='P', unit='mm', format='A4')
            pdf.set_auto_page_break(auto=True, margin=12)

            # Preparar filas normalizadas
            normalized_rows = []
            for r in datos:
                if isinstance(r, dict):
                    normalized_rows.append([str(r.get(c, '')) for c in columnas])
                else:
                    normalized_rows.append([str(x) for x in r])

            # cálculo de layout
            page_width = pdf.w - 2 * pdf.l_margin  # ancho utilizable en mm
            page_height = pdf.h - 2 * pdf.t_margin
            min_cell_width = 22  # mínimo razonable por columna en mm
            # cuántas columnas caben por página
            max_cols_per_page = max(1, int(page_width // min_cell_width))

            # dividir columnas en chunks si son demasiadas
            ncols = len(columnas)
            col_chunks = [columnas[i:i + max_cols_per_page] for i in range(0, ncols, max_cols_per_page)]
            # rows per page (ajustar con altura y fila)
            row_height = 7
            rows_per_page = max(3, int(page_height // row_height) - 3)

            # asegurar directorio
            os.makedirs(os.path.dirname(nombre_archivo) or '.', exist_ok=True)

            for chunk_idx, chunk_cols in enumerate(col_chunks):
                # calcular ancho por columna en este chunk
                cols_in_chunk = len(chunk_cols)
                col_width = page_width / cols_in_chunk
                # determinar tamaño de fuente en función del ancho
                font_size = 10 if col_width >= 30 else (9 if col_width >= 24 else 8)
                pdf.set_font('Arial', size=font_size)

                # preparar header text max chars
                max_chars = max(6, int(col_width / 2.2))

                # paginar filas para este chunk
                for start in range(0, len(normalized_rows), rows_per_page):
                    pdf.add_page()
                    # dibujar cabecera
                    pdf.set_font('Arial', 'B', font_size)
                    for col in chunk_cols:
                        pdf.cell(col_width, row_height, txt=str(col)[:max_chars], border=1, align='C')
                    pdf.ln()
                    pdf.set_font('Arial', size=font_size)

                    # escribir filas de este bloque
                    for row in normalized_rows[start:start + rows_per_page]:
                        # seleccionar subrow correspondiente al chunk
                        # map column indices
                        row_slice = []
                        for c in chunk_cols:
                            try:
                                idx = columnas.index(c)
                                row_slice.append(row[idx])
                            except Exception:
                                row_slice.append('')

                        for cell in row_slice:
                            txt = str(cell).replace('\n', ' ')[:max_chars]
                            pdf.cell(col_width, row_height, txt=txt, border=1)
                        pdf.ln()

            pdf.output(nombre_archivo)
            logger.info('PDF exportado correctamente: %s', nombre_archivo)
            return True
        except Exception:
            logger.exception('Error al exportar a PDF')
            return False
