"""Acceso a datos para la tabla `produccion_ordenes` y `produccion_lineas`.

Contiene la clase `ProduccionOrdenesRepository` que expone métodos para consultar
y gestionar órdenes de producción y sus líneas desde la base de datos usando el wrapper
`kool_tpv.base_datos.db_wrapper.Database`.
"""
from typing import List, Optional

from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.produccion.models.produccion_orden_model import ProduccionOrden
from kool_tpv.modulos.produccion.models.produccion_linea_model import ProduccionLinea


class ProduccionOrdenesRepository:
	"""Data access object (DAO) para `produccion_ordenes`.

	Args:
		db: instancia de `Database` ya conectada.
	"""

	def __init__(self, db: Database):
		self.db = db

	def get_todas(self) -> List[ProduccionOrden]:
		"""Obtener todas las órdenes de producción.

		Returns:
			Lista de objetos ProduccionOrden.
		"""
		query = """
			SELECT id, fecha_hora, usuario_id, notas, tiempo_estimado_minutos, estado, origen
			FROM produccion_ordenes
			ORDER BY fecha_hora DESC
		"""
		rows = self.db.fetch_all(query)

		ordenes: List[ProduccionOrden] = []
		for row in rows:
			id_, fecha_hora, usuario_id, notas, tiempo_estimado_minutos, estado, origen = row
			ordenes.append(ProduccionOrden(
				id=id_,
				fecha_hora=fecha_hora,
				usuario_id=usuario_id,
				notas=notas,
				tiempo_estimado_minutos=tiempo_estimado_minutos,
				estado=estado,
				origen=origen or 'KOOL'
			))
		return ordenes

	def get_por_id(self, orden_id: int) -> Optional[ProduccionOrden]:
		"""Obtener una orden por su ID.

		Args:
			orden_id: ID de la orden.

		Returns:
			Objeto ProduccionOrden o None si no existe.
		"""
		query = """
			SELECT id, fecha_hora, usuario_id, notas, tiempo_estimado_minutos, estado, origen
			FROM produccion_ordenes
			WHERE id = ?
		"""
		rows = self.db.fetch_all(query, (orden_id,))

		if not rows:
			return None

		id_, fecha_hora, usuario_id, notas, tiempo_estimado_minutos, estado, origen = rows[0]
		return ProduccionOrden(
			id=id_,
			fecha_hora=fecha_hora,
			usuario_id=usuario_id,
			notas=notas,
			tiempo_estimado_minutos=tiempo_estimado_minutos,
			estado=estado,
			origen=origen or 'KOOL'
		)

	def get_pendientes(self) -> List[ProduccionOrden]:
		"""Obtener órdenes en estado PENDIENTE.

		Returns:
			Lista de objetos ProduccionOrden con estado PENDIENTE.
		"""
		query = """
			SELECT id, fecha_hora, usuario_id, notas, tiempo_estimado_minutos, estado, origen
			FROM produccion_ordenes
			WHERE estado = 'PENDIENTE'
			ORDER BY fecha_hora ASC
		"""
		rows = self.db.fetch_all(query)

		ordenes: List[ProduccionOrden] = []
		for row in rows:
			id_, fecha_hora, usuario_id, notas, tiempo_estimado_minutos, estado, origen = row
			ordenes.append(ProduccionOrden(
				id=id_,
				fecha_hora=fecha_hora,
				usuario_id=usuario_id,
				notas=notas,
				tiempo_estimado_minutos=tiempo_estimado_minutos,
				estado=estado,
				origen=origen or 'KOOL'
			))
		return ordenes

	def crear(self, orden: ProduccionOrden) -> Optional[int]:
		"""Crear una nueva orden de producción.

		Args:
			orden: Objeto ProduccionOrden con los datos.

		Returns:
			ID de la orden creada o None si error.
		"""
		try:
			query = """
				INSERT INTO produccion_ordenes
				(fecha_hora, usuario_id, notas, tiempo_estimado_minutos, estado, origen)
				VALUES (?, ?, ?, ?, ?, ?)
			"""
			self.db.execute_query(query, (
				orden.fecha_hora, orden.usuario_id, orden.notas,
				orden.tiempo_estimado_minutos, orden.estado, orden.origen
			))
			# Obtener el ID del último insert
			result = self.db.fetch_all("SELECT last_insert_rowid()")
			if result:
				return result[0][0]
			return None
		except Exception:
			import logging
			logging.exception("Error creando orden de producción")
			return None

	def actualizar(self, orden: ProduccionOrden) -> bool:
		"""Actualizar una orden existente.

		Args:
			orden: Objeto ProduccionOrden con los datos (debe tener id).

		Returns:
			True si OK, False si error.
		"""
		if not orden.id:
			return False

		try:
			query = """
				UPDATE produccion_ordenes
				SET fecha_hora = ?, usuario_id = ?, notas = ?,
				    tiempo_estimado_minutos = ?, estado = ?, origen = ?
				WHERE id = ?
			"""
			self.db.execute_query(query, (
				orden.fecha_hora, orden.usuario_id, orden.notas,
				orden.tiempo_estimado_minutos, orden.estado, orden.origen, orden.id
			))
			return True
		except Exception:
			import logging
			logging.exception(f"Error actualizando orden {orden.id}")
			return False

	def actualizar_estado(self, orden_id: int, estado: str) -> bool:
		"""Actualizar solo el estado de una orden.

		Args:
			orden_id: ID de la orden.
			estado: Nuevo estado (PENDIENTE, EN_PRODUCCION, COMPLETADA, etc).

		Returns:
			True si OK, False si error.
		"""
		try:
			query = "UPDATE produccion_ordenes SET estado = ? WHERE id = ?"
			self.db.execute_query(query, (estado, orden_id))
			return True
		except Exception:
			import logging
			logging.exception(f"Error actualizando estado de orden {orden_id}")
			return False

	def eliminar(self, orden_id: int) -> bool:
		"""Eliminar una orden (y sus líneas por CASCADE).

		Args:
			orden_id: ID de la orden a eliminar.

		Returns:
			True si OK, False si error.
		"""
		try:
			query = "DELETE FROM produccion_ordenes WHERE id = ?"
			self.db.execute_query(query, (orden_id,))
			return True
		except Exception:
			import logging
			logging.exception(f"Error eliminando orden {orden_id}")
			return False

	# --- MÉTODOS PARA LÍNEAS DE PRODUCCIÓN ---

	def get_lineas_por_orden(self, orden_id: int) -> List[ProduccionLinea]:
		"""Obtener todas las líneas de una orden.

		Args:
			orden_id: ID de la orden.

		Returns:
			Lista de objetos ProduccionLinea.
		"""
		query = """
			SELECT id, orden_id, diseno_codigo, tipo_producto, talla, color_id,
			       cantidad, produccion_mixta, usuario_produccion_id,
			       coste_unitario, coste_total
			FROM produccion_lineas
			WHERE orden_id = ?
			ORDER BY id
		"""
		rows = self.db.fetch_all(query, (orden_id,))

		lineas: List[ProduccionLinea] = []
		for row in rows:
			(id_, orden_id, diseno_codigo, tipo_producto, talla, color_id,
			 cantidad, produccion_mixta, usuario_produccion_id,
			 coste_unitario, coste_total) = row
			lineas.append(ProduccionLinea(
				id=id_,
				orden_id=orden_id,
				diseno_codigo=diseno_codigo,
				tipo_producto=tipo_producto,
				talla=talla,
				color_id=color_id,
				cantidad=cantidad,
				produccion_mixta=produccion_mixta,
				usuario_produccion_id=usuario_produccion_id,
				coste_unitario=coste_unitario,
				coste_total=coste_total
			))
		return lineas

	def crear_linea(self, linea: ProduccionLinea) -> Optional[int]:
		"""Crear una nueva línea de producción.

		Args:
			linea: Objeto ProduccionLinea con los datos.

		Returns:
			ID de la línea creada o None si error.
		"""
		try:
			query = """
				INSERT INTO produccion_lineas
				(orden_id, diseno_codigo, tipo_producto, talla, color_id,
				 cantidad, produccion_mixta, usuario_produccion_id,
				 coste_unitario, coste_total)
				VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
			"""
			self.db.execute_query(query, (
				linea.orden_id, linea.diseno_codigo, linea.tipo_producto,
				linea.talla, linea.color_id, linea.cantidad,
				linea.produccion_mixta, linea.usuario_produccion_id,
				linea.coste_unitario, linea.coste_total
			))
			# Obtener el ID del último insert
			result = self.db.fetch_all("SELECT last_insert_rowid()")
			if result:
				return result[0][0]
			return None
		except Exception:
			import logging
			logging.exception("Error creando línea de producción")
			return None

	def eliminar_linea(self, linea_id: int) -> bool:
		"""Eliminar una línea de producción.

		Args:
			linea_id: ID de la línea a eliminar.

		Returns:
			True si OK, False si error.
		"""
		try:
			query = "DELETE FROM produccion_lineas WHERE id = ?"
			self.db.execute_query(query, (linea_id,))
			return True
		except Exception:
			import logging
			logging.exception(f"Error eliminando línea {linea_id}")
			return False
