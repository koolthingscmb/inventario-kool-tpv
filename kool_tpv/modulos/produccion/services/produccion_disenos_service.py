"""Servicio para gestión de diseños de producción.

Contiene la clase `ProduccionDisenosService` que expone métodos para gestionar
diseños con lógica de negocio, utilizando el repository para acceso a datos.
"""
from typing import List, Optional

from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.produccion.models.produccion_diseno_model import ProduccionDiseno, DisenoCoste
from kool_tpv.modulos.produccion.repositories.produccion_disenos_repository import ProduccionDisenosRepository
from kool_tpv.modulos.produccion.repositories.produccion_colecciones_repository import ProduccionColeccionesRepository
from kool_tpv.modulos.produccion.repositories.produccion_sufijos_repository import ProduccionSufijosRepository


class ProduccionDisenosService:
	"""Servicio de lógica de negocio para diseños de producción.

	Args:
		db: instancia de `Database` ya conectada.
	"""

	def __init__(self, db: Database):
		self.db = db
		self.repository = ProduccionDisenosRepository(db)
		self.colecciones_repo = ProduccionColeccionesRepository(db)
		self.sufijos_repo = ProduccionSufijosRepository(db)

	def obtener_todos(self) -> List[ProduccionDiseno]:
		"""Obtener todos los diseños.

		Returns:
			Lista de objetos ProduccionDiseno.
		"""
		return self.repository.get_todos()

	def obtener_activos(self) -> List[ProduccionDiseno]:
		"""Obtener solo los diseños activos.

		Returns:
			Lista de objetos ProduccionDiseno con activo=1.
		"""
		return self.repository.get_activos()

	def obtener_por_codigo(self, codigo: str) -> Optional[ProduccionDiseno]:
		"""Obtener un diseño por su código.

		Args:
			codigo: Código del diseño.

		Returns:
			Objeto ProduccionDiseno o None si no existe.
		"""
		return self.repository.get_por_codigo(codigo)

	def buscar(self, filtro: str) -> List[ProduccionDiseno]:
		"""Buscar diseños por código, nombre o colección.

		Args:
			filtro: Término de búsqueda (coincidencia parcial).

		Returns:
			Lista de objetos ProduccionDiseno que coinciden.
		"""
		return self.repository.buscar(filtro)

	def generar_codigo(self, coleccion_id: int) -> str:
		"""Generar código único para un nuevo diseño.

		Formato: COLECCION + número secuencial de 2 dígitos (ANIME01, ANIME02, GAME01...).

		Args:
			coleccion_id: ID de la colección.

		Returns:
			Código generado.
		"""
		coleccion = self.colecciones_repo.get_por_id(coleccion_id)
		prefijo = (coleccion.nombre if coleccion else "DES").strip().upper()[:10]
		max_num = self.repository.obtener_max_numero_coleccion(prefijo)
		return f"{prefijo}{max_num + 1:02d}"

	def crear(self, coleccion_id: int, nombre: str, sufijo_id: Optional[int] = None,
	          tipos: Optional[List[int]] = None) -> Optional[str]:
		"""Crear un nuevo diseño.

		Args:
			coleccion_id: ID de la colección del diseño.
			nombre: Nombre del diseño.
			sufijo_id: ID del sufijo opcional.
			tipos: Lista de IDs de tipos de producto (FK a tipos.id).

		Returns:
			None si OK, o string con el error.
		"""
		if not coleccion_id or not nombre:
			return "Colección y nombre son obligatorios"

		nombre_norm = nombre.strip()

		if self.repository.existe_diseno(coleccion_id, nombre_norm, sufijo_id):
			return "Ya existe un diseño con esa colección, nombre y sufijo"

		codigo = self.generar_codigo(coleccion_id)
		diseno = ProduccionDiseno(
			codigo=codigo,
			coleccion_id=coleccion_id,
			nombre=nombre.strip(),
			sufijo_id=sufijo_id,
			tipos=tipos or [],
			activo=1
		)
		ok = self.repository.crear(diseno)
		return None if ok else "Error guardando el diseño en la base de datos"

	def actualizar(self, codigo: str, coleccion_id: int, nombre: str, sufijo_id: Optional[int] = None,
	              tipos: Optional[List[int]] = None) -> bool:
		"""Actualizar un diseño existente.

		Args:
			codigo: Código del diseño a actualizar.
			coleccion_id: ID de la colección.
			nombre: Nuevo nombre.
			sufijo_id: ID del sufijo.
			tipos: Lista de IDs de tipos de producto (FK a tipos.id).

		Returns:
			True si OK, False si error.
		"""
		if not codigo or not coleccion_id or not nombre:
			return False

		diseno = ProduccionDiseno(
			codigo=codigo.strip(),
			coleccion_id=coleccion_id,
			nombre=nombre.strip(),
			sufijo_id=sufijo_id,
			tipos=tipos or [],
			activo=1
		)
		return self.repository.actualizar(diseno)

	def eliminar(self, codigo: str) -> bool:
		"""Eliminar un diseño (soft delete: marca como inactivo).

		Args:
			codigo: Código del diseño a eliminar.

		Returns:
			True si OK, False si error.
		"""
		return self.repository.eliminar(codigo)

	def obtener_estadisticas_disenos(self, codigos: List[str]) -> dict:
		"""Obtener estadísticas (total producido y costes por método) para una lista de diseños.

		Args:
			codigos: Lista de códigos de diseño.

		Returns:
			Diccionario {codigo: {total_producido: int, costes_metodos: list}}
		"""
		return self.repository.get_estadisticas_disenos(codigos)

	def obtener_por_coleccion(self, coleccion_id: int) -> List[ProduccionDiseno]:
		"""Obtener diseños activos por ID de colección."""
		return self.repository.get_por_coleccion(coleccion_id)

	def obtener_por_sufijo(self, sufijo_id: int) -> List[ProduccionDiseno]:
		"""Obtener diseños activos por ID de sufijo."""
		return self.repository.get_por_sufijo(sufijo_id)
