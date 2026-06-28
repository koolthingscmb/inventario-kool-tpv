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

	def obtener_coste_por_tipo(self, codigo: str, tipo_producto: str) -> int:
		"""Obtener el coste de un diseño para un tipo de producto específico (compatibilidad).

		Busca en la lista de costes dinámicos del diseño. Resuelve el tipo_id
		a partir del nombre del tipo.

		Args:
			codigo: Código del diseño.
			tipo_producto: Tipo de producto (camiseta, taza, gorra, etc).

		Returns:
			Coste en céntimos (0 si no existe el diseño o el tipo).
		"""
		diseno = self.repository.get_por_codigo(codigo)
		if not diseno or not diseno.costes:
			return 0

		# Resolver tipo_id desde el nombre
		rows = self.db.fetch_all(
			"SELECT id FROM tipos WHERE LOWER(nombre) = LOWER(?) AND activo = 1",
			(tipo_producto,)
		)
		if not rows:
			return 0
		tipo_id = rows[0][0]

		return self.obtener_coste(codigo, tipo_id)

	def obtener_coste(self, codigo: str, tipo_id: int, variante_id: Optional[int] = None,
	                 talla_id: Optional[int] = None) -> int:
		"""Obtener el coste más específico de un diseño dado tipo, variante y talla.

		Busca en la lista de costes del diseño y retorna el match más específico.

		Args:
			codigo: Código del diseño.
			tipo_id: ID del tipo de producto.
			variante_id: ID de la variante (opcional).
			talla_id: ID de la talla (opcional).

		Returns:
			Coste en céntimos (0 si no existe el diseño o no hay coste configurado).
		"""
		diseno = self.repository.get_por_codigo(codigo)
		if not diseno or not diseno.costes:
			return 0

		best = None
		best_score = -1
		for c in diseno.costes:
			if c.tipo_id != tipo_id:
				continue
			score = 0
			if c.variante_id is not None and c.variante_id == variante_id:
				score += 1
			elif c.variante_id is not None:
				continue
			if c.talla_id is not None and c.talla_id == talla_id:
				score += 1
			elif c.talla_id is not None:
				continue
			if score > best_score:
				best = c
				best_score = score
		return best.coste if best else 0

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
	          tipos: Optional[List[int]] = None, costes: Optional[dict] = None,
	          lista_costes: Optional[List[DisenoCoste]] = None) -> Optional[str]:
		"""Crear un nuevo diseño.

		Args:
			coleccion_id: ID de la colección del diseño.
			nombre: Nombre del diseño.
			sufijo_id: ID del sufijo opcional.
			tipos: Lista de IDs de tipos de producto (FK a tipos.id).
			costes: Diccionario con costes por tipo (camiseta, taza, etc) en céntimos (compatibilidad).
			lista_costes: Lista de DisenoCoste para la tabla nueva de costes dinámicos.

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
			costes=lista_costes or [],
			activo=1
		)
		ok = self.repository.crear(diseno)
		return None if ok else "Error guardando el diseño en la base de datos"

	def actualizar(self, codigo: str, coleccion_id: int, nombre: str, sufijo_id: Optional[int] = None,
	              tipos: Optional[List[int]] = None, costes: Optional[dict] = None,
	              lista_costes: Optional[List[DisenoCoste]] = None) -> bool:
		"""Actualizar un diseño existente.

		Args:
			codigo: Código del diseño a actualizar.
			coleccion_id: ID de la colección.
			nombre: Nuevo nombre.
			sufijo_id: ID del sufijo.
			tipos: Lista de IDs de tipos de producto (FK a tipos.id).
			costes: Nuevos costes por tipo en céntimos (compatibilidad).
			lista_costes: Lista de DisenoCoste para la tabla nueva de costes dinámicos.

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
			costes=lista_costes or [],
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
