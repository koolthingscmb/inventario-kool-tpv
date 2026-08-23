"""Servicios para tallas de producción."""
from typing import List, Optional

from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.produccion.models.produccion_talla_model import ProduccionTalla
from kool_tpv.modulos.produccion.repositories.produccion_tallas_repository import (
    ProduccionTallasRepository,
)
from kool_tpv.modulos.produccion.repositories.produccion_tallas_grupos_repository import (
    ProduccionTallasGruposRepository,
)


class ProduccionTallasService:
	"""Servicio para tallas de producción."""

	def __init__(self, db: Database):
		self.repository = ProduccionTallasRepository(db)
		self.grupos_repo = ProduccionTallasGruposRepository(db)

	def obtener_todas(self) -> List[ProduccionTalla]:
		"""Obtener todas las tallas."""
		return self.repository.get_todas()

	def obtener_por_tipo_color_3d(self, tipo_id: int, color_id: int, variante_id: Optional[int] = None) -> List[ProduccionTalla]:
		"""Obtener tallas disponibles para una combinación tipo/variante+color (tabla stock base)."""
		return self.repository.get_por_tipo_color_3d(tipo_id, color_id, variante_id)

	def obtener_por_id(self, talla_id: int) -> Optional[ProduccionTalla]:
		"""Obtener una talla por su ID."""
		return self.repository.get_por_id(talla_id)

	def obtener_por_nombre(self, nombre: str) -> Optional[ProduccionTalla]:
		"""Obtener una talla por su nombre exacto."""
		return self.repository.get_por_nombre(nombre)

	def obtener_por_variante(self, variante_id: int) -> List[ProduccionTalla]:
		"""Obtener las tallas permitidas para una variante según su grupo.
		Si la variante no tiene grupo, devuelve una lista vacía.
		"""
		talla_ids = self.grupos_repo.get_tallas_por_variante(variante_id)
		if not talla_ids:
			return []
		
		# Obtener los modelos de talla correspondientes
		todas = self.repository.get_todas()
		return [t for t in todas if t.id in talla_ids]
