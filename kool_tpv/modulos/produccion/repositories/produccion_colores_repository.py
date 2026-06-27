"""Acceso a datos para la tabla `produccion_colores`.

Contiene la clase `ProduccionColoresRepository` que expone métodos para consultar
y gestionar colores desde la base de datos usando el wrapper
`kool_tpv.base_datos.db_wrapper.Database`.
"""
from typing import List, Optional

from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.produccion.models.produccion_color_model import ProduccionColor


class ProduccionColoresRepository:
	"""Data access object (DAO) para `produccion_colores`.

	Args:
		db: instancia de `Database` ya conectada.
	"""

	def __init__(self, db: Database):
		self.db = db

	def get_todos(self) -> List[ProduccionColor]:
		"""Obtener todos los colores.

		Returns:
			Lista de objetos ProduccionColor.
		"""
		query = "SELECT id, nombre, codigo_hex FROM produccion_colores ORDER BY nombre"
		rows = self.db.fetch_all(query)

		colores: List[ProduccionColor] = []
		for row in rows:
			id_, nombre, codigo_hex = row
			colores.append(ProduccionColor(
				id=id_,
				nombre=nombre,
				codigo_hex=codigo_hex
			))
		return colores

	def get_activos(self) -> List[ProduccionColor]:
		"""Obtener solo los colores activos.

		Returns:
			Lista de objetos ProduccionColor con activo=1.
		"""
		query = "SELECT id, nombre, codigo_hex FROM produccion_colores ORDER BY nombre"
		rows = self.db.fetch_all(query)

		colores: List[ProduccionColor] = []
		for row in rows:
			id_, nombre, codigo_hex = row
			colores.append(ProduccionColor(
				id=id_,
				nombre=nombre,
				codigo_hex=codigo_hex
			))
		return colores

	def get_por_id(self, color_id: int) -> Optional[ProduccionColor]:
		"""Obtener un color por su ID.

		Args:
			color_id: ID del color.

		Returns:
			Objeto ProduccionColor o None si no existe.
		"""
		query = "SELECT id, nombre, codigo_hex FROM produccion_colores WHERE id = ?"
		rows = self.db.fetch_all(query, (color_id,))

		if not rows:
			return None

		id_, nombre, codigo_hex = rows[0]
		return ProduccionColor(
			id=id_,
			nombre=nombre,
			codigo_hex=codigo_hex
		)

	def crear(self, color: ProduccionColor) -> bool:
		"""Crear un nuevo color.

		Args:
			color: Objeto ProduccionColor con los datos.

		Returns:
			True si OK, False si error.
		"""
		try:
			query = """
				INSERT INTO produccion_colores (nombre, codigo_hex)
				VALUES (?, ?)
			"""
			self.db.execute_query(query, (color.nombre, color.codigo_hex))
			return True
		except Exception:
			import logging
			logging.exception("Error creando color")
			return False

	def actualizar(self, color: ProduccionColor) -> bool:
		"""Actualizar un color existente.

		Args:
			color: Objeto ProduccionColor con los datos (debe tener id).

		Returns:
			True si OK, False si error.
		"""
		if not color.id:
			return False

		try:
			query = """
				UPDATE produccion_colores
				SET nombre = ?, codigo_hex = ?
				WHERE id = ?
			"""
			self.db.execute_query(query, (color.nombre, color.codigo_hex, color.id))
			return True
		except Exception:
			import logging
			logging.exception(f"Error actualizando color {color.id}")
			return False

	def get_por_tipo_3d(self, tipo_id: int, variante_id: Optional[int] = None) -> List[ProduccionColor]:
		"""Obtener colores asignados a un tipo o variante (tabla Libro de Recetas)."""
		if variante_id:
			query = """
				SELECT DISTINCT c.id, c.nombre, c.codigo_hex
				FROM produccion_colores c
				JOIN produccion_tipo_color_tallas tct ON c.id = tct.color_id
				WHERE tct.tipo_id = ? AND tct.variante_id = ?
				ORDER BY c.nombre
			"""
			params = (tipo_id, variante_id)
		else:
			query = """
				SELECT DISTINCT c.id, c.nombre, c.codigo_hex
				FROM produccion_colores c
				JOIN produccion_tipo_color_tallas tct ON c.id = tct.color_id
				WHERE tct.tipo_id = ? AND tct.variante_id IS NULL
				ORDER BY c.nombre
			"""
			params = (tipo_id,)
			
		rows = self.db.fetch_all(query, params)
		return [
			ProduccionColor(id=r[0], nombre=r[1], codigo_hex=r[2])
			for r in rows
		]

	def eliminar(self, color_id: int) -> bool:
		"""Eliminar un color (soft delete: marcar como inactivo).

		Args:
			color_id: ID del color a eliminar.

		Returns:
			True si OK, False si error.
		"""
		try:
			query = "DELETE FROM produccion_colores WHERE id = ?"
			self.db.execute_query(query, (color_id,))
			return True
		except Exception:
			import logging
			logging.exception(f"Error eliminando color {color_id}")
			return False
