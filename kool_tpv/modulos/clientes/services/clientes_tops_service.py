"""Servicios para obtener 'tops' de clientes (backend).

Este módulo expone `ClientesTopsService` con consultas limpias hacia la
tabla `clientes` para calcular rankings/posiciones en Python.
"""
from typing import List, Dict
import logging
from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.clientes.services.clientes_tops_repository import ClientesTopsRepository

logger = logging.getLogger(__name__)


class ClientesTopsService:
    """Servicio que provee rankings/Top de clientes."""

    def __init__(self, db: Database):
        self.db = db
        self.repo = ClientesTopsRepository(db)

    def get_top_clientes_general(self, limit: int = 50) -> List[Dict]:
        """Top general de clientes ordenado por total_compras_euros."""
        return self.repo.get_top_clientes_general(limit)

    @staticmethod
    def _rows_to_result(rows) -> List[Dict]:
        """Mantenido por compatibilidad. La lógica real está en ClientesTopsRepository."""
        from kool_tpv.modulos.clientes.services.clientes_tops_repository import ClientesTopsRepository
        return ClientesTopsRepository._rows_to_result(rows)

    def get_top_por_producto(self, producto_id: int, limit: int = 50) -> List[Dict]:
        return self.repo.get_top_por_producto(producto_id, limit)

    def get_top_por_categoria(self, categoria_id: int, limit: int = 50) -> List[Dict]:
        return self.repo.get_top_por_categoria(categoria_id, limit)

    def get_top_por_tipo(self, tipo_id: int, limit: int = 50) -> List[Dict]:
        return self.repo.get_top_por_tipo(tipo_id, limit)

    def get_top_por_tesoro(self, limit: int = 50) -> List[Dict]:
        return self.repo.get_top_por_tesoro(limit)

    def get_top_ordenado_por_tesoro(self, field: str, limit: int = 50) -> List[Dict]:
        return self.repo.get_top_ordenado_por_tesoro(field, limit)

    def get_top_filtrado(
        self,
        categoria_id: int = None,
        tipo_id: int = None,
        producto_id: int = None,
        limit: int = 50,
    ) -> List[Dict]:
        return self.repo.get_top_filtrado(categoria_id, tipo_id, producto_id, limit)
