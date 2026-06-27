"""Servicios para tallas de producción."""
from typing import List, Optional

from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.produccion.models.produccion_talla_model import ProduccionTalla
from kool_tpv.modulos.produccion.repositories.produccion_generos_tallas_repository import (
    ProduccionTallasRepository,
)


class ProduccionTallasService:
	"""Servicio para tallas de producción."""

	def __init__(self, db: Database):
		self.repository = ProduccionTallasRepository(db)

	def obtener_por_tipo_color_3d(self, tipo_id: int, color_id: int, variante_id: Optional[int] = None) -> List[ProduccionTalla]:
		"""Obtener tallas disponibles para una combinación tipo/variante+color (tabla stock base)."""
		return self.repository.get_por_tipo_color_3d(tipo_id, color_id, variante_id)
