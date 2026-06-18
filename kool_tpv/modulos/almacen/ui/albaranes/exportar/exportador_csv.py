"""Exportador de albaranes a formato CSV."""
import csv
import logging
import os
from datetime import datetime
from pathlib import Path
from tkinter import filedialog
from typing import List, Dict, Any, Optional

from .logica_busqueda import BusquedaService

logger = logging.getLogger(__name__)


class ExportadorCSV:
    """Genera archivos CSV con datos de albaranes."""

    def __init__(self, db):
        self.db = db
        self.busqueda_service = BusquedaService(db)

    def exportar(
        self,
        albaran_ids: List[int],
        incluir_cabecera_tienda: bool = False,
        agrupar: bool = True,
        parent_widget=None
    ) -> Optional[str]:
        """Exportar albaranes a CSV.

        Args:
            albaran_ids: Lista de IDs de albaranes a exportar
            incluir_cabecera_tienda: Si True, incluye datos de la tienda al inicio
            agrupar: Si True, exporta todos en un único archivo. Si False, uno por cada albarán.
            parent_widget: Widget padre para el diálogo de guardar

        Returns:
            Ruta del archivo o carpeta generada o None si se canceló
        """
        if not albaran_ids:
            logger.warning("No hay albaranes para exportar")
            return None

        # Si agrupamos o solo hay uno, pedir nombre de archivo
        if agrupar or len(albaran_ids) == 1:
            fecha_hora = datetime.now().strftime('%Y%m%d_%H%M%S')
            default_filename = f"albaranes_{fecha_hora}.csv"

            file_path = filedialog.asksaveasfilename(
                parent=parent_widget,
                defaultextension=".csv",
                filetypes=[("Archivos CSV", "*.csv"), ("Todos los archivos", "*.*")],
                initialfile=default_filename,
                title="Guardar CSV"
            )

            if not file_path:
                logger.info("Exportación CSV cancelada")
                return None

            try:
                albaranes_completos = self._obtener_datos_completos(albaran_ids)
                self._escribir_csv(file_path, albaranes_completos, incluir_cabecera_tienda)
                return file_path
            except Exception:
                logger.exception("Error exportando CSV agrupado")
                return None
        else:
            # Exportar individualmente: pedir carpeta
            folder = filedialog.askdirectory(
                parent=parent_widget,
                title="Seleccionar carpeta para guardar archivos CSV"
            )
            if not folder:
                logger.info("Exportación CSV cancelada")
                return None

            try:
                fecha_hora = datetime.now().strftime('%Y%m%d_%H%M%S')
                for alb_id in albaran_ids:
                    albaran = self.busqueda_service.obtener_albaran_completo(alb_id)
                    if not albaran:
                        continue
                    
                    num_alb = albaran.get('num_albaran', alb_id)
                    filename = f"albaran_{num_alb}_{fecha_hora}.csv"
                    file_path = os.path.join(folder, filename)
                    
                    self._escribir_csv(file_path, [albaran], incluir_cabecera_tienda)
                
                logger.info(f"CSVs exportados en: {folder}")
                return folder
            except Exception:
                logger.exception("Error exportando CSVs individuales")
                return None

    def _obtener_datos_completos(
        self,
        albaran_ids: List[int]
    ) -> List[Dict[str, Any]]:
        """Obtener datos completos de albaranes incluyendo líneas."""
        albaranes = []
        for alb_id in albaran_ids:
            albaran = self.busqueda_service.obtener_albaran_completo(alb_id)
            if albaran:
                albaranes.append(albaran)
        return albaranes

    def _escribir_csv(
        self,
        file_path: str,
        albaranes: List[Dict[str, Any]],
        incluir_cabecera_tienda: bool
    ):
        """Escribir datos al archivo CSV."""
        with open(file_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f, delimiter=';', quoting=csv.QUOTE_MINIMAL)

            # Cabecera de tienda (opcional)
            if incluir_cabecera_tienda:
                self._escribir_cabecera_tienda(writer)

            # Por cada albarán
            for albaran in albaranes:
                # Fila de separación entre albaranes (excepto el primero)
                if albaran != albaranes[0]:
                    writer.writerow([])

                # Cabecera del albarán (sin totales)
                self._escribir_cabecera_albaran(writer, albaran)

                # Líneas del albarán
                lineas = albaran.get('lineas', [])
                if lineas:
                    writer.writerow([])
                    self._escribir_lineas_albaran(writer, lineas)

                # Totales al final
                writer.writerow([])
                self._escribir_totales_albaran(writer, albaran)

    def _escribir_cabecera_tienda(self, writer):
        """Escribir datos de la tienda al inicio del CSV."""
        try:
            cfg = self.busqueda_service.obtener_config_tienda()
            nombre_tienda = cfg.get('shop_name', '')
            telefono = cfg.get('shop_phone', '')
            direccion = cfg.get('fiscal_address', '')
            cif = cfg.get('fiscal_nif', '')

            writer.writerow(["TIENDA"])
            writer.writerow(["Nombre:", nombre_tienda])
            if direccion:
                writer.writerow(["Dirección:", direccion])
            if cif:
                writer.writerow(["CIF/NIF:", cif])
            if telefono:
                writer.writerow(["Teléfono:", telefono])
            writer.writerow([])
            writer.writerow(["-" * 50])
            writer.writerow([])

        except Exception:
            logger.exception("Error escribiendo cabecera de tienda")

    def _escribir_cabecera_albaran(self, writer, albaran: Dict[str, Any]):
        """Escribir datos de cabecera de un albarán."""
        writer.writerow(["ALBARÁN"])
        writer.writerow(["Número:", albaran.get('num_albaran', '')])
        writer.writerow(["Fecha:", albaran.get('fecha', '')])
        writer.writerow(["Proveedor:", albaran.get('proveedor_nombre', '')])

    def _escribir_totales_albaran(self, writer, albaran: Dict[str, Any]):
        """Escribir totales de un albarán tras sus líneas."""
        iva = albaran.get('total_iva_4', 0) + albaran.get('total_iva_10', 0) + albaran.get('total_iva_21', 0)
        writer.writerow(["Base Imponible:", f"{albaran.get('total_neto', 0):.2f}"])
        writer.writerow(["Total IVA:", f"{iva:.2f}"])
        writer.writerow(["Total:", f"{albaran.get('total', 0):.2f}"])

    def _escribir_lineas_albaran(self, writer, lineas: List[Dict[str, Any]]):
        """Escribir líneas de un albarán."""
        # Encabezados de columnas
        headers = [
            "EAN",
            "Producto",
            "Cantidad",
            "Precio Coste",
            "Total Línea"
        ]
        writer.writerow(headers)

        # Datos de líneas
        for linea in lineas:
            cantidad = linea.get('cantidad', 0)
            coste = linea.get('coste', 0)
            total_linea = cantidad * coste
            writer.writerow([
                linea.get('ean', ''),
                linea.get('nombre', ''),
                cantidad,
                f"{coste:.4f}",
                f"{total_linea:.2f}"
            ])
