"""Acceso a datos para la tabla `tipos_variantes_metodos`.

Contiene la clase `TiposVariantesMetodosRepository` que gestiona la relación
N:M entre variantes y métodos de impresión.
"""
from typing import List, Optional, Dict, Any
import logging

from kool_tpv.base_datos.db_wrapper import Database

logger = logging.getLogger(__name__)


class TiposVariantesMetodosRepository:
	"""Data access object (DAO) para `tipos_variantes_metodos`.

	Args:
		db: instancia de `Database` ya conectada.
	"""

	def __init__(self, db: Database):
		self.db = db

	def get_metodos_por_variante(self, variante_id: int) -> List[Dict[str, Any]]:
		"""Obtener los métodos disponibles para una variante.

		Args:
			variante_id: ID de la variante.

		Returns:
			Lista de dicts con: id, nombre, descripcion, icono, orden.
		"""
		query = """
			SELECT m.id, m.nombre, m.descripcion, m.icono, m.orden
			FROM produccion_metodos m
			INNER JOIN tipos_variantes_metodos tvm ON tvm.metodo_id = m.id
			WHERE tvm.variante_id = ? AND m.activo = 1
			ORDER BY m.orden, m.nombre
		"""
		rows = self.db.fetch_all(query, (variante_id,))
		return [
			{"id": r[0], "nombre": r[1], "descripcion": r[2],
			 "icono": r[3], "orden": r[4]}
			for r in rows
		]

	def get_variantes_por_metodo(self, metodo_id: int) -> List[int]:
		"""Obtener los IDs de variantes que tienen un método dado."""
		query = "SELECT variante_id FROM tipos_variantes_metodos WHERE metodo_id = ?"
		rows = self.db.fetch_all(query, (metodo_id,))
		return [r[0] for r in rows]

	def asignar_metodo(self, variante_id: int, metodo_id: int) -> bool:
		"""Asignar un método a una variante (si no existe ya)."""
		try:
			self.db.execute_query(
				"INSERT OR IGNORE INTO tipos_variantes_metodos (variante_id, metodo_id) VALUES (?, ?)",
				(variante_id, metodo_id)
			)
			return True
		except Exception:
			logger.exception(f"Error asignando metodo {metodo_id} a variante {variante_id}")
			return False

	def desasignar_metodo(self, variante_id: int, metodo_id: int) -> bool:
		"""Quitar un método de una variante."""
		try:
			self.db.execute_query(
				"DELETE FROM tipos_variantes_metodos WHERE variante_id = ? AND metodo_id = ?",
				(variante_id, metodo_id)
			)
			return True
		except Exception:
			logger.exception(f"Error desasignando metodo {metodo_id} de variante {variante_id}")
			return False

	def get_todos_metodos(self) -> List[Dict[str, Any]]:
		"""Obtener todos los métodos de impresión disponibles."""
		query = """
			SELECT id, nombre, descripcion, icono, activo, orden
			FROM produccion_metodos
			ORDER BY orden, nombre
		"""
		rows = self.db.fetch_all(query)
		return [
			{"id": r[0], "nombre": r[1], "descripcion": r[2],
			 "icono": r[3], "activo": r[4], "orden": r[5]}
			for r in rows
		]

	def get_metodos_activos(self) -> List[Dict[str, Any]]:
		"""Obtener solo los métodos activos."""
		query = """
			SELECT id, nombre, descripcion, icono, orden
			FROM produccion_metodos
			WHERE activo = 1
			ORDER BY orden, nombre
		"""
		rows = self.db.fetch_all(query)
		return [
			{"id": r[0], "nombre": r[1], "descripcion": r[2],
			 "icono": r[3], "orden": r[4]}
			for r in rows
		]
