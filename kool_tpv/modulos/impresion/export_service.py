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


class ExportService:
    """Servicio responsable de exportar cierres/tickets a disco.

    Esta clase NO maneja UI; devuelve rutas de fichero o lanza excepciones.
    """

    def __init__(self, db, out_dir: Optional[str] = None):
        self.db = db
        self.cierre_svc = CierreService(db)
        base = out_dir or os.path.join(os.getcwd(), "exports")
        self.out_dir = os.path.abspath(base)
        try:
            os.makedirs(self.out_dir, exist_ok=True)
        except Exception:
            logging.exception('No se pudo crear carpeta de exports: %s', self.out_dir)

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
                w = csv.writer(f)

                # Metadatos
                w.writerow(['campo', 'valor'])
                w.writerow(['cierre_id', cierre.get('id')])
                w.writerow(['cierre_num', cierre.get('cierre_num')])
                w.writerow(['fecha_hora', cierre.get('fecha_hora')])
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
                        w.writerow([r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8]])
                    except Exception:
                        logging.exception('Error escribiendo fila ticket en CSV')

            return path
        except Exception:
            logging.exception('Error generando CSV para cierre %s', cierre_id)
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
                w = csv.writer(f)
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
