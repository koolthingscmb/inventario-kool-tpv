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

	def crear(self, nombre: str, codigo_hex: Optional[str] = None) -> bool:
		"""Crear un nuevo color.

		Args:
			nombre: Nombre del color.
			codigo_hex: Valor hexadecimal del color (ej: "#FF5733").

		Returns:
			True si OK, False si error.
		"""
		# Validar que el nombre no esté vacío
		if not nombre or not nombre.strip():
			return False

		color = ProduccionColor(
			nombre=nombre.strip(),
			codigo_hex=codigo_hex
		)
		return self.repository.crear(color)

	def actualizar(self, color_id: int, nombre: str, codigo_hex: Optional[str] = None) -> bool:
		"""Actualizar un color existente.

		Args:
			color_id: ID del color a actualizar.
			nombre: Nuevo nombre del color.
			codigo_hex: Nuevo valor hexadecimal del color.

		Returns:
			True si OK, False si error.
		"""
		# Validar que el nombre no esté vacío
		if not nombre or not nombre.strip():
			return False

		color = ProduccionColor(
			id=color_id,
			nombre=nombre.strip(),
			codigo_hex=codigo_hex
		)
		return self.repository.actualizar(color)

	def eliminar(self, color_id: int) -> bool:
		"""Eliminar un color (soft delete: marca como inactivo).

		Args:
			color_id: ID del color a eliminar.

		Returns:
			True si OK, False si error.
		"""
		return self.repository.eliminar(color_id)

	def obtener_por_tipo_3d(self, tipo_id: int, variante_id: Optional[int] = None, solo_con_stock: bool = True) -> List[ProduccionColor]:
		"""Obtener colores asignados a un tipo o variante (tabla stock base o matriz)."""
		return self.repository.get_por_tipo_3d(tipo_id, variante_id, solo_con_stock)

	def obtener_como_dict(self, solo_activos: bool = True) -> List[dict]:
		"""Obtener colores como diccionarios (útil para UI con comboboxes).

		Args:
			solo_activos: Si True, solo retorna colores activos.

		Returns:
			Lista de diccionarios con claves: id, nombre, codigo_hex.
		"""
		colores = self.repository.get_activos() if solo_activos else self.repository.get_todos()
		return [
			{
				"id": c.id,
				"nombre": c.nombre,
				"codigo_hex": c.codigo_hex
			}
			for c in colores
		]
