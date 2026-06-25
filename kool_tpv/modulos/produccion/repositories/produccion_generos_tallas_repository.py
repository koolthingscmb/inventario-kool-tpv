"""Acceso a datos para géneros y tallas de producción."""
from typing import List, Optional

from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.produccion.models.produccion_genero_model import ProduccionGenero
from kool_tpv.modulos.produccion.models.produccion_talla_model import ProduccionTalla


class ProduccionGenerosRepository:
	"""DAO para `produccion_generos`."""

	def __init__(self, db: Database):
		self.db = db

	def get_todos(self) -> List[ProduccionGenero]:
		"""Obtener todos los géneros (incluyendo inactivos)."""
		query = "SELECT id, nombre, orden, activo FROM produccion_generos ORDER BY orden"
		rows = self.db.fetch_all(query)
		return [ProduccionGenero(id=r[0], nombre=r[1], orden=r[2], activo=r[3]) for r in rows]

	def get_activos(self) -> List[ProduccionGenero]:
		"""Obtener solo los géneros activos."""
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

	def crear(self, genero: ProduccionGenero) -> Optional[int]:
		"""Crear un nuevo género."""
		query = "INSERT INTO produccion_generos (nombre, orden, activo) VALUES (?, ?, ?)"
		self.db.execute_query(query, (genero.nombre, genero.orden, genero.activo))
		res = self.db.fetch_all("SELECT last_insert_rowid()")
		return res[0][0] if res else None

	def actualizar(self, genero: ProduccionGenero) -> bool:
		"""Actualizar un género existente."""
		if not genero.id: return False
		query = "UPDATE produccion_generos SET nombre = ?, orden = ?, activo = ? WHERE id = ?"
		self.db.execute_query(query, (genero.nombre, genero.orden, genero.activo, genero.id))
		return True

	def eliminar(self, genero_id: int) -> bool:
		"""Borrado físico de un género."""
		self.db.execute_query("DELETE FROM produccion_generos WHERE id = ?", (genero_id,))
		return True


class ProduccionTallasRepository:
	"""DAO para `produccion_tallas`."""

	def __init__(self, db: Database):
		self.db = db

	def get_todas(self) -> List[ProduccionTalla]:
		"""Obtener todas las tallas."""
		query = "SELECT id, nombre, orden, activo FROM produccion_tallas ORDER BY orden"
		rows = self.db.fetch_all(query)
		return [ProduccionTalla(id=r[0], nombre=r[1], orden=r[2], activo=r[3]) for r in rows]

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

	def get_por_genero_color_3d(self, genero_id: int, color_id: int) -> List[ProduccionTalla]:
		"""Obtener tallas disponibles para una combinación género+color (tabla 3D)."""
		query = """
			SELECT t.id, t.nombre, t.orden, t.activo
			FROM produccion_tallas t
			JOIN produccion_genero_color_tallas gct ON t.id = gct.talla_id
			WHERE gct.genero_id = ? AND gct.color_id = ? AND t.activo = 1
			ORDER BY t.orden
		"""
		rows = self.db.fetch_all(query, (genero_id, color_id))
		return [ProduccionTalla(id=r[0], nombre=r[1], orden=r[2], activo=r[3]) for r in rows]

	def get_por_tipo_color_3d(self, tipo_id: int, color_id: int, variante_id: Optional[int] = None) -> List[ProduccionTalla]:
		"""Obtener tallas disponibles para una combinación tipo+color o variante+color (tabla Libro de Recetas)."""
		if variante_id:
			query = """
				SELECT t.id, t.nombre, t.orden, t.activo
				FROM produccion_tallas t
				JOIN produccion_tipo_color_tallas tct ON t.id = tct.talla_id
				WHERE tct.tipo_id = ? AND tct.variante_id = ? AND tct.color_id = ? AND t.activo = 1
				ORDER BY t.orden
			"""
			params = (tipo_id, variante_id, color_id)
		else:
			query = """
				SELECT t.id, t.nombre, t.orden, t.activo
				FROM produccion_tallas t
				JOIN produccion_tipo_color_tallas tct ON t.id = tct.talla_id
				WHERE tct.tipo_id = ? AND tct.variante_id IS NULL AND tct.color_id = ? AND t.activo = 1
				ORDER BY t.orden
			"""
			params = (tipo_id, color_id)
			
		rows = self.db.fetch_all(query, params)
		return [ProduccionTalla(id=r[0], nombre=r[1], orden=r[2], activo=r[3]) for r in rows]

	def crear(self, talla: ProduccionTalla) -> Optional[int]:
		"""Crear una nueva talla."""
		query = "INSERT INTO produccion_tallas (nombre, orden, activo) VALUES (?, ?, ?)"
		self.db.execute_query(query, (talla.nombre, talla.orden, talla.activo))
		res = self.db.fetch_all("SELECT last_insert_rowid()")
		return res[0][0] if res else None

	def actualizar(self, talla: ProduccionTalla) -> bool:
		"""Actualizar una talla existente."""
		if not talla.id: return False
		query = "UPDATE produccion_tallas SET nombre = ?, orden = ?, activo = ? WHERE id = ?"
		self.db.execute_query(query, (talla.nombre, talla.orden, talla.activo, talla.id))
		return True

	def eliminar(self, talla_id: int) -> bool:
		"""Borrado físico de una talla."""
		self.db.execute_query("DELETE FROM produccion_tallas WHERE id = ?", (talla_id,))
		return True
