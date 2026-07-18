"""Service layer para los informes de Producción.

Se encarga de transformar los datos del repositorio en el formato
que esperan la vista y los exportadores (headers, items, títulos).
Utiliza money_adapter para la conversión de céntimos a euros.
"""
import logging
from typing import List, Dict, Any
from datetime import datetime

from kool_tpv.modulos.produccion.repositories.produccion_informes_repository import ProduccionInformesRepository
from kool_tpv.base_datos.money_adapter import read_from_db


class ProduccionInformesService:
    """Service para el módulo de Informes de Producción."""

    def __init__(self, db):
        self.db = db
        self.repo = ProduccionInformesRepository(db)

    def _ahora_formateado(self) -> str:
        """Fecha y hora actual formateada para mostrar."""
        return datetime.now().strftime('%d/%m/%Y %H:%M')

    def _get_base_report(self, title: str, fi: str = None, ff: str = None) -> dict:
        """Estructura base para todos los informes."""
        report = {
            "title": title,
            "generated_at": self._ahora_formateado(),
            "sections": []
        }
        if fi and ff:
            report["range"] = {"start": fi, "end": ff}
        return report

    # ── 1. RESUMEN DE PRODUCCIÓN ─────────────────────────────────────────────

    def get_informe_resumen_produccion(self, fecha_inicio: str, fecha_fin: str) -> dict:
        """Informe resumen de actividad de producción."""
        data = self.repo.get_resumen_produccion(fecha_inicio, fecha_fin)
        report = self._get_base_report(f"RESUMEN DE PRODUCCIÓN", fecha_inicio, fecha_fin)
        
        coste_total = read_from_db(data['coste_total'])
        coste_medio = read_from_db(data['coste_total'] / data['total_unidades']) if data['total_unidades'] > 0 else 0.0

        # Sección de Resumen
        report["sections"].append({
            "type": "summary",
            "headers": ["Total Órdenes", "Total Unidades", "Coste Total", "Coste Medio"],
            "rows": [[data['total_ordenes'], data['total_unidades'], f"{coste_total:.2f} €", f"{coste_medio:.2f} €"]]
        })

        # Sección de Tabla de Estados
        items = [[e['estado'], e['num_ordenes'], e['unidades']] for e in data['estados']]
        report["sections"].append({
            "type": "table",
            "title": "Desglose por Estado",
            "headers": ["Estado", "Num. Órdenes", "Unidades"],
            "rows": items
        })
        
        # Para compatibilidad con el visor de texto actual
        report["titulo"] = report["title"]
        report["fecha_generacion"] = report["generated_at"]
        report["resumen"] = {"Órdenes": data['total_ordenes'], "Unidades": data['total_unidades'], "Coste": f"{coste_total:.2f} €"}
        report["headers"] = ["Estado", "Órdenes", "Unidades"]
        report["items"] = items
        
        return report

    # ── 2. PRODUCCIÓN POR TIPO ───────────────────────────────────────────────

    def get_informe_produccion_por_tipo(self, fecha_inicio: str, fecha_fin: str) -> dict:
        """Informe de unidades y costes por tipo de producto."""
        data = self.repo.get_produccion_por_tipo(fecha_inicio, fecha_fin)
        report = self._get_base_report(f"PRODUCCIÓN POR TIPO", fecha_inicio, fecha_fin)
        
        total_uds = sum(r['unidades'] for r in data)
        total_coste = sum(r['coste_total'] for r in data)

        report["sections"].append({
            "type": "summary",
            "headers": ["Total Tipos", "Total Unidades", "Coste Total"],
            "rows": [[len(data), total_uds, f"{read_from_db(total_coste):.2f} €"]]
        })

        rows = []
        for r in data:
            rows.append([r['tipo'], r['unidades'], f"{read_from_db(r['coste_total']):.2f} €", r['num_ordenes']])

        report["sections"].append({
            "type": "table",
            "headers": ["Tipo Producto", "Unidades", "Coste Total", "Num. Órdenes"],
            "rows": rows
        })

        # Compatibilidad visor
        report["titulo"] = report["title"]
        report["fecha_generacion"] = report["generated_at"]
        report["resumen"] = {"Unidades": total_uds, "Coste": f"{read_from_db(total_coste):.2f} €"}
        report["headers"] = ["Tipo", "Uds", "Coste", "Órdenes"]
        report["items"] = rows
        return report

    # ── 3. PRODUCCIÓN DE DISEÑOS ─────────────────────────────────────────────

    def get_informe_produccion_detallada_disenos(self, fecha_inicio: str, fecha_fin: str,
                                              coleccion_ids: list = None,
                                              sufijo_ids: list = None) -> dict:
        """Informe detallado de producción de diseños por variante y método."""
        data = self.repo.get_produccion_detallada_disenos(fecha_inicio, fecha_fin, coleccion_ids, sufijo_ids)
        report = self._get_base_report(f"PRODUCCIÓN DE DISEÑOS", fecha_inicio, fecha_fin)
        
        total_uds = sum(r['unidades'] for r in data)
        total_coste = sum(r['coste_total'] for r in data)

        report["sections"].append({
            "type": "summary",
            "headers": ["Total Registros", "Total Unidades", "Coste Total"],
            "rows": [[len(data), total_uds, f"{read_from_db(total_coste):.2f} €"]]
        })

        rows = []
        for r in data:
            fecha_raw = r.get('fecha', '')
            fecha_str = '-'
            if fecha_raw:
                try:
                    dt = datetime.strptime(str(fecha_raw)[:19], '%Y-%m-%d %H:%M:%S')
                    fecha_str = dt.strftime('%d/%m/%y')
                except Exception:
                    fecha_str = str(fecha_raw)[:10]
            rows.append([
                r['coleccion'],
                r['sufijo'],
                r['diseno_nombre'],
                r['tipo_nombre'],
                r['variante'],
                r['talla'],
                r['color'],
                r['metodo'],
                r['unidades'],
                f"{read_from_db(r['coste_total']):.2f} €",
                fecha_str,
                r.get('usuario', '-')
            ])

        report["sections"].append({
            "type": "table",
            "headers": ["Colección", "Sufijo", "Diseño", "Tipo", "Variante", "Talla", "Color", "Impresión", "Uds", "Coste", "Fecha", "Usuario"],
            "rows": rows
        })

        # Compatibilidad visor
        report["titulo"] = report["title"]
        report["fecha_generacion"] = report["generated_at"]
        report["resumen"] = {"Unidades": total_uds, "Coste Total": f"{read_from_db(total_coste):.2f} €"}
        report["headers"] = ["Colección", "Sufijo", "Diseño", "Tipo", "Variante", "Talla", "Color", "Impresión", "Uds", "Coste", "Fecha", "Usuario"]
        report["items"] = rows
        return report
