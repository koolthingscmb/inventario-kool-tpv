"""Servicio para la gestión del stock de bases textiles y otros materiales.

Lógica de negocio para controlar el inventario de materiales en blanco,
sincronización de SKUs y disponibilidad para el taller.
"""
from typing import List, Optional, Dict, Any
import logging

from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.produccion.repositories.produccion_stock_base_repository import ProduccionStockBaseRepository

logger = logging.getLogger(__name__)

class ProduccionStockBaseService:
	"""Servicio para gestionar el stock base de producción.

	Args:
		db: instancia de `Database` ya conectada.
	"""

	def __init__(self, db: Database):
		self.db = db
		self.repo = ProduccionStockBaseRepository(db)

	def listar_todo(self) -> List[Dict[str, Any]]:
		"""Obtener la lista completa de stock base."""
		return self.repo.get_todos()

	def guardar_variante(self, tipo_id: int, genero_id: Optional[int], 
	                     color_id: Optional[int], talla: str, sku: str, cantidad: int) -> bool:
		"""Guardar o actualizar una variante de stock.
		
		Valida que los datos mínimos estén presentes.
		"""
		if not tipo_id:
			logger.error("Falta dato obligatorio (tipo) para guardar stock base")
			return False
		
		# Limpiar strings
		talla = (talla or "").strip().upper()
		sku = (sku or "").strip().upper()
		
		return self.repo.crear_o_actualizar(tipo_id, genero_id, color_id, talla, sku, cantidad)

	def eliminar_variante(self, id_stock: int) -> bool:
		"""Eliminar un registro de stock."""
		return self.repo.eliminar(id_stock)

	def comprobar_disponibilidad(self, tipo_id: int, genero_id: Optional[int], 
	                           color_id: int, talla: str, cantidad_requerida: int = 1) -> bool:
		"""Verifica si hay stock suficiente para producir."""
		stock_actual = self.repo.obtener_cantidad(tipo_id, genero_id, color_id, (talla or "").strip().upper())
		return stock_actual >= cantidad_requerida

	def consumir_stock(self, tipo_id: int, genero_id: Optional[int], 
	                  color_id: int, talla: str, cantidad: int) -> bool:
		"""Descontar stock del almacén de bases."""
		if cantidad <= 0:
			return True
		return self.repo.actualizar_cantidad(tipo_id, genero_id, color_id, (talla or "").strip().upper(), -cantidad)

	def reponer_stock(self, tipo_id: int, genero_id: Optional[int], 
	                 color_id: int, talla: str, cantidad: int) -> bool:
		"""Añadir stock al almacén de bases."""
		if cantidad <= 0:
			return True
		return self.repo.actualizar_cantidad(tipo_id, genero_id, color_id, (talla or "").strip().upper(), cantidad)

	def obtener_opciones_formulario(self) -> Dict[str, List[Dict[str, Any]]]:
		"""Obtener listas de tipos, géneros y colores para los selectores."""
		# 1. Tipos activos del taller
		query_tipos = """
			SELECT id, nombre FROM tipos WHERE activo = 1 ORDER BY nombre
		"""
		tipos = [{"id": r[0], "nombre": r[1]} for r in self.db.fetch_all(query_tipos)]

		# 2. Géneros
		query_gen = "SELECT id, nombre FROM produccion_generos ORDER BY id"
		generos = [{"id": r[0], "nombre": r[1]} for r in self.db.fetch_all(query_gen)]

		# 3. Colores
		query_col = "SELECT id, nombre FROM produccion_colores ORDER BY nombre"
		colores = [{"id": r[0], "nombre": r[1]} for r in self.db.fetch_all(query_col)]

		return {
			"tipos": tipos,
			"generos": generos,
			"colores": colores
		}
