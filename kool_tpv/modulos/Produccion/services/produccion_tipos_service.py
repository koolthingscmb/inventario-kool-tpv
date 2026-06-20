"""Servicio para gestión de tipos de producto fabricable.

Contiene la clase `ProduccionTiposService` que expone métodos para gestionar
tipos con lógica de negocio, utilizando el repository para acceso a datos.
"""
from typing import List, Optional

from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.produccion.models.produccion_tipos_model import ProduccionTipo
from kool_tpv.modulos.produccion.repositories.produccion_tipos_repository import ProduccionTiposRepository


class ProduccionTiposService:
	"""Servicio de lógica de negocio para tipos de producto fabricable.

	Args:
		db: instancia de `Database` ya conectada.
	"""

	def __init__(self, db: Database):
		self.db = db
		self.repository = ProduccionTiposRepository(db)

	def obtener_todos(self) -> List[ProduccionTipo]:
		"""Obtener todos los tipos de producto.

		Returns:
			Lista de objetos ProduccionTipo ordenados por `orden`.
		"""
		return self.repository.get_todos()

	def obtener_activos(self) -> List[ProduccionTipo]:
		"""Obtener solo los tipos activos (para mostrar en UI).

		Returns:
			Lista de objetos ProduccionTipo con activo=1, ordenados por `orden`.
		"""
		return self.repository.get_activos()

	def obtener_por_id(self, tipo_id: int) -> Optional[ProduccionTipo]:
		"""Obtener un tipo por su ID.

		Args:
			tipo_id: ID del tipo.

		Returns:
			Objeto ProduccionTipo o None si no existe.
		"""
		return self.repository.get_por_id(tipo_id)

	def crear(self, nombre: str, descripcion: Optional[str] = None,
	          color: Optional[str] = None, icono: Optional[str] = None,
	          coste_base: float = 0.0, requiere_talla: int = 0,
	          requiere_color: int = 0, orden: int = 0) -> Optional[int]:
		"""Crear un nuevo tipo de producto.

		Args:
			nombre: Nombre del tipo.
			descripcion: Descripción opcional.
			color: Color hex para el chip (ej: "#FF5733").
			icono: Nombre o ruta de icono.
			coste_base: Coste base de fabricación.
			requiere_talla: 1 si requiere talla, 0 si no.
			requiere_color: 1 si requiere color, 0 si no.
			orden: Orden de visualización.

		Returns:
			ID del tipo creado o None si error.
		"""
		if not nombre or not nombre.strip():
			return None

		tipo = ProduccionTipo(
			nombre=nombre.strip(),
			descripcion=descripcion,
			color=color,
			icono=icono,
			coste_base=coste_base,
			requiere_talla=requiere_talla,
			requiere_color=requiere_color,
			activo=1,
			orden=orden
		)
		return self.repository.crear(tipo)

	def actualizar(self, tipo_id: int, nombre: str, descripcion: Optional[str] = None,
	               color: Optional[str] = None, icono: Optional[str] = None,
	               coste_base: float = 0.0, requiere_talla: int = 0,
	               requiere_color: int = 0, activo: int = 1,
	               orden: int = 0) -> bool:
		"""Actualizar un tipo existente.

		Args:
			tipo_id: ID del tipo a actualizar.
			nombre: Nuevo nombre del tipo.
			resto: Campos del tipo.

		Returns:
			True si OK, False si error.
		"""
		if not nombre or not nombre.strip():
			return False

		tipo = ProduccionTipo(
			id=tipo_id,
			nombre=nombre.strip(),
			descripcion=descripcion,
			color=color,
			icono=icono,
			coste_base=coste_base,
			requiere_talla=requiere_talla,
			requiere_color=requiere_color,
			activo=activo,
			orden=orden
		)
		return self.repository.actualizar(tipo)

	def eliminar(self, tipo_id: int) -> bool:
		"""Eliminar un tipo (soft delete: marca como inactivo).

		Args:
			tipo_id: ID del tipo a eliminar.

		Returns:
			True si OK, False si error.
		"""
		return self.repository.eliminar(tipo_id)

	def obtener_como_dict(self, solo_activos: bool = True) -> List[dict]:
		"""Obtener tipos como diccionarios (útil para UI con chips).

		Args:
			solo_activos: Si True, solo retorna tipos activos.

		Returns:
			Lista de diccionarios con claves: id, nombre, descripcion,
			color, icono, coste_base, requiere_talla, requiere_color, orden.
		"""
		tipos = self.repository.get_activos() if solo_activos else self.repository.get_todos()
		return [
			{
				"id": t.id,
				"nombre": t.nombre,
				"descripcion": t.descripcion,
				"color": t.color,
				"icono": t.icono,
				"coste_base": t.coste_base,
				"requiere_talla": t.requiere_talla,
				"requiere_color": t.requiere_color,
				"orden": t.orden
			}
			for t in tipos
		]
