"""Acceso a datos para la tabla `clientes`.

Contiene la clase `ClientesDB` que expone métodos para consultar
información de clientes desde la base de datos usando el wrapper
`kool_tpv.base_datos.db_wrapper.Database`.
"""
from typing import List, Dict, Any

from kool_tpv.base_datos.db_wrapper import Database


class ClientesDB:
	"""Data access object (DAO) para `clientes`.

	Args:
		db: instancia de `Database` ya conectada.
	"""

	def __init__(self, db: Database):
		self.db = db

	def get_clientes(self, filtro: str = "") -> List[Dict[str, Any]]:
		"""Buscar clientes filtrando por nombre, dni o telefono.

		Se utiliza LIKE para búsquedas parciales y los resultados se
		ordenan por `tesoro_total` de forma descendente.

		Args:
			filtro: término de búsqueda (coincidencia parcial).

		Returns:
			Lista de diccionarios con las claves: `id`, `nombre`,
			`telefono`, `tesoro_total`, `id_nivel`.
		"""
		term = f"%{filtro}%"
		query = (
			"SELECT id, nombre, telefono, tesoro_total, id_nivel, fecha_alta "
			"FROM clientes "
			"WHERE nombre LIKE ? OR dni LIKE ? OR telefono LIKE ? "
			"ORDER BY COALESCE(tesoro_total, 0) DESC"
		)
		rows = self.db.fetch_all(query, (term, term, term))

		# (removed debug print) filas retornadas por la consulta ya no se imprimen en producción

		clientes: List[Dict[str, Any]] = []
		for row in rows:
			# row expected: (id, nombre, telefono, tesoro_total, id_nivel)
			try:
				id_, nombre, telefono, tesoro_total, id_nivel, fecha_alta = row
			except Exception:
				# defensivo: si el esquema cambia, ignorar fila mal formada
				continue

			clientes.append({
				"id": id_,
				"nombre": nombre,
				"telefono": telefono,
				"tesoro_total": tesoro_total,
				"id_nivel": id_nivel,
				"fecha_alta": fecha_alta,
			})

		return clientes
