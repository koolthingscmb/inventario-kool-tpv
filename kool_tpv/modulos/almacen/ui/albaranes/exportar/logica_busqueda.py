"""Lógica de búsqueda de albaranes para exportación."""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from kool_tpv.base_datos.albaran_service import AlbaranService
from kool_tpv.base_datos.configuracion_repository import ConfiguracionRepository
from kool_tpv.modulos.configuracion.impresion.plantillas_albaran_ui import CLAVES_PLANTILLA

logger = logging.getLogger(__name__)


class BusquedaService:
    """Servicio para buscar albaranes con filtros."""

    def __init__(self, db):
        self.db = db
        self.albaran_service = AlbaranService(db) if db else None

    def buscar_albaranes(
        self,
        proveedor_id: Optional[int] = None,
        fecha_desde: Optional[str] = None,
        fecha_hasta: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Buscar albaranes con filtros.

        Args:
            proveedor_id: ID del proveedor (None = todos)
            fecha_desde: Fecha inicio formato YYYY-MM-DD
            fecha_hasta: Fecha fin formato YYYY-MM-DD

        Returns:
            Lista de albaranes con formato para la UI
        """
        if not self.albaran_service:
            logger.error("No hay conexión a la base de datos")
            return []

        try:
            # Usar el método existente del servicio
            albaranes = self.albaran_service.filtrar_albaranes(
                proveedor_id=proveedor_id,
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta
            )

            # Formatear para la UI
            resultado = []
            for alb in albaranes:
                resultado.append({
                    'id': alb.get('id'),
                    'num_albaran': alb.get('num_albaran', ''),
                    'fecha': alb.get('fecha', ''),
                    'proveedor_nombre': alb.get('proveedor_nombre', ''),
                    'total': alb.get('total', 0.0),
                    'num_lineas': alb.get('num_lineas', 0)
                })

            logger.info(f"Búsqueda encontrada: {len(resultado)} albaranes")
            return resultado

        except Exception:
            logger.exception("Error buscando albaranes")
            return []

    def obtener_lineas_albaran(self, albaran_id: int) -> List[Dict[str, Any]]:
        """Obtener líneas de un albarán específico.

        Args:
            albaran_id: ID del albarán

        Returns:
            Lista de líneas del albarán
        """
        if not self.albaran_service:
            return []

        try:
            detalle = self.albaran_service.get_albaran_detalle(albaran_id)
            if detalle:
                return detalle.get('lines', [])
            return []
        except Exception:
            logger.exception(f"Error obteniendo líneas del albarán {albaran_id}")
            return []

    def obtener_albaran_completo(self, albaran_id: int) -> Optional[Dict[str, Any]]:
        """Obtener albarán completo con sus líneas, como dict plano."""
        if not self.albaran_service:
            return None
        try:
            detalle = self.albaran_service.get_albaran_detalle(albaran_id)
            if not detalle:
                return None
            albaran = detalle.get('albaran', {})
            albaran['lineas'] = detalle.get('lines', [])
            return albaran
        except Exception:
            logger.exception(f"Error obteniendo albarán completo {albaran_id}")
            return None

    def obtener_config_tienda(self) -> Dict[str, str]:
        """Obtener configuración de la tienda desde la tabla configuracion."""
        if not self.db:
            return {}
        try:
            repo = ConfiguracionRepository(self.db)
            return repo.obtener_multiples(
                ['shop_name', 'shop_phone', 'fiscal_address', 'fiscal_nif']
            )
        except Exception:
            logger.exception("Error obteniendo configuración de tienda")
            return {}

    def obtener_plantilla_albaran(self) -> Dict[str, str]:
        """Obtener configuración de plantilla PDF de albaranes.

        Devuelve los valores guardados en BD, o los defaults si no existen.
        """
        if not self.db:
            return dict(CLAVES_PLANTILLA)
        try:
            repo = ConfiguracionRepository(self.db)
            guardados = repo.obtener_multiples(list(CLAVES_PLANTILLA.keys()))
            result = dict(CLAVES_PLANTILLA)
            result.update(guardados)
            return result
        except Exception:
            logger.exception("Error obteniendo plantilla de albarán")
            return dict(CLAVES_PLANTILLA)
