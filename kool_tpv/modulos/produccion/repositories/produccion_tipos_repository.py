"""Acceso a datos para la tabla `produccion_tipos`.

Contiene la clase `ProduccionTiposRepository` que expone métodos para consultar
y gestionar tipos de producto fabricable desde la base de datos usando el wrapper
`kool_tpv.base_datos.db_wrapper.Database`.
"""
from typing import List, Optional

from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.produccion.models.produccion_tipos_model import ProduccionTipo


class ProduccionTiposRepository:
	"""Data access object (DAO) para `produccion_tipos`.

	Args:
		db: instancia de `Database` ya conectada.
	"""

	def __init__(self, db: Database):
		self.db = db

	def _row_to_tipo(self, row) -> ProduccionTipo:
		"""Mapear una fila de BD a objeto ProduccionTipo."""
		(id_, nombre, descripcion, color, icono,
		 coste_base, requiere_talla, requiere_color, requiere_genero, activo, orden) = row
		return ProduccionTipo(
			id=id_,
			nombre=nombre,
			descripcion=descripcion,
			color=color,
			icono=icono,
			coste_base=coste_base or 0.0,
			requiere_talla=requiere_talla or 0,
			requiere_color=requiere_color or 0,
			requiere_genero=requiere_genero or 0,
			activo=activo if activo is not None else 1,
			orden=orden or 0
		)

	_QUERY_SELECT = """
		SELECT id, nombre, descripcion, color, icono,
		       coste_base, requiere_talla, requiere_color, requiere_genero, activo, orden
		FROM produccion_tipos
	"""

	def get_todos(self) -> List[ProduccionTipo]:
		"""Obtener todos los tipos de producto.

		Returns:
			Lista de objetos ProduccionTipo ordenados por `orden`.
		"""
		query = self._QUERY_SELECT + " ORDER BY orden"
		rows = self.db.fetch_all(query)
		return [self._row_to_tipo(row) for row in rows]

	def get_activos(self) -> List[ProduccionTipo]:
		"""Obtener solo los tipos activos ordenados por `orden`.

		Returns:
			Lista de objetos ProduccionTipo con activo=1.
		"""
		query = self._QUERY_SELECT + " WHERE activo = 1 ORDER BY orden"
		rows = self.db.fetch_all(query)
		return [self._row_to_tipo(row) for row in rows]

	def get_por_id(self, tipo_id: int) -> Optional[ProduccionTipo]:
		"""Obtener un tipo por su ID.

		Args:
			tipo_id: ID del tipo.

		Returns:
			Objeto ProduccionTipo o None si no existe.
		"""
		query = self._QUERY_SELECT + " WHERE id = ?"
		rows = self.db.fetch_all(query, (tipo_id,))

		if not rows:
			return None
		return self._row_to_tipo(rows[0])

	def crear(self, tipo: ProduccionTipo) -> Optional[int]:
		"""Crear un nuevo tipo de producto.

		Args:
			tipo: Objeto ProduccionTipo con los datos.

		Returns:
			ID del tipo creado o None si error.
		"""
		try:
			query = """
				INSERT INTO produccion_tipos
				(nombre, descripcion, color, icono, coste_base,
				 requiere_talla, requiere_color, requiere_genero, activo, orden)
				VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
			"""
			self.db.execute_query(query, (
				tipo.nombre, tipo.descripcion, tipo.color, tipo.icono,
				tipo.coste_base, tipo.requiere_talla, tipo.requiere_color,
				tipo.requiere_genero, tipo.activo, tipo.orden
			))
			result = self.db.fetch_all("SELECT last_insert_rowid()")
			if result:
				return result[0][0]
			return None
		except Exception:
			import logging
			logging.exception("Error creando tipo de producto")
			return None

	def actualizar(self, tipo: ProduccionTipo) -> bool:
		"""Actualizar un tipo existente.

		Args:
			tipo: Objeto ProduccionTipo con los datos (debe tener id).

		Returns:
			True si OK, False si error.
		"""
		if not tipo.id:
			return False

		try:
			query = """
				UPDATE produccion_tipos
				SET nombre = ?, descripcion = ?, color = ?, icono = ?,
				    coste_base = ?, requiere_talla = ?, requiere_color = ?,
				    requiere_genero = ?, activo = ?, orden = ?
				WHERE id = ?
			"""
			self.db.execute_query(query, (
				tipo.nombre, tipo.descripcion, tipo.color, tipo.icono,
				tipo.coste_base, tipo.requiere_talla, tipo.requiere_color,
				tipo.requiere_genero, tipo.activo, tipo.orden, tipo.id
			))
			return True
		except Exception:
			import logging
			logging.exception(f"Error actualizando tipo {tipo.id}")
			return False

	def eliminar(self, tipo_id: int) -> bool:
		"""Eliminar un tipo (soft delete: marcar como inactivo).

		Args:
			tipo_id: ID del tipo a eliminar.

		Returns:
			True si OK, False si error.
		"""
		try:
			query = "UPDATE produccion_tipos SET activo = 0 WHERE id = ?"
			self.db.execute_query(query, (tipo_id,))
			return True
		except Exception:
			import logging
			logging.exception(f"Error eliminando tipo {tipo_id}")
			return False
