"""Orquestador de Exportar Albarán - Gestiona las diferentes vistas.

Flujo:
1. VistaFiltros (Pantalla 1): Proveedor + fechas + BUSCAR
2. VistaSeleccion (Pantalla 2): Lista con checkboxes + exportar
3. Opcional: VistaPreview (Pantalla 3): Preview antes de exportar
"""
import logging
from typing import Optional, List, Dict, Any

import customtkinter as ctk

from kool_tpv.utils.config_loader import load_colors
from kool_tpv.utils.font_loader import load_font_config
from .exportar.vista_filtros import VistaFiltros
from .exportar.vista_seleccion import VistaSeleccion
from .exportar.logica_busqueda import BusquedaService
from .exportar.exportador_csv import ExportadorCSV
from .exportar.exportador_pdf import ExportadorPDF
from .exportar.impresion import ImpresionService

logger = logging.getLogger(__name__)


class ExportarAlbaranUI:
    """Orquestador que gestiona las vistas de exportación de albaranes."""

    def __init__(self, parent, db=None, on_close_callback=None):
        """Inicializar orquestador.

        Args:
            parent: Widget padre (frame donde se mostrará)
            db: Conexión a base de datos
            on_close_callback: Función a llamar al cerrar
        """
        self.parent = parent
        self.db = db
        self.on_close_callback = on_close_callback

        # Configuración visual
        self.colors = load_colors('almacen')
        self.fonts = load_font_config()

        # Servicios
        self.busqueda_service = BusquedaService(db)
        self.exportador_csv = ExportadorCSV(db)
        self.exportador_pdf = ExportadorPDF(db)
        self.impresion_service = ImpresionService(db)

        # Estado
        self.albaranes_encontrados: List[Dict[str, Any]] = []
        self.vista_actual: Optional[ctk.CTkFrame] = None

        # Crear container y mostrar primera vista
        self._crear_container()
        self._mostrar_vista_filtros()
        self.font_config = load_font_config()
        self.title_font = ctk.CTkFont(
            family=self.font_config.get('title', {}).get('family', 'Inter'),
            size=self.font_config.get('title', {}).get('size', 18),
            weight=self.font_config.get('title', {}).get('weight', 'bold')
        )
        self.subtitle_font = ctk.CTkFont(
            family=self.font_config.get('subtitle', {}).get('family', 'Inter'),
            size=self.font_config.get('subtitle', {}).get('size', 14),
            weight=self.font_config.get('subtitle', {}).get('weight', 'bold')
        )

    def _crear_container(self):
        self.container = ctk.CTkFrame(self.parent, fg_color=self.colors.get('background', '#2B2B2B'))
        self.container.pack(fill='both', expand=True)

    def _clear_container(self):
        for widget in self.container.winfo_children():
            widget.destroy()
        self.vista_actual = None

    def _mostrar_vista_filtros(self):
        self._clear_container()
        self.vista_actual = VistaFiltros(
            parent=self.container, db=self.db,
            on_buscar_callback=self._on_buscar,
            on_cancelar_callback=self._on_cerrar
        )
        self.vista_actual.pack(fill='both', expand=True)

    def _mostrar_vista_seleccion(self, albaranes):
        self._clear_container()
        self.albaranes_encontrados = albaranes
        plantilla = self.busqueda_service.obtener_plantilla_albaran()
        mostrar_tienda = plantilla.get('albaran_pdf_mostrar_tienda', '0') == '1'
        self.vista_actual = VistaSeleccion(
            parent=self.container, albaranes=albaranes,
            on_volver_callback=self._mostrar_vista_filtros,
            on_exportar_csv_callback=self._on_exportar_csv,
            on_exportar_pdf_callback=self._on_exportar_pdf,
            on_imprimir_callback=self._on_imprimir,
            mostrar_tienda_default=mostrar_tienda
        )
        self.vista_actual.pack(fill='both', expand=True)

    def _on_buscar(self, proveedor_id, fecha_desde, fecha_hasta):
        """Callback cuando se pulsa BUSCAR."""
        try:
            from kool_tpv.base_datos.albaran_service import AlbaranService
            service = AlbaranService(self.db)
            albaranes = service.filtrar_albaranes(
                proveedor_id=proveedor_id,
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta
            )
            self._mostrar_vista_seleccion(albaranes)
        except Exception as e:
            logger.exception("Error buscando albaranes")

    def _on_exportar_csv(self, selected_ids, incluir_cabecera):
        """Exportar seleccionados a CSV."""
        try:
            resultado = self.exportador_csv.exportar(
                albaran_ids=selected_ids,
                incluir_cabecera_tienda=incluir_cabecera,
                parent_widget=self.parent
            )
            if resultado:
                logger.info(f"CSV exportado: {resultado}")
        except Exception:
            logger.exception("Error exportando CSV")

    def _on_exportar_pdf(self, selected_ids, incluir_cabecera, agrupar):
        """Exportar seleccionados a PDF."""
        try:
            if agrupar:
                resultado = self.exportador_pdf.exportar_agrupado(
                    albaran_ids=selected_ids,
                    incluir_cabecera_tienda=incluir_cabecera,
                    parent_widget=self.parent
                )
            else:
                resultado = self.exportador_pdf.exportar_individual(
                    albaran_ids=selected_ids,
                    incluir_cabecera_tienda=incluir_cabecera,
                    parent_widget=self.parent
                )
            if resultado:
                logger.info(f"PDF exportado: {resultado}")
        except Exception:
            logger.exception("Error exportando PDF")

    def _on_imprimir(self, selected_ids):
        """Imprimir albaranes seleccionados. (TODO: implementar)"""
        pass

    def _on_cerrar(self):
        """Cerrar UI de exportación."""
        if self.on_close_callback:
            self.on_close_callback()
        if hasattr(self, 'container'):
            self.container.destroy()

        pass  # Métodos del orquestador implementados arriba
