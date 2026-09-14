"""Servicio para gestión de colores de producción.

Contiene la clase `ProduccionColoresService` que expone métodos para gestionar
colores con lógica de negocio, utilizando el repository para acceso a datos.
"""
from typing import List, Optional

from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.produccion.models.produccion_color_model import ProduccionColor
from kool_tpv.modulos.produccion.repositories.produccion_colores_repository import ProduccionColoresRepository


class ProduccionColoresService:
	"""Servicio de lógica de negocio para colores de producción.

	Args:
		db: instancia de `Database` ya conectada.
	"""

	def __init__(self, db: Database):
		self.db = db
		self.repository = ProduccionColoresRepository(db)

	def obtener_todos(self) -> List[ProduccionColor]:
		"""Obtener todos los colores.

		Returns:
			Lista de objetos ProduccionColor.
		"""
		return self.repository.get_todos()

	def obtener_activos(self) -> List[ProduccionColor]:
		"""Obtener solo los colores activos (para mostrar en UI).

		Returns:
			Lista de objetos ProduccionColor con activo=1.
		"""
		return self.repository.get_activos()

	def obtener_por_id(self, color_id: int) -> Optional[ProduccionColor]:
		"""Obtener un color por su ID.

		Args:
			color_id: ID del color.

		Returns:
			Objeto ProduccionColor o None si no existe.
		"""
		return self.repository.get_por_id(color_id)

	def crear(self, nombre: str, codigo_hex: Optional[str] = None, orden: int = 0) -> bool:
		"""Crear un nuevo color."""
		if not nombre or not nombre.strip():
			return False

		color = ProduccionColor(
			nombre=nombre.strip(),
			codigo_hex=codigo_hex,
			orden=orden
		)
		return self.repository.crear(color)

	def actualizar(self, color_id: int, nombre: str, codigo_hex: Optional[str] = None, orden: int = 0) -> bool:
		"""Actualizar un color existente."""
		if not nombre or not nombre.strip():
			return False

		color = ProduccionColor(
			id=color_id,
			nombre=nombre.strip(),
			codigo_hex=codigo_hex,
			orden=orden
		)
		return self.repository.actualizar(color)

	def eliminar(self, color_id: int) -> bool:
		"""Eliminar un color."""
		return self.repository.eliminar(color_id)

	def obtener_por_tipo_3d(self, tipo_id: int, variante_id: Optional[int] = None) -> List[ProduccionColor]:
		"""Obtener colores asignados a un tipo o variante (tabla stock base)."""
		return self.repository.get_por_tipo_3d(tipo_id, variante_id)

	def mover_orden(self, color_id: int, direccion: str) -> bool:
		"""Mover un color arriba o abajo en el orden.
		
		Args:
			color_id: ID del color a mover.
			direccion: 'up' o 'down'.
		"""
		c_actual = self.repository.get_por_id(color_id)
		if not c_actual:
			return False
			
		# Obtener todos los colores ordenados
		colores = self.repository.get_todos()
		
		# Encontrar índice del actual
		idx = -1
		for i, c in enumerate(colores):
			if c.id == color_id:
				idx = i
				break
				
		if idx == -1:
			return False
			
		# Determinar objetivo
		if direccion == 'up':
			if idx == 0: return True
			c_otro = colores[idx-1]
		else:
			if idx == len(colores) - 1: return True
			c_otro = colores[idx+1]
			
		# Intercambiar orden usando transacción profesional
		from kool_tpv.base_datos.db_wrapper import Database
		with self.db.transaction():
			orden_actual = c_actual.orden
			orden_otro = c_otro.orden
			
			# Si ambos son iguales, forzar ordenación secuencial primero
			if orden_actual == orden_otro:
				for i, c in enumerate(colores):
					self.repository.actualizar_orden(c.id, i * 10)
				# Re-ejecutar lógica con órdenes nuevos
				return self.mover_orden(color_id, direccion)
			
			self.repository.actualizar_orden(c_actual.id, orden_otro)
			self.repository.actualizar_orden(c_otro.id, orden_actual)
			
		return True

	def obtener_como_dict(self, solo_activos: bool = True) -> List[dict]:
		"""Obtener colores como diccionarios (útil para UI con comboboxes)."""
		colores = self.repository.get_activos() if solo_activos else self.repository.get_todos()
		return [
			{
				"id": c.id,
				"nombre": c.nombre,
				"codigo_hex": c.codigo_hex,
				"orden": c.orden
			}
			for c in colores
		]
