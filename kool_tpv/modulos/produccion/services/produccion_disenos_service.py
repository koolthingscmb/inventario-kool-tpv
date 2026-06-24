"""Servicio para gestión de diseños de producción.

Contiene la clase `ProduccionDisenosService` que expone métodos para gestionar
diseños con lógica de negocio, utilizando el repository para acceso a datos.
"""
from typing import List, Optional

from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.produccion.models.produccion_diseno_model import ProduccionDiseno
from kool_tpv.modulos.produccion.repositories.produccion_disenos_repository import ProduccionDisenosRepository


class ProduccionDisenosService:
	"""Servicio de lógica de negocio para diseños de producción.

	Args:
		db: instancia de `Database` ya conectada.
	"""

	def __init__(self, db: Database):
		self.db = db
		self.repository = ProduccionDisenosRepository(db)

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
		"""Obtener el coste de un diseño para un tipo de producto específico.

		Args:
			codigo: Código del diseño.
			tipo_producto: Tipo de producto (camiseta, taza, gorra, etc).

		Returns:
			Coste en céntimos (0 si no existe el diseño o el tipo).
		"""
		diseno = self.repository.get_por_codigo(codigo)
		if not diseno:
			return 0

		# Mapear tipo de producto al campo correspondiente
		coste_map = {
			"camiseta": diseno.coste_camiseta,
			"taza": diseno.coste_taza,
			"gorra": diseno.coste_gorra,
			"calcetin": diseno.coste_calcetin,
			"libreta": diseno.coste_libreta,
			"poster": diseno.coste_poster,
			"cartera": diseno.coste_cartera,
		}
		return coste_map.get(tipo_producto.lower(), 0)

	def generar_codigo(self, coleccion: str) -> str:
		"""Generar código único para un nuevo diseño.

		Formato: COLECCION + número secuencial de 2 dígitos (ANIME01, ANIME02, GAME01...).

		Args:
			coleccion: Nombre de la colección.

		Returns:
			Código generado.
		"""
		prefijo = coleccion.strip().upper()[:10]
		max_num = self.repository.obtener_max_numero_coleccion(prefijo)
		return f"{prefijo}{max_num + 1:02d}"

	def crear(self, coleccion: str, nombre: str, sufijo: Optional[str] = None,
	          tipos: Optional[List[int]] = None, costes: Optional[dict] = None) -> Optional[str]:
		"""Crear un nuevo diseño.

		Args:
			coleccion: Colección del diseño.
			nombre: Nombre del diseño.
			sufijo: Sufijo opcional.
			tipos: Lista de IDs de tipos de producto (FK a tipos.id).
			costes: Diccionario con costes por tipo (camiseta, taza, etc) en céntimos.

		Returns:
			None si OK, o string con el error.
		"""
		if not coleccion or not nombre:
			return "Colección y nombre son obligatorios"

		coleccion_norm = coleccion.strip()
		nombre_norm = nombre.strip()
		sufijo_norm = sufijo.strip() if sufijo else None

		if self.repository.existe_diseno(coleccion_norm, nombre_norm, sufijo_norm):
			return "Ya existe un diseño con esa colección, nombre y sufijo"

		codigo = self.generar_codigo(coleccion_norm)
		costes = costes or {}
		diseno = ProduccionDiseno(
			codigo=codigo,
			coleccion=coleccion.strip(),
			nombre=nombre.strip(),
			sufijo=sufijo,
			tipos=tipos or [],
			coste_camiseta=costes.get("camiseta", 0),
			coste_taza=costes.get("taza", 0),
			coste_gorra=costes.get("gorra", 0),
			coste_calcetin=costes.get("calcetin", 0),
			coste_libreta=costes.get("libreta", 0),
			coste_poster=costes.get("poster", 0),
			coste_cartera=costes.get("cartera", 0),
			activo=1
		)
		ok = self.repository.crear(diseno)
		return None if ok else "Error guardando el diseño en la base de datos"

	def actualizar(self, codigo: str, coleccion: str, nombre: str, sufijo: Optional[str] = None,
	              tipos: Optional[List[int]] = None, costes: Optional[dict] = None) -> bool:
		"""Actualizar un diseño existente.

		Args:
			codigo: Código del diseño a actualizar.
			coleccion: Nueva colección.
			nombre: Nuevo nombre.
			sufijo: Nuevo sufijo.
			tipos: Lista de IDs de tipos de producto (FK a tipos.id).
			costes: Nuevos costes por tipo en céntimos.

		Returns:
			True si OK, False si error.
		"""
		if not codigo or not coleccion or not nombre:
			return False

		costes = costes or {}
		diseno = ProduccionDiseno(
			codigo=codigo.strip(),
			coleccion=coleccion.strip(),
			nombre=nombre.strip(),
			sufijo=sufijo,
			tipos=tipos or [],
			coste_camiseta=costes.get("camiseta", 0),
			coste_taza=costes.get("taza", 0),
			coste_gorra=costes.get("gorra", 0),
			coste_calcetin=costes.get("calcetin", 0),
			coste_libreta=costes.get("libreta", 0),
			coste_poster=costes.get("poster", 0),
			coste_cartera=costes.get("cartera", 0),
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
