import csv
import textwrap
import logging
import os
from typing import List, Any
from datetime import datetime

from modulos.tpv.cierre_service import CierreService
from modulos.tpv.fidelizacion_service import FidelizacionService
from modulos.almacen.producto_service import ProductoService

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

    # High-level exports that consume CierreService
    def exportar_desglose_ventas_csv(self, nombre_archivo: str, fecha_desde: str, fecha_hasta: str) -> bool:
        """Exporta un CSV con los desgloses por categoría, tipo, artículo y el IVA del periodo."""
        try:
            svc = CierreService()
            desglose = svc.desglose_ventas(fecha_desde, fecha_hasta)
            impuestos = svc.desglose_impuestos_periodo(fecha_desde, fecha_hasta)

            columnas = ['seccion', 'clave', 'qty', 'total']
            rows = []

            # categorias
            rows.append({'seccion': 'CATEGORIAS', 'clave': '', 'qty': '', 'total': ''})
            for c in desglose.get('por_categoria', []):
                rows.append({'seccion': 'CATEGORIAS', 'clave': c.get('categoria',''), 'qty': c.get('qty',0), 'total': c.get('total',0)})

            rows.append({'seccion': '', 'clave': '', 'qty': '', 'total': ''})
            rows.append({'seccion': 'TIPOS', 'clave': '', 'qty': '', 'total': ''})
            for t in desglose.get('por_tipo', []):
                rows.append({'seccion': 'TIPOS', 'clave': t.get('tipo',''), 'qty': t.get('qty',0), 'total': t.get('total',0)})

            rows.append({'seccion': '', 'clave': '', 'qty': '', 'total': ''})
            rows.append({'seccion': 'ARTICULOS', 'clave': '', 'qty': '', 'total': ''})
            for a in desglose.get('por_articulo', []):
                rows.append({'seccion': 'ARTICULOS', 'clave': a.get('nombre',''), 'qty': a.get('qty',0), 'total': a.get('total',0)})

            rows.append({'seccion': '', 'clave': '', 'qty': '', 'total': ''})
            rows.append({'seccion': 'IVA', 'clave': '', 'qty': '', 'total': ''})
            for imp in impuestos:
                rows.append({'seccion': 'IVA', 'clave': f"{imp.get('iva')}%", 'qty': imp.get('base',0), 'total': imp.get('cuota',0)})

                # Puntos
                try:
                    fid = FidelizacionService()
                    puntos = fid.desglose_puntos_periodo(fecha_desde, fecha_hasta)
                    rows.append({'seccion': '', 'clave': '', 'qty': '', 'total': ''})
                    rows.append({'seccion': 'PUNTOS', 'clave': '', 'qty': '', 'total': ''})
                    rows.append({'seccion': 'PUNTOS', 'clave': 'OTORGADOS', 'qty': '', 'total': puntos.get('puntos_otorgados',0)})
                    for c in puntos.get('clientes_otorgados', []):
                        rows.append({'seccion': 'PUNTOS', 'clave': c.get('nombre',''), 'qty': c.get('cliente_id') or '', 'total': c.get('puntos',0)})
                    rows.append({'seccion': '', 'clave': '', 'qty': '', 'total': ''})
                    rows.append({'seccion': 'PUNTOS', 'clave': 'GASTADOS', 'qty': '', 'total': puntos.get('puntos_gastados',0)})
                    for c in puntos.get('clientes_gastados', []):
                        rows.append({'seccion': 'PUNTOS', 'clave': c.get('nombre',''), 'qty': c.get('cliente_id') or '', 'total': c.get('puntos',0)})
                except Exception:
                    logger.exception('Error añadiendo desgloses de puntos al CSV')

            return self.exportar_a_csv(nombre_archivo, columnas, rows)
        except Exception:
            logger.exception('Error exportando desglose ventas a CSV')
            return False

    def exportar_desglose_ventas_pdf(self, nombre_archivo: str, fecha_desde: str, fecha_hasta: str) -> bool:
        """Exporta un PDF con los desgloses por categoría, tipo, artículo y el IVA del periodo."""
        try:
            svc = CierreService()
            desglose = svc.desglose_ventas(fecha_desde, fecha_hasta)
            impuestos = svc.desglose_impuestos_periodo(fecha_desde, fecha_hasta)

            # Build a flat table of rows with a section column
            columnas = ['Sección', 'Clave', 'Cantidad', 'Importe']
            rows = []

            rows.append(['CATEGORIAS', '', '', ''])
            for c in desglose.get('por_categoria', []):
                rows.append(['CATEGORIAS', c.get('categoria',''), str(c.get('qty',0)), f"{c.get('total',0):.2f}"])

            rows.append(['', '', '', ''])
            rows.append(['TIPOS', '', '', ''])
            for t in desglose.get('por_tipo', []):
                rows.append(['TIPOS', t.get('tipo',''), str(t.get('qty',0)), f"{t.get('total',0):.2f}"])

            rows.append(['', '', '', ''])
            rows.append(['ARTICULOS', '', '', ''])
            for a in desglose.get('por_articulo', []):
                rows.append(['ARTICULOS', a.get('nombre',''), str(a.get('qty',0)), f"{a.get('total',0):.2f}"])

            rows.append(['', '', '', ''])
            rows.append(['IVA', '', '', ''])
            for imp in impuestos:
                rows.append(['IVA', f"{imp.get('iva')}%", f"{imp.get('base',0):.2f}", f"{imp.get('cuota',0):.2f}"])

                # Puntos
                try:
                    fid = FidelizacionService()
                    puntos = fid.desglose_puntos_periodo(fecha_desde, fecha_hasta)
                    rows.append(['', '', '', ''])
                    rows.append(['PUNTOS', '', '', ''])
                    rows.append(['PUNTOS', 'OTORGADOS', '', f"{puntos.get('puntos_otorgados',0):.2f}"])
                    for c in puntos.get('clientes_otorgados', []):
                        rows.append(['PUNTOS', c.get('nombre',''), str(c.get('cliente_id') or ''), f"{c.get('puntos',0):.2f}"])
                    rows.append(['', '', '', ''])
                    rows.append(['PUNTOS', 'GASTADOS', '', f"{puntos.get('puntos_gastados',0):.2f}"])
                    for c in puntos.get('clientes_gastados', []):
                        rows.append(['PUNTOS', c.get('nombre',''), str(c.get('cliente_id') or ''), f"{c.get('puntos',0):.2f}"])
                except Exception:
                    logger.exception('Error añadiendo desgloses de puntos al PDF')

            return self.exportar_a_pdf(nombre_archivo, columnas, rows)
        except Exception:
            logger.exception('Error exportando desglose ventas a PDF')
            return False

    # Helpers for exporting artículos (UI compatibility)
    def exportar_articulos_csv(self, nombre_archivo: str = None, categorias: list = None, search: str = None, dry_run: bool = False):
        """Exporta listados de artículos. Si `dry_run` devuelve la lista de filas (sin escribir archivo).

        Cuando `dry_run` es False, `nombre_archivo` debe ser una ruta de archivo válida.
        """
        try:
            svc = ProductoService()
            # obtener hasta 10000 filas para export
            filtros = {'page': 1, 'page_size': 10000, 'search': search or '', 'categoria': (categorias[0] if categorias else '')}
            rows = svc.obtener_productos_paginados(filtros) or []

            if dry_run:
                return rows

            if not nombre_archivo:
                logger.error('No se proporcionó nombre_archivo para exportar CSV de artículos')
                return False

            # columnas visibles por defecto
            columnas = ['id', 'nombre', 'sku', 'categoria', 'proveedor', 'tipo']
            # convertir rows (dicts) a listas respetando columnas
            datos = [[r.get(c, '') for c in columnas] for r in rows]
            return self.exportar_a_csv(nombre_archivo, columnas, datos)
        except Exception:
            logger.exception('Error exportando artículos a CSV')
            return False

    def exportar_articulos_pdf(self, nombre_archivo: str = None, categorias: list = None, search: str = None, dry_run: bool = False):
        """Exporta listado de artículos a PDF. Si `dry_run` devuelve la lista de filas.
        """
        try:
            svc = ProductoService()
            filtros = {'page': 1, 'page_size': 10000, 'search': search or '', 'categoria': (categorias[0] if categorias else '')}
            rows = svc.obtener_productos_paginados(filtros) or []

            if dry_run:
                return rows

            if not nombre_archivo:
                logger.error('No se proporcionó nombre_archivo para exportar PDF de artículos')
                return False

            columnas = ['ID', 'Nombre', 'SKU', 'Categoría', 'Proveedor', 'Tipo']
            datos = []
            for r in rows:
                datos.append([str(r.get('id','')), r.get('nombre',''), r.get('sku',''), r.get('categoria',''), r.get('proveedor',''), r.get('tipo','')])

            return self.exportar_a_pdf(nombre_archivo, columnas, datos)
        except Exception:
            logger.exception('Error exportando artículos a PDF')
            return False

    # Export ventas por cajero
    def exportar_ventas_por_cajero_csv(self, nombre_archivo: str, fecha_desde: str, fecha_hasta: str) -> bool:
        try:
            svc = CierreService()
            rows = svc.ventas_por_cajero(fecha_desde, fecha_hasta) or []
            columnas = ['Cajero', 'ID del Cajero', 'Total Ventas']
            datos = []
            for r in rows:
                datos.append({'Cajero': r.get('nombre',''), 'ID del Cajero': r.get('cajero_id') or '', 'Total Ventas': f"{r.get('total_ventas',0):.2f}"})
            return self.exportar_a_csv(nombre_archivo, columnas, datos)
        except Exception:
            logger.exception('Error exportando ventas por cajero a CSV')
            return False

    def exportar_ventas_por_cajero_pdf(self, nombre_archivo: str, fecha_desde: str, fecha_hasta: str) -> bool:
        try:
            svc = CierreService()
            rows = svc.ventas_por_cajero(fecha_desde, fecha_hasta) or []
            columnas = ['Cajero', 'ID del Cajero', 'Total Ventas']
            datos = []
            for r in rows:
                datos.append([r.get('nombre',''), str(r.get('cajero_id') or ''), f"{r.get('total_ventas',0):.2f}"])
            return self.exportar_a_pdf(nombre_archivo, columnas, datos)
        except Exception:
            logger.exception('Error exportando ventas por cajero a PDF')
            return False

    def exportar_estadisticas_pdf(self, nombre_archivo: str, secciones: List[Any], fecha_desde: str = None, fecha_hasta: str = None) -> bool:
        """Exporta un PDF formateado parecido al visor de Estadísticas.

        `secciones` debe ser una lista de tuplas `(key, columnas, filas)` tal como genera `EstadisticasView._load_all_selected`.
        """
        if FPDF is None:
            logger.error('FPDF no está disponible. Instale la dependencia `fpdf2`.')
            return False

        try:
            pdf = FPDF(orientation='P', unit='mm', format='A4')
            pdf.set_auto_page_break(auto=True, margin=12)
            pdf.add_page()

            # Header
            now = datetime.now().strftime('%Y-%m-%d %H:%M')
            pdf.set_font('Courier', 'B', 12)
            pdf.cell(0, 6, f'KOOL THINGS - Generado: {now}', ln=True)
            if fecha_desde or fecha_hasta:
                fd = fecha_desde.split('T')[0] if fecha_desde else ''
                fh = fecha_hasta.split('T')[0] if fecha_hasta else ''
                pdf.cell(0, 6, f'Rango de fechas: {fd} a {fh}', ln=True)
            pdf.ln(6)

            pdf.set_font('Courier', size=10)
            row_h = 5

            for key, columns, rows in secciones:
                label = key
                try:
                    # map to human label if present
                    label = dict([('por_tipo','Por Tipo'),('por_categoria','Por Categoría'),('por_articulo','Por Artículo'),('por_cajero','Por Cajero'),('por_proveedor','Por Proveedor'),('fidelizacion','Fidelización')]).get(key, key)
                except Exception:
                    pass

                pdf.set_font('Courier', 'B', 11)
                pdf.cell(0, row_h+1, f'=== {label} ===', ln=True)
                pdf.ln(1)

                pdf.set_font('Courier', 'B', 10)
                # columns header as a single line
                header_line = '  '.join(columns) if columns else ''
                # wrap header_line safely
                char_w = pdf.get_string_width('W') or 4
                chars_per_line = max(20, int((pdf.w - pdf.l_margin - pdf.r_margin) / char_w))
                for hline in textwrap.wrap(header_line, width=chars_per_line, break_long_words=True):
                    pdf.write(row_h, hline + '\n')
                pdf.set_font('Courier', size=10)
                # draw a horizontal rule instead of a long dashed string (avoids width issues)
                try:
                    y = pdf.get_y() + (row_h / 2)
                    x1 = pdf.l_margin
                    x2 = pdf.w - pdf.r_margin
                    pdf.line(x1, y, x2, y)
                    pdf.ln(row_h)
                except Exception:
                    # fallback to a short dashed line
                    pdf.multi_cell(0, row_h, '-' * 60)

                if not rows:
                    pdf.multi_cell(0, row_h, 'No hay información disponible para este análisis en el período seleccionado.')
                    pdf.ln(3)
                    continue

                for r in rows:
                    try:
                        line = '  '.join([str(x) for x in r])
                    except Exception:
                        line = str(r)
                    # wrap line safely to avoid extremely long unbreakable words
                    char_w = pdf.get_string_width('W') or 4
                    chars_per_line = max(20, int((pdf.w - pdf.l_margin - pdf.r_margin) / char_w))
                    for sub in textwrap.wrap(line, width=chars_per_line, break_long_words=True):
                        pdf.write(row_h, sub + '\n')

                pdf.ln(4)

            # ensure directory exists
            os.makedirs(os.path.dirname(nombre_archivo) or '.', exist_ok=True)
            pdf.output(nombre_archivo)
            logger.info('PDF de estadísticas exportado correctamente: %s', nombre_archivo)
            return True
        except Exception:
            logger.exception('Error al exportar estadísticas a PDF')
            return False
