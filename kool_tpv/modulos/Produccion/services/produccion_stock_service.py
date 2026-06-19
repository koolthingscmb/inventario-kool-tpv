"""Servicio para gestión de stock de colores por producto.

Contiene la clase `ProduccionStockService` que expone métodos para gestionar
el stock de colores de productos fabricados por nosotros.
"""
from typing import List, Optional, Dict

from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.produccion.repositories.produccion_stock_colores_repository import ProduccionStockColoresRepository


class ProduccionStockService:
	"""Servicio de lógica de negocio para stock de colores.

	Args:
		db: instancia de `Database` ya conectada.
	"""

	def __init__(self, db: Database):
		self.db = db
		self.repository = ProduccionStockColoresRepository(db)

	def obtener_todo_stock(self) -> List[Dict[str, any]]:
		"""Obtener todo el stock de colores.

		Returns:
			Lista de diccionarios con información de stock.
		"""
		return self.repository.get_todos()

	def obtener_stock_producto(self, producto_id: int) -> List[Dict[str, any]]:
		"""Obtener el stock de colores para un producto específico.

		Args:
			producto_id: ID del producto.

		Returns:
			Lista de diccionarios con stock por color.
		"""
		return self.repository.get_por_producto(producto_id)

	def obtener_stock_producto_color(self, producto_id: int, color_id: int) -> Optional[int]:
		"""Obtener la cantidad de stock para un producto y color específicos.

		Args:
			producto_id: ID del producto.
			color_id: ID del color.

		Returns:
			Cantidad en stock o None si no existe el registro.
		"""
		stock = self.repository.get_por_producto_color(producto_id, color_id)
		return stock["cantidad"] if stock else None

	def obtener_cantidad(self, producto_id: int, color_id: int) -> int:
		"""Obtener solo la cantidad de stock para un producto y color.

		Args:
			producto_id: ID del producto.
			color_id: ID del color.

		Returns:
			Cantidad en stock (0 si no existe).
		"""
		return self.repository.obtener_cantidad(producto_id, color_id)

	def establecer_stock(self, producto_id: int, color_id: int, cantidad: int) -> bool:
		"""Establecer el stock de un producto-color (crea o actualiza).

		Args:
			producto_id: ID del producto.
			color_id: ID del color.
			cantidad: Nueva cantidad de stock.

		Returns:
			True si OK, False si error.
		"""
		if cantidad < 0:
			return False
		return self.repository.crear_o_actualizar(producto_id, color_id, cantidad)

	def actualizar_cantidad(self, producto_id: int, color_id: int, cantidad: int) -> bool:
		"""Actualizar la cantidad de stock existente.

		Args:
			producto_id: ID del producto.
			color_id: ID del color.
			cantidad: Nueva cantidad.

		Returns:
			True si OK, False si error.
		"""
		if cantidad < 0:
			return False
		return self.repository.actualizar_cantidad(producto_id, color_id, cantidad)

	def sumar_stock(self, producto_id: int, color_id: int, delta: int) -> bool:
		"""Sumar o restar cantidad al stock existente.

		Args:
			producto_id: ID del producto.
			color_id: ID del color.
			delta: Cantidad a sumar (positiva o negativa).

		Returns:
			True si OK, False si error o si resultaría en stock negativo.
		"""
		# Verificar que no resulte en stock negativo
		stock_actual = self.obtener_cantidad(producto_id, color_id)
		if stock_actual + delta < 0:
			return False

		return self.repository.sumar_cantidad(producto_id, color_id, delta)

	def eliminar_stock(self, producto_id: int, color_id: int) -> bool:
		"""Eliminar el registro de stock de un producto-color.

		Args:
			producto_id: ID del producto.
			color_id: ID del color.

		Returns:
			True si OK, False si error.
		"""
		return self.repository.eliminar(producto_id, color_id)

	def verificar_disponibilidad(self, producto_id: int, color_id: int, cantidad: int) -> bool:
		"""Verificar si hay suficiente stock disponible.

		Args:
			producto_id: ID del producto.
			color_id: ID del color.
			cantidad: Cantidad requerida.

		Returns:
			True si hay suficiente stock, False si no.
		"""
		stock_actual = self.obtener_cantidad(producto_id, color_id)
		return stock_actual >= cantidad
