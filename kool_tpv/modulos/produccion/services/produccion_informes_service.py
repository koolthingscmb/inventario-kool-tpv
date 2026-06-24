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

    # ── 3. PRODUCCIÓN POR DISEÑO ─────────────────────────────────────────────

    def get_informe_produccion_por_diseno(self, fecha_inicio: str, fecha_fin: str) -> dict:
        """Informe de producción desglosado por diseño."""
        data = self.repo.get_produccion_por_diseno(fecha_inicio, fecha_fin)
        report = self._get_base_report(f"PRODUCCIÓN POR DISEÑO", fecha_inicio, fecha_fin)
        
        total_uds = sum(r['unidades'] for r in data)
        report["sections"].append({"type": "summary", "headers": ["Total Diseños", "Total Unidades"], "rows": [[len(data), total_uds]]})

        rows = [[r['diseno_codigo'], r['diseno_nombre'], r['coleccion'], r['unidades'], f"{read_from_db(r['coste_total']):.2f} €"] for r in data]
        report["sections"].append({
            "type": "table",
            "headers": ["Código", "Diseño", "Colección", "Unidades", "Coste Total"],
            "rows": rows
        })

        report["titulo"] = report["title"]; report["fecha_generacion"] = report["generated_at"]
        report["resumen"] = {"Diseños": len(data), "Unidades": total_uds}
        report["headers"] = ["Código", "Diseño", "Colección", "Uds", "Coste"]; report["items"] = rows
        return report

    # ── 4. PRODUCCIÓN POR COLECCIÓN ──────────────────────────────────────────

    def get_informe_produccion_por_coleccion(self, fecha_inicio: str, fecha_fin: str) -> dict:
        """Informe de producción agrupado por colección."""
        data = self.repo.get_produccion_por_coleccion(fecha_inicio, fecha_fin)
        report = self._get_base_report(f"PRODUCCIÓN POR COLECCIÓN", fecha_inicio, fecha_fin)
        
        total_uds = sum(r['unidades'] for r in data)
        rows = [[r['coleccion'], r['unidades'], f"{read_from_db(r['coste_total']):.2f} €", r['num_disenos']] for r in data]
        
        report["sections"].append({
            "type": "table",
            "headers": ["Colección", "Unidades", "Coste Total", "Num. Diseños"],
            "rows": rows
        })

        report["titulo"] = report["title"]; report["fecha_generacion"] = report["generated_at"]
        report["resumen"] = {"Colecciones": len(data), "Unidades": total_uds}
        report["headers"] = ["Colección", "Uds", "Coste", "Diseños"]; report["items"] = rows
        return report

    # ── 5. STOCK POR TIPO ────────────────────────────────────────────────────

    def get_informe_stock_por_tipo(self) -> dict:
        """Informe de stock actual de bases por tipo."""
        data = self.repo.get_stock_por_tipo()
        report = self._get_base_report("INFORME DE STOCK POR TIPO (BASES)")
        
        total_uds = sum(r['total_unidades'] for r in data)
        valor_total = sum(r['valor_stock'] for r in data)

        report["sections"].append({
            "type": "summary",
            "headers": ["Total Unidades", "Valor Total"],
            "rows": [[total_uds, f"{read_from_db(valor_total):.2f} €"]]
        })

        rows = [[r['tipo_nombre'], r['total_unidades'], f"{read_from_db(r['valor_stock']):.2f} €", r['num_referencias']] for r in data]
        report["sections"].append({
            "type": "table",
            "headers": ["Tipo Producto", "Stock Actual", "Valor Stock", "Num. Refs"],
            "rows": rows
        })

        report["titulo"] = report["title"]; report["fecha_generacion"] = report["generated_at"]
        report["resumen"] = {"Stock Total": total_uds, "Valor Total": f"{read_from_db(valor_total):.2f} €"}
        report["headers"] = ["Tipo", "Stock", "Valor", "Refs"]; report["items"] = rows
        return report

    # ── 6. STOCK POR VARIANTE ────────────────────────────────────────────────

    def get_informe_stock_por_variante(self) -> dict:
        """Informe de stock actual de bases desglosado por variante."""
        data = self.repo.get_stock_por_variante()
        report = self._get_base_report("INFORME DE STOCK POR VARIANTE (BASES)")
        
        rows = [[r['tipo_nombre'], r['variante_nombre'], r['total_unidades'], f"{read_from_db(r['valor_stock']):.2f} €", r['num_referencias']] for r in data]
        report["sections"].append({
            "type": "table",
            "headers": ["Tipo", "Variante", "Stock", "Valor", "Refs"],
            "rows": rows
        })

        report["titulo"] = report["title"]; report["fecha_generacion"] = report["generated_at"]
        report["headers"] = ["Tipo", "Variante", "Stock", "Valor", "Refs"]; report["items"] = rows
        return report

    # ── 7. VENTAS DE DISEÑOS ─────────────────────────────────────────────────

    def get_informe_ventas_disenos(self, fecha_inicio: str, fecha_fin: str) -> dict:
        """Informe de ventas reales de productos con diseño."""
        data = self.repo.get_ventas_disenos(fecha_inicio, fecha_fin)
        report = self._get_base_report(f"VENTAS DE DISEÑOS", fecha_inicio, fecha_fin)
        
        total_uds = sum(r['unidades_vendidas'] for r in data)
        total_ventas = sum(r['total_ventas'] for r in data)

        report["sections"].append({
            "type": "summary",
            "headers": ["Total Unidades", "Total Ventas"],
            "rows": [[total_uds, f"{read_from_db(total_ventas):.2f} €"]]
        })

        rows = [[r['diseno_codigo'], r['diseno_nombre'], r['coleccion'], r['unidades_vendidas'], f"{read_from_db(r['total_ventas']):.2f} €"] for r in data]
        report["sections"].append({
            "type": "table",
            "headers": ["Código", "Diseño", "Colección", "Uds. Vendidas", "Total Ventas"],
            "rows": rows
        })

        report["titulo"] = report["title"]; report["fecha_generacion"] = report["generated_at"]
        report["resumen"] = {"Uds. Vendidas": total_uds, "Total Ingresos": f"{read_from_db(total_ventas):.2f} €"}
        report["headers"] = ["Código", "Diseño", "Colección", "Ventas", "Total"]; report["items"] = rows
        return report
