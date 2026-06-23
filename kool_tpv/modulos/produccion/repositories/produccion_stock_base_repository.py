"""Acceso a datos para la tabla `produccion_stock_colores_tallas`.

Contiene la clase `ProduccionStockBaseRepository` que gestiona el inventario de bases
(materiales en blanco por tipo) incluyendo género, color, talla y SKU de Shopify.
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
			Lista de dicts con: id, tipo, genero, color, talla, sku, cantidad.
		"""
		query = """
			SELECT 
				psbt.id,
				t.nombre AS tipo_nombre,
				g.nombre AS genero_nombre,
				c.nombre AS color_nombre,
				psbt.talla,
				psbt.sku,
				psbt.cantidad,
				psbt.tipo_id,
				psbt.genero_id,
				psbt.color_id,
				psbt.coste_medio
			FROM produccion_stock_colores_tallas psbt
			JOIN tipos t ON psbt.tipo_id = t.id
			LEFT JOIN produccion_generos g ON psbt.genero_id = g.id
			LEFT JOIN produccion_colores c ON psbt.color_id = c.id
			ORDER BY t.nombre, g.nombre, c.nombre, psbt.talla
		"""
		try:
			rows = self.db.fetch_all(query)
			return [
				{
					"id": r[0],
					"tipo": r[1],
					"genero": r[2] or "-",
					"color": r[3] or "-",
					"talla": r[4] or "-",
					"sku": r[5] or "",
					"cantidad": r[6] or 0,
					"tipo_id": r[7],
					"genero_id": r[8],
					"color_id": r[9],
					"coste_medio": r[10] or 0
				}
				for r in rows
			]
		except Exception:
			logger.exception("Error obteniendo stock base")
			return []

	def crear_o_actualizar(self, tipo_id: int, genero_id: Optional[int], 
	                      color_id: Optional[int], talla: str, sku: str, 
	                      cantidad: int, coste_medio: int = 0) -> bool:
		"""Insertar o actualizar una variante de stock base (Upsert manual).
		
		Usa SELECT + UPDATE/INSERT en vez de ON CONFLICT porque SQLite
		no considera NULL = NULL en la resolución de conflictos.
		"""
		check_query = """
			SELECT id FROM produccion_stock_colores_tallas 
			WHERE tipo_id = ? AND genero_id IS ? AND color_id IS ? AND talla = ?
		"""
		update_query = """
			UPDATE produccion_stock_colores_tallas 
			SET sku = ?, cantidad = ?, coste_medio = ?
			WHERE id = ?
		"""
		insert_query = """
			INSERT INTO produccion_stock_colores_tallas 
				(tipo_id, genero_id, color_id, talla, sku, cantidad, coste_medio)
			VALUES (?, ?, ?, ?, ?, ?, ?)
		"""
		try:
			existing = self.db.fetch_all(check_query, (tipo_id, genero_id, color_id, talla))
			if existing:
				self.db.execute_query(update_query, (sku, cantidad, coste_medio, existing[0][0]))
			else:
				self.db.execute_query(insert_query, (tipo_id, genero_id, color_id, talla, sku, cantidad, coste_medio))
			return True
		except Exception:
			logger.exception(f"Error en upsert stock base: tipo={tipo_id}, sku={sku}")
			return False

	def eliminar(self, id_stock: int) -> bool:
		"""Eliminar un registro de stock por su ID."""
		try:
			self.db.execute_query("DELETE FROM produccion_stock_colores_tallas WHERE id = ?", (id_stock,))
			return True
		except Exception:
			logger.exception(f"Error eliminando stock base ID {id_stock}")
			return False

	def obtener_cantidad(self, tipo_id: int, genero_id: Optional[int], 
	                     color_id: Optional[int], talla: str) -> int:
		"""Obtener la cantidad disponible para una variante específica."""
		query = """
			SELECT cantidad FROM produccion_stock_colores_tallas 
			WHERE tipo_id = ? AND genero_id IS ? AND color_id IS ? AND talla = ?
		"""
		try:
			res = self.db.fetch_all(query, (tipo_id, genero_id, color_id, talla))
			return res[0][0] if res else 0
		except Exception:
			logger.exception("Error consultando cantidad stock base")
			return 0

	def actualizar_cantidad(self, tipo_id: int, genero_id: Optional[int], 
	                        color_id: Optional[int], talla: str, delta: int) -> bool:
		"""Sumar o restar cantidad al stock (ej: -1 al producir)."""
		query = """
			UPDATE produccion_stock_colores_tallas 
			SET cantidad = cantidad + ?
			WHERE tipo_id = ? AND genero_id IS ? AND color_id IS ? AND talla = ?
		"""
		try:
			self.db.execute_query(query, (delta, tipo_id, genero_id, color_id, talla))
			return True
		except Exception:
			logger.exception("Error actualizando cantidad stock base")
			return False
