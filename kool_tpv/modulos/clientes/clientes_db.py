"""Acceso a datos para la tabla `clientes`.

Contiene la clase `ClientesDB` que expone métodos para consultar
información de clientes desde la base de datos usando el wrapper
`kool_tpv.base_datos.db_wrapper.Database`.
"""
from typing import List, Dict, Any
from decimal import Decimal

from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.base_datos.money_adapter import read_from_db, prepare_for_db


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
			"SELECT c.id, c.nombre, c.telefono, c.tesoro_total, c.id_nivel, c.fecha_alta, "
			"n.level AS nivel_level, n.nombre_nivel AS nivel_nombre, n.grafismo_nivel AS nivel_grafismo "
			"FROM clientes c "
			"LEFT JOIN niveles_fidelidad n ON c.id_nivel = n.id "
			"WHERE c.nombre LIKE ? OR c.dni LIKE ? OR c.telefono LIKE ? "
			"ORDER BY COALESCE(c.tesoro_total, 0) DESC"
		)
		rows = self.db.fetch_all(query, (term, term, term))

		# (removed debug print) filas retornadas por la consulta ya no se imprimen en producción

		clientes: List[Dict[str, Any]] = []
		for row in rows:
			# row expected: (id, nombre, telefono, tesoro_total, id_nivel, fecha_alta, nivel_level, nivel_nombre, nivel_grafismo)
			try:
				id_, nombre, telefono, tesoro_total, id_nivel, fecha_alta, nivel_level, nivel_nombre, nivel_grafismo = row
			except Exception:
				# defensivo: si el esquema cambia, ignorar fila mal formada
				continue

			clientes.append({
				"id": id_,
				"nombre": nombre,
				"telefono": telefono,
				"tesoro_total": read_from_db(int(tesoro_total or 0)),
				"id_nivel": id_nivel,
				"fecha_alta": fecha_alta,
				"nivel_level": nivel_level,
				"nivel_nombre": nivel_nombre or 'Forastero',
				"nivel_grafismo": nivel_grafismo or '~',
			})

		return clientes

	def sumar_tesoro(self, cliente_id: int, cantidad_decimal: Decimal) -> bool:
		"""Sumar una cantidad al tesoro total e histórico del cliente.

		Args:
			cliente_id: ID del cliente
			cantidad_decimal: Cantidad en euros (Decimal) a sumar

		Returns:
			bool: True si OK, False si error
		"""
		try:
			# Convertir a céntimos para la base de datos
			cantidad_cents = prepare_for_db(cantidad_decimal)
			
			query = """
				UPDATE clientes 
				SET tesoro_total = COALESCE(tesoro_total, 0) + ?,
				    tesoro_historico = COALESCE(tesoro_historico, 0) + ?
				WHERE id = ?
			"""
			self.db.execute_query(query, (cantidad_cents, cantidad_cents, cliente_id))
			return True
		except Exception:
			import logging
			logging.exception(f"Error sumando tesoro al cliente {cliente_id}")
			return False
