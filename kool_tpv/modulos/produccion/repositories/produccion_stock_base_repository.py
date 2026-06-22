"""Acceso a datos para la tabla `produccion_stock_colores_tallas`.

Contiene la clase `ProduccionStockBaseRepository` que gestiona el inventario de bases
(productos sin imprimir) incluyendo género, color, talla y SKU de Shopify.
"""
from typing import List, Optional, Dict, Any
import logging

from kool_tpv.base_datos.db_wrapper import Database

logger = logging.getLogger(__name__)

class ProduccionStockBaseRepository:
	"""Data access object (DAO) para `produccion_stock_colores_tallas`.

	Args:
		db: instancia de `Database` ya conectada.
	"""

	def __init__(self, db: Database):
		self.db = db

	def get_todos(self) -> List[Dict[str, Any]]:
		"""Obtener todo el stock de bases con nombres legibles.

		Returns:
			Lista de dicts con: id, producto, genero, color, talla, sku, cantidad.
		"""
		query = """
			SELECT 
				psbt.id,
				p.nombre AS producto_nombre,
				g.nombre AS genero_nombre,
				c.nombre AS color_nombre,
				psbt.talla,
				psbt.sku,
				psbt.cantidad,
				psbt.producto_id,
				psbt.genero_id,
				psbt.color_id
			FROM produccion_stock_colores_tallas psbt
			JOIN productos p ON psbt.producto_id = p.id
			LEFT JOIN produccion_generos g ON psbt.genero_id = g.id
			JOIN produccion_colores c ON psbt.color_id = c.id
			ORDER BY p.nombre, g.nombre, c.nombre, psbt.talla
		"""
		try:
			rows = self.db.fetch_all(query)
			return [
				{
					"id": r[0],
					"producto": r[1],
					"genero": r[2] or "-",
					"color": r[3],
					"talla": r[4] or "-",
					"sku": r[5] or "",
					"cantidad": r[6] or 0,
					"producto_id": r[7],
					"genero_id": r[8],
					"color_id": r[9]
				}
				for r in rows
			]
		except Exception:
			logger.exception("Error obteniendo stock base")
			return []

	def crear_o_actualizar(self, producto_id: int, genero_id: Optional[int], 
	                      color_id: int, talla: str, sku: str, cantidad: int) -> bool:
		"""Insertar o actualizar una variante de stock base (Upsert)."""
		query = """
			INSERT INTO produccion_stock_colores_tallas 
				(producto_id, genero_id, color_id, talla, sku, cantidad)
			VALUES (?, ?, ?, ?, ?, ?)
			ON CONFLICT(producto_id, genero_id, color_id, talla) 
			DO UPDATE SET 
				sku = excluded.sku,
				cantidad = excluded.cantidad
		"""
		try:
			self.db.execute_query(query, (producto_id, genero_id, color_id, talla, sku, cantidad))
			return True
		except Exception:
			logger.exception(f"Error en upsert stock base: prod={producto_id}, sku={sku}")
			return False

	def eliminar(self, id_stock: int) -> bool:
		"""Eliminar un registro de stock por su ID."""
		try:
			self.db.execute_query("DELETE FROM produccion_stock_colores_tallas WHERE id = ?", (id_stock,))
			return True
		except Exception:
			logger.exception(f"Error eliminando stock base ID {id_stock}")
			return False

	def obtener_cantidad(self, producto_id: int, genero_id: Optional[int], 
	                     color_id: int, talla: str) -> int:
		"""Obtener la cantidad disponible para una variante específica."""
		query = """
			SELECT cantidad FROM produccion_stock_colores_tallas 
			WHERE producto_id = ? AND genero_id IS ? AND color_id = ? AND talla = ?
		"""
		try:
			# Usamos 'IS ?' para que funcione con NULL en genero_id
			res = self.db.fetch_all(query, (producto_id, genero_id, color_id, talla))
			return res[0][0] if res else 0
		except Exception:
			logger.exception("Error consultando cantidad stock base")
			return 0

	def actualizar_cantidad(self, producto_id: int, genero_id: Optional[int], 
	                        color_id: int, talla: str, delta: int) -> bool:
		"""Sumar o restar cantidad al stock (ej: -1 al producir)."""
		query = """
			UPDATE produccion_stock_colores_tallas 
			SET cantidad = cantidad + ?
			WHERE producto_id = ? AND genero_id IS ? AND color_id = ? AND talla = ?
		"""
		try:
			self.db.execute_query(query, (delta, producto_id, genero_id, color_id, talla))
			return True
		except Exception:
			logger.exception("Error actualizando cantidad stock base")
			return False
