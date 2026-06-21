"""Acceso a datos para géneros y tallas de producción."""
from typing import List, Optional

from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.produccion.models.produccion_genero_model import ProduccionGenero
from kool_tpv.modulos.produccion.models.produccion_talla_model import ProduccionTalla


class ProduccionGenerosRepository:
	"""DAO para `produccion_generos`."""

	def __init__(self, db: Database):
		self.db = db

	def get_activos(self) -> List[ProduccionGenero]:
		query = "SELECT id, nombre, orden, activo FROM produccion_generos WHERE activo = 1 ORDER BY orden"
		rows = self.db.fetch_all(query)
		return [ProduccionGenero(id=r[0], nombre=r[1], orden=r[2], activo=r[3]) for r in rows]

	def get_por_tipo(self, tipo_id: int) -> List[ProduccionGenero]:
		"""Obtener géneros asociados a un tipo de producto."""
		query = """
			SELECT g.id, g.nombre, g.orden, g.activo
			FROM produccion_generos g
			JOIN produccion_tipos_generos tg ON g.id = tg.genero_id
			WHERE tg.tipo_id = ? AND g.activo = 1
			ORDER BY g.orden
		"""
		rows = self.db.fetch_all(query, (tipo_id,))
		return [ProduccionGenero(id=r[0], nombre=r[1], orden=r[2], activo=r[3]) for r in rows]


class ProduccionTallasRepository:
	"""DAO para `produccion_tallas`."""

	def __init__(self, db: Database):
		self.db = db

	def get_por_genero(self, genero_id: int) -> List[ProduccionTalla]:
		"""Obtener tallas asociadas a un género."""
		query = """
			SELECT t.id, t.nombre, t.orden, t.activo
			FROM produccion_tallas t
			JOIN produccion_genero_tallas gt ON t.id = gt.talla_id
			WHERE gt.genero_id = ? AND t.activo = 1
			ORDER BY t.orden
		"""
		rows = self.db.fetch_all(query, (genero_id,))
		return [ProduccionTalla(id=r[0], nombre=r[1], orden=r[2], activo=r[3]) for r in rows]
