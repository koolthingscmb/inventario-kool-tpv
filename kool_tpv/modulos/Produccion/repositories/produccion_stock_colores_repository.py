"""Acceso a datos para la tabla `produccion_stock_colores`.

Contiene la clase `ProduccionStockColoresRepository` que expone métodos para consultar
y gestionar el stock de colores por producto desde la base de datos usando el wrapper
`kool_tpv.base_datos.db_wrapper.Database`.
"""
from typing import List, Optional, Dict

from kool_tpv.base_datos.db_wrapper import Database


class ProduccionStockColoresRepository:
	"""Data access object (DAO) para `produccion_stock_colores`.

	Args:
		db: instancia de `Database` ya conectada.
	"""

	def __init__(self, db: Database):
		self.db = db

	def get_todos(self) -> List[Dict[str, any]]:
		"""Obtener todo el stock de colores.

		Returns:
			Lista de diccionarios con claves: id, producto_id, color_id, cantidad.
		"""
		query = """
			SELECT psc.id, psc.producto_id, psc.color_id, psc.cantidad,
			       prod.nombre AS producto_nombre, c.nombre AS color_nombre
			FROM produccion_stock_colores psc
			LEFT JOIN productos prod ON psc.producto_id = prod.id
			LEFT JOIN produccion_colores c ON psc.color_id = c.id
			ORDER BY prod.nombre, c.nombre
		"""
		rows = self.db.fetch_all(query)

		stocks: List[Dict[str, any]] = []
		for row in rows:
			id_, producto_id, color_id, cantidad, producto_nombre, color_nombre = row
			stocks.append({
				"id": id_,
				"producto_id": producto_id,
				"color_id": color_id,
				"cantidad": cantidad or 0,
				"producto_nombre": producto_nombre,
				"color_nombre": color_nombre
			})
		return stocks

	def get_por_producto(self, producto_id: int) -> List[Dict[str, any]]:
		"""Obtener stock de colores para un producto específico.

		Args:
			producto_id: ID del producto.

		Returns:
			Lista de diccionarios con el stock por color.
		"""
		query = """
			SELECT psc.id, psc.producto_id, psc.color_id, psc.cantidad,
			       c.nombre AS color_nombre, c.hex_value
			FROM produccion_stock_colores psc
			LEFT JOIN produccion_colores c ON psc.color_id = c.id
			WHERE psc.producto_id = ?
			ORDER BY c.nombre
		"""
		rows = self.db.fetch_all(query, (producto_id,))

		stocks: List[Dict[str, any]] = []
		for row in rows:
			id_, producto_id, color_id, cantidad, color_nombre, hex_value = row
			stocks.append({
				"id": id_,
				"producto_id": producto_id,
				"color_id": color_id,
				"cantidad": cantidad or 0,
				"color_nombre": color_nombre,
				"hex_value": hex_value
			})
		return stocks

	def get_por_producto_color(self, producto_id: int, color_id: int) -> Optional[Dict[str, any]]:
		"""Obtener stock para un producto y color específicos.

		Args:
			producto_id: ID del producto.
			color_id: ID del color.

		Returns:
			Diccionario con el stock o None si no existe.
		"""
		query = """
			SELECT id, producto_id, color_id, cantidad
			FROM produccion_stock_colores
			WHERE producto_id = ? AND color_id = ?
		"""
		rows = self.db.fetch_all(query, (producto_id, color_id))

		if not rows:
			return None

		id_, producto_id, color_id, cantidad = rows[0]
		return {
			"id": id_,
			"producto_id": producto_id,
			"color_id": color_id,
			"cantidad": cantidad or 0
		}

	def obtener_cantidad(self, producto_id: int, color_id: int) -> int:
		"""Obtener solo la cantidad de stock para un producto y color.

		Args:
			producto_id: ID del producto.
			color_id: ID del color.

		Returns:
			Cantidad en stock (0 si no existe).
		"""
		query = """
			SELECT cantidad
			FROM produccion_stock_colores
			WHERE producto_id = ? AND color_id = ?
		"""
		rows = self.db.fetch_all(query, (producto_id, color_id))

		if not rows:
			return 0

		return rows[0][0] or 0

	def crear_o_actualizar(self, producto_id: int, color_id: int, cantidad: int) -> bool:
		"""Crear o actualizar el stock de un producto-color (upsert).

		Args:
			producto_id: ID del producto.
			color_id: ID del color.
			cantidad: Cantidad de stock.

		Returns:
			True si OK, False si error.
		"""
		try:
			# Intentar update primero
			query = """
				UPDATE produccion_stock_colores
				SET cantidad = ?
				WHERE producto_id = ? AND color_id = ?
			"""
			self.db.execute_query(query, (cantidad, producto_id, color_id))

			# Si no se actualizó ninguna fila, hacer insert
			if self.db.fetch_all("SELECT changes()")[0][0] == 0:
				query = """
					INSERT INTO produccion_stock_colores (producto_id, color_id, cantidad)
					VALUES (?, ?, ?)
				"""
				self.db.execute_query(query, (producto_id, color_id, cantidad))

			return True
		except Exception:
			import logging
			logging.exception(f"Error actualizando stock producto {producto_id} color {color_id}")
			return False

	def actualizar_cantidad(self, producto_id: int, color_id: int, cantidad: int) -> bool:
		"""Actualizar la cantidad de stock existente.

		Args:
			producto_id: ID del producto.
			color_id: ID del color.
			cantidad: Nueva cantidad.

		Returns:
			True si OK, False si error.
		"""
		try:
			query = """
				UPDATE produccion_stock_colores
				SET cantidad = ?
				WHERE producto_id = ? AND color_id = ?
			"""
			self.db.execute_query(query, (cantidad, producto_id, color_id))
			return True
		except Exception:
			import logging
			logging.exception(f"Error actualizando cantidad stock producto {producto_id} color {color_id}")
			return False

	def sumar_cantidad(self, producto_id: int, color_id: int, delta: int) -> bool:
		"""Sumar o restar cantidad al stock existente.

		Args:
			producto_id: ID del producto.
			color_id: ID del color.
			delta: Cantidad a sumar (positiva o negativa).

		Returns:
			True si OK, False si error.
		"""
		try:
			query = """
				UPDATE produccion_stock_colores
				SET cantidad = COALESCE(cantidad, 0) + ?
				WHERE producto_id = ? AND color_id = ?
			"""
			self.db.execute_query(query, (delta, producto_id, color_id))
			return True
		except Exception:
			import logging
			logging.exception(f"Error sumando cantidad stock producto {producto_id} color {color_id}")
			return False

	def eliminar(self, producto_id: int, color_id: int) -> bool:
		"""Eliminar el registro de stock de un producto-color.

		Args:
			producto_id: ID del producto.
			color_id: ID del color.

		Returns:
			True si OK, False si error.
		"""
		try:
			query = "DELETE FROM produccion_stock_colores WHERE producto_id = ? AND color_id = ?"
			self.db.execute_query(query, (producto_id, color_id))
			return True
		except Exception:
			import logging
			logging.exception(f"Error eliminando stock producto {producto_id} color {color_id}")
			return False
