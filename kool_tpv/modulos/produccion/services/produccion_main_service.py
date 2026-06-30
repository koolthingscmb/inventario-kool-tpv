"""Servicio principal para gestión de órdenes de producción.

Contiene la clase `ProduccionMainService` que expone métodos para crear
órdenes de producción, añadir líneas y gestionar el flujo completo.
"""
from typing import List, Optional, Dict, Any
from datetime import datetime

from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.produccion.models.produccion_orden_model import ProduccionOrden
from kool_tpv.modulos.produccion.models.produccion_linea_model import ProduccionLinea
from kool_tpv.modulos.produccion.repositories.produccion_ordenes_repository import ProduccionOrdenesRepository
from kool_tpv.modulos.produccion.repositories.produccion_disenos_repository import ProduccionDisenosRepository
from kool_tpv.modulos.produccion.repositories.produccion_stock_colores_repository import ProduccionStockColoresRepository


class ProduccionMainService:
	"""Servicio principal de lógica de negocio para producción.

	Args:
		db: instancia de `Database` ya conectada.
	"""

	def __init__(self, db: Database):
		self.db = db
		self.ordenes_repo = ProduccionOrdenesRepository(db)
		self.disenos_repo = ProduccionDisenosRepository(db)
		self.stock_repo = ProduccionStockColoresRepository(db)

	def crear_orden(self, usuario_id: Optional[int] = None, notas: Optional[str] = None) -> Optional[int]:
		"""Crear una nueva orden de producción.

		Args:
			usuario_id: ID del usuario que crea la orden.
			notas: Notas opcionales para la orden.

		Returns:
			ID de la orden creada o None si error.
		"""
		orden = ProduccionOrden(
			fecha_hora=datetime.now(),
			usuario_id=usuario_id,
			notas=notas,
			estado="PENDIENTE"
		)
		return self.ordenes_repo.crear(orden)

	def añadir_linea(self, orden_id: int, diseno_codigo: str, producto_id: int,
	                 color_id: int, talla: str, cantidad: int,
	                 usuario_produccion_id: Optional[int] = None,
	                 produccion_mixta: int = 0,
	                 extra_id: Optional[int] = None,
	                 extra_coste: int = 0) -> Optional[int]:
		"""Añadir una línea a una orden de producción.

		Args:
			orden_id: ID de la orden.
			diseno_codigo: Código del diseño.
			producto_id: ID del producto.
			color_id: ID del color.
			talla: Talla del producto.
			cantidad: Cantidad a producir.
			usuario_produccion_id: ID del usuario de producción.
			produccion_mixta: 1 si es producción mixta, 0 si no.
			extra_id: ID del extra aplicado.
			extra_coste: Coste del extra en céntimos.

		Returns:
			ID de la línea creada o None si error.
		"""
		# Obtener el tipo de producto del producto_id
		producto = self._obtener_producto_por_id(producto_id)
		if not producto:
			return None

		tipo_id = producto.get("tipo", 0)

		# Obtener el coste unitario del diseño para este tipo de producto
		coste_unitario = self._obtener_coste_diseno(diseno_codigo, tipo_id)

		# Calcular coste total (unitario * cantidad) + coste del extra
		# El extra se aplica una vez por línea o por unidad? 
		# Normalmente un extra como "MIXTA" es por unidad producida.
		coste_total = (coste_unitario + extra_coste) * cantidad

		linea = ProduccionLinea(
			orden_id=orden_id,
			diseno_codigo=diseno_codigo,
			tipo_id=tipo_id,
			talla=talla,
			color_id=color_id,
			cantidad=cantidad,
			produccion_mixta=produccion_mixta,
			extra_id=extra_id,
			extra_coste=extra_coste,
			usuario_produccion_id=usuario_produccion_id,
			coste_unitario=coste_unitario,
			coste_total=coste_total
		)

		linea_id = self.ordenes_repo.crear_linea(linea)

		# Actualizar stock de colores
		if linea_id:
			self._actualizar_stock(producto_id, color_id, -cantidad)

		return linea_id

	def obtener_orden_completa(self, orden_id: int) -> Optional[Dict[str, Any]]:
		"""Obtener una orden con todas sus líneas.

		Args:
			orden_id: ID de la orden.

		Returns:
			Diccionario con la orden y sus líneas, o None si no existe.
		"""
		orden = self.ordenes_repo.get_por_id(orden_id)
		if not orden:
			return None

		lineas = self.ordenes_repo.get_lineas_por_orden(orden_id)

		return {
			"orden": orden,
			"lineas": lineas,
			"total_lineas": len(lineas),
			"coste_total": sum(l.coste_total for l in lineas)
		}

	def obtener_ordenes_pendientes(self) -> List[Dict[str, Any]]:
		"""Obtener todas las órdenes pendientes con sus líneas.

		Returns:
			Lista de diccionarios con órdenes y líneas.
		"""
		ordenes = self.ordenes_repo.get_pendientes()
		result = []
		for orden in ordenes:
			lineas = self.ordenes_repo.get_lineas_por_orden(orden.id)
			result.append({
				"orden": orden,
				"lineas": lineas,
				"total_lineas": len(lineas),
				"coste_total": sum(l.coste_total for l in lineas)
			})
		return result

	def actualizar_estado_orden(self, orden_id: int, estado: str) -> bool:
		"""Actualizar el estado de una orden.

		Args:
			orden_id: ID de la orden.
			estado: Nuevo estado (PENDIENTE, EN_PRODUCCION, COMPLETADA, etc).

		Returns:
			True si OK, False si error.
		"""
		return self.ordenes_repo.actualizar_estado(orden_id, estado)

	def eliminar_linea(self, linea_id: int) -> bool:
		"""Eliminar una línea de producción y restaurar stock.

		Args:
			linea_id: ID de la línea a eliminar.

		Returns:
			True si OK, False si error.
		"""
		# Primero obtener la línea para restaurar stock
		# Nota: esto requeriría un método get_por_id en el repo
		# Por ahora, simplemente eliminamos la línea
		return self.ordenes_repo.eliminar_linea(linea_id)

	def _obtener_producto_por_id(self, producto_id: int) -> Optional[Dict[str, Any]]:
		"""Obtener información de un producto por su ID.

		Args:
			producto_id: ID del producto.

		Returns:
			Diccionario con información del producto o None.
		"""
		query = "SELECT id, nombre, tipo FROM productos WHERE id = ?"
		rows = self.db.fetch_all(query, (producto_id,))
		if not rows:
			return None
		id_, nombre, tipo = rows[0]
		return {"id": id_, "nombre": nombre, "tipo": tipo}

	def _obtener_coste_diseno(self, codigo: str, tipo_id: int) -> int:
		"""Obtener el coste de un diseño para un tipo de producto.

		Busca en la lista de costes dinámicos del diseño.

		Args:
			codigo: Código del diseño.
			tipo_id: ID del tipo de producto.

		Returns:
			Coste en céntimos (0 si no existe).
		"""
		diseno = self.disenos_repo.get_por_codigo(codigo)
		if not diseno or not diseno.costes:
			return 0

		# Buscar coste más específico
		best = None
		best_score = -1
		for c in diseno.costes:
			if c.tipo_id != tipo_id:
				continue
			score = 0
			if c.variante_id is not None:
				score += 1
			if score > best_score:
				best = c
				best_score = score
		return best.coste if best else 0

	def _actualizar_stock(self, producto_id: int, color_id: int, delta: int) -> bool:
		"""Actualizar el stock de colores de un producto.

		Args:
			producto_id: ID del producto.
			color_id: ID del color.
			delta: Cantidad a sumar (positiva o negativa).

		Returns:
			True si OK, False si error.
		"""
		return self.stock_repo.sumar_cantidad(producto_id, color_id, delta)
