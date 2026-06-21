"""Servicios para géneros y tallas de producción."""
from typing import List

from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.produccion.models.produccion_genero_model import ProduccionGenero
from kool_tpv.modulos.produccion.models.produccion_talla_model import ProduccionTalla
from kool_tpv.modulos.produccion.repositories.produccion_generos_tallas_repository import (
    ProduccionGenerosRepository,
    ProduccionTallasRepository,
)


class ProduccionGenerosService:
	"""Servicio para géneros de producción."""

	def __init__(self, db: Database):
		self.repository = ProduccionGenerosRepository(db)

	def obtener_por_tipo(self, tipo_id: int) -> List[ProduccionGenero]:
		"""Obtener géneros activos asociados a un tipo de producto."""
		return self.repository.get_por_tipo(tipo_id)


class ProduccionTallasService:
	"""Servicio para tallas de producción."""

	def __init__(self, db: Database):
		self.repository = ProduccionTallasRepository(db)

	def obtener_por_genero(self, genero_id: int) -> List[ProduccionTalla]:
		"""Obtener tallas activas asociadas a un género."""
		return self.repository.get_por_genero(genero_id)
