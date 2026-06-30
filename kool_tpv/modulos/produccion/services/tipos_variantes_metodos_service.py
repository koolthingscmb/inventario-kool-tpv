"""Servicio para gestión de métodos por variante.

Contiene la clase `TiposVariantesMetodosService` que expone métodos para
gestionar qué métodos de impresión están disponibles para cada variante.
"""
from typing import List, Dict, Any, Optional

from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.produccion.repositories.tipos_variantes_metodos_repository import TiposVariantesMetodosRepository


class TiposVariantesMetodosService:
	"""Servicio de lógica de negocio para métodos por variante.

	Args:
		db: instancia de `Database` ya conectada.
	"""

	def __init__(self, db: Database):
		self.db = db
		self.repository = TiposVariantesMetodosRepository(db)

	def obtener_metodos_por_variante(self, variante_id: int) -> List[Dict[str, Any]]:
		"""Obtener los métodos disponibles para una variante.

		Args:
			variante_id: ID de la variante.

		Returns:
			Lista de dicts con: id, nombre, descripcion, icono, orden.
		"""
		if not variante_id:
			return []
		return self.repository.get_metodos_por_variante(variante_id)

	def obtener_todos_metodos(self) -> List[Dict[str, Any]]:
		"""Obtener todos los métodos de impresión."""
		return self.repository.get_todos_metodos()

	def obtener_metodos_activos(self) -> List[Dict[str, Any]]:
		"""Obtener solo los métodos activos."""
		return self.repository.get_metodos_activos()

	def asignar_metodo(self, variante_id: int, metodo_id: int) -> bool:
		"""Asignar un método a una variante."""
		if not variante_id or not metodo_id:
			return False
		return self.repository.asignar_metodo(variante_id, metodo_id)

	def desasignar_metodo(self, variante_id: int, metodo_id: int) -> bool:
		"""Quitar un método de una variante."""
		if not variante_id or not metodo_id:
			return False
		return self.repository.desasignar_metodo(variante_id, metodo_id)

	def sincronizar_metodos(self, variante_id: int, metodo_ids: List[int]) -> bool:
		"""Sincronizar los métodos de una variante.

		Borra los métodos no incluidos en la lista y añade los nuevos.

		Args:
			variante_id: ID de la variante.
			metodo_ids: Lista de IDs de métodos que debe tener la variante.

		Returns:
			True si OK, False si error.
		"""
		if not variante_id:
			return False
		try:
			actuales = self.repository.get_metodos_por_variante(variante_id)
			actuales_ids = {m["id"] for m in actuales}
			nuevos_ids = set(metodo_ids)

			for mid in actuales_ids - nuevos_ids:
				self.repository.desasignar_metodo(variante_id, mid)

			for mid in nuevos_ids - actuales_ids:
				self.repository.asignar_metodo(variante_id, mid)

			return True
		except Exception:
			import logging
			logging.exception(f"Error sincronizando métodos de variante {variante_id}")
			return False
