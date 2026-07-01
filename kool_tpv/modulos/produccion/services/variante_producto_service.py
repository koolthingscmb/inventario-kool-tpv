"""Lógica de negocio para el mapeo entre variantes de producción y productos del TPV.
"""
import logging
from typing import List, Optional

from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.produccion.models.variante_producto_link import VarianteProductoLink
from kool_tpv.modulos.produccion.repositories.variante_producto_repository import VarianteProductoRepository

logger = logging.getLogger(__name__)

class VarianteProductoService:
    """Servicio para gestionar la relación entre variantes y productos TPV."""

    def __init__(self, db: Database):
        self.db = db
        self.repo = VarianteProductoRepository(db)

    def get_todos(self) -> List[VarianteProductoLink]:
        """Obtener todos los mapeos configurados."""
        return self.repo.get_todos()

    def get_por_variante(self, variante_id: int) -> Optional[VarianteProductoLink]:
        """Obtener el mapeo activo para una variante de producción."""
        return self.repo.get_por_variante(variante_id)

    def guardar_mapeo(self, variante_id: int, producto_id: int, ratio: int = 1, link_id: Optional[int] = None) -> bool:
        """Crea o actualiza un mapeo.
        
        Asegura que una variante solo esté mapeada a un producto (regla de negocio).
        """
        try:
            link = VarianteProductoLink(
                id=link_id,
                variante_id=variante_id,
                producto_id=producto_id,
                ratio=ratio,
                activo=1
            )

            if link_id:
                return self.repo.actualizar(link)
            else:
                # Verificar si ya existe un mapeo para esta variante para evitar duplicados manuales
                # aunque la BD tiene un UNIQUE, aquí lo manejamos limpiamente
                existente = self.repo.get_por_variante(variante_id)
                if existente:
                    link.id = existente.id
                    return self.repo.actualizar(link)
                
                return self.repo.crear(link) is not None
        except Exception:
            logger.exception("Error en VarianteProductoService.guardar_mapeo")
            return False

    def eliminar_mapeo(self, link_id: int) -> bool:
        """Elimina un mapeo por su ID."""
        return self.repo.eliminar(link_id)

    def vincular_variante_con_producto(self, variante_id: int, producto_id: int, ratio: int = 1) -> bool:
        """Método de conveniencia para vinculación rápida."""
        return self.guardar_mapeo(variante_id, producto_id, ratio)
