"""Acceso a datos para la tabla `produccion_stock_colores_tallas`.

Contiene la clase `ProduccionStockBaseRepository` que gestiona el inventario de bases
(materiales en blanco por tipo) incluyendo color, talla y SKU de Shopify.
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

	def get_tipos_con_stock(self) -> List[int]:
		"""Obtener IDs de tipos que tienen al menos un registro de stock base."""
		query = "SELECT DISTINCT tipo_id FROM produccion_stock_colores_tallas"
		try:
			rows = self.db.fetch_all(query)
			return [r[0] for r in rows if r[0] is not None]
		except Exception:
			logger.exception("Error obteniendo tipos con stock")
			return []

	def get_todos(self) -> List[Dict[str, Any]]:
		"""Obtener todo el stock de bases con nombres legibles.

		Returns:
			Lista de dicts con: id, tipo, variante, color, talla, sku, cantidad.
		"""
		query = """
			SELECT 
				psbt.id,
				t.nombre AS tipo_nombre,
				v.nombre AS variante_nombre,
				c.nombre AS color_nombre,
				psbt.talla,
				psbt.sku,
				psbt.cantidad,
				psbt.tipo_id,
				psbt.variante_id,
				psbt.color_id,
				psbt.coste_medio
			FROM produccion_stock_colores_tallas psbt
			JOIN tipos t ON psbt.tipo_id = t.id
			LEFT JOIN tipos_variantes v ON psbt.variante_id = v.id
			LEFT JOIN produccion_colores c ON psbt.color_id = c.id
			ORDER BY t.nombre, v.nombre, c.nombre, psbt.talla
		"""
		try:
			rows = self.db.fetch_all(query)
			return [
				{
					"id": r[0],
					"tipo": r[1],
					"variante": r[2] or "-",
					"color": r[3] or "-",
					"talla": r[4] or "-",
					"sku": r[5] or "",
					"cantidad": r[6] or 0,
					"tipo_id": r[7],
					"variante_id": r[8],
					"color_id": r[9],
					"coste_medio": r[10] or 0
				}
				for r in rows
			]
		except Exception:
			logger.exception("Error obteniendo stock base")
			return []

	def get_by_params(self, tipo_id: int, color_id: Optional[int], talla: str, 
	                  variante_id: Optional[int] = None, cur=None) -> Optional[Dict[str, Any]]:
		"""Obtener un registro específico por sus parámetros identificadores."""
		query = """
			SELECT id, tipo_id, variante_id, color_id, talla, sku, cantidad, coste_medio, talla_id
			FROM produccion_stock_colores_tallas
			WHERE tipo_id = ? AND variante_id IS ? AND color_id IS ? AND COALESCE(talla, '') = COALESCE(?, '')
		"""
		try:
			if cur:
				cur.execute(query, (tipo_id, variante_id, color_id, talla))
				row = cur.fetchone()
			else:
				row = self.db.fetch_one(query, (tipo_id, variante_id, color_id, talla))
			if row:
				return {
					"id": row[0],
					"tipo_id": row[1],
					"variante_id": row[2],
					"color_id": row[3],
					"talla": row[4],
					"sku": row[5],
					"cantidad": row[6],
					"coste_medio": row[7],
					"talla_id": row[8]
				}
			return None
		except Exception:
			logger.exception("Error buscando stock base por parámetros")
			return None

	def get_stock_por_tipo_color(self, tipo_id: int, color_id: int,
	                             variante_id: Optional[int] = None) -> Dict[str, int]:
		"""Obtener un dict {talla: cantidad} para un tipo+color+variante dados."""
		query = """
			SELECT talla, cantidad FROM produccion_stock_colores_tallas
			WHERE tipo_id = ? AND variante_id IS ? AND color_id = ?
		"""
		try:
			rows = self.db.fetch_all(query, (tipo_id, variante_id, color_id))
			# Usamos una clave especial (cadena vacía) si la talla es NULL
			return {(r[0] or "").strip().upper(): r[1] for r in rows}
		except Exception:
			logger.exception("Error obteniendo stock por tipo+color")
			return {}

	def crear_o_actualizar(self, tipo_id: int,
	                      color_id: Optional[int], talla: str, sku: str, 
	                      cantidad: int, coste_medio: int = 0,
	                      variante_id: Optional[int] = None,
	                      talla_id: Optional[int] = None,
	                      cur=None) -> bool:
		"""Insertar o actualizar una variante de stock base (Upsert manual).
		
		Usa SELECT + UPDATE/INSERT en vez de ON CONFLICT porque SQLite
		no considera NULL = NULL en la resolución de conflictos.
		"""
		# Normalizar talla: el UI puede enviar '-' o '' para ausencia, el script de importación envía None.
		# Unificar a None para que NULL y '' se traten como la misma talla.
		if not talla or talla == '-':
			talla = None
		check_query = """
			SELECT id FROM produccion_stock_colores_tallas 
			WHERE tipo_id = ? AND variante_id IS ? AND color_id IS ? AND COALESCE(talla, '') = COALESCE(?, '')
		"""
		update_query = """
			UPDATE produccion_stock_colores_tallas 
			SET sku = ?, cantidad = ?, coste_medio = ?, talla_id = ?
			WHERE id = ?
		"""
		insert_query = """
			INSERT INTO produccion_stock_colores_tallas 
				(tipo_id, variante_id, color_id, talla, sku, cantidad, coste_medio, talla_id)
			VALUES (?, ?, ?, ?, ?, ?, ?, ?)
		"""
		try:
			if cur:
				cur.execute(check_query, (tipo_id, variante_id, color_id, talla))
				existing = cur.fetchall()
				if existing:
					cur.execute(update_query, (sku, cantidad, coste_medio, talla_id, existing[0][0]))
				else:
					cur.execute(insert_query, (tipo_id, variante_id, color_id, talla, sku, cantidad, coste_medio, talla_id))
			else:
				existing = self.db.fetch_all(check_query, (tipo_id, variante_id, color_id, talla))
				if existing:
					self.db.execute_query(update_query, (sku, cantidad, coste_medio, talla_id, existing[0][0]))
				else:
					self.db.execute_query(insert_query, (tipo_id, variante_id, color_id, talla, sku, cantidad, coste_medio, talla_id))
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

	def obtener_cantidad(self, tipo_id: int,
	                     color_id: Optional[int], talla: str,
	                     variante_id: Optional[int] = None) -> int:
		"""Obtener la cantidad disponible para una variante específica."""
		query = """
			SELECT cantidad FROM produccion_stock_colores_tallas 
			WHERE tipo_id = ? AND variante_id IS ? AND color_id IS ? AND talla IS ?
		"""
		try:
			res = self.db.fetch_all(query, (tipo_id, variante_id, color_id, talla))
			return res[0][0] if res else 0
		except Exception:
			logger.exception("Error consultando cantidad stock base")
			return 0

	def get_coste_medio_variante(self, tipo_id: int,
	                             variante_id: Optional[int] = None) -> float:
		"""Obtener el coste medio ponderado de una variante (suma cantidad*coste / suma cantidad)."""
		query = """
			SELECT COALESCE(SUM(cantidad * coste_medio) / NULLIF(SUM(cantidad), 0), 0)
			FROM produccion_stock_colores_tallas
			WHERE tipo_id = ? AND variante_id IS ?
		"""
		try:
			row = self.db.fetch_one(query, (tipo_id, variante_id))
			return float(row[0]) if row and row[0] else 0.0
		except Exception:
			logger.exception("Error obteniendo coste medio variante")
			return 0.0

	def actualizar_cantidad(self, tipo_id: int,
	                        color_id: Optional[int], talla: str, delta: int,
	                        variante_id: Optional[int] = None) -> bool:
		"""Sumar o restar cantidad al stock (ej: -1 al producir)."""
		query = """
			UPDATE produccion_stock_colores_tallas 
			SET cantidad = cantidad + ?
			WHERE tipo_id = ? AND variante_id IS ? AND color_id IS ? AND talla IS ?
		"""
		try:
			self.db.execute_query(query, (delta, tipo_id, variante_id, color_id, talla))
			return True
		except Exception:
			logger.exception("Error actualizando cantidad stock base")
			return False
