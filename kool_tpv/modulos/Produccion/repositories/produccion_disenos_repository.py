"""Acceso a datos para la tabla `produccion_disenos`.

Contiene la clase `ProduccionDisenosRepository` que expone métodos para consultar
y gestionar diseños desde la base de datos usando el wrapper
`kool_tpv.base_datos.db_wrapper.Database`.
"""
from typing import List, Optional

from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.produccion.models.produccion_diseno_model import ProduccionDiseno


class ProduccionDisenosRepository:
	"""Data access object (DAO) para `produccion_disenos`.

	Args:
		db: instancia de `Database` ya conectada.
	"""

	def __init__(self, db: Database):
		self.db = db

	def get_todos(self) -> List[ProduccionDiseno]:
		"""Obtener todos los diseños.

		Returns:
			Lista de objetos ProduccionDiseno.
		"""
		query = """
			SELECT codigo, coleccion, nombre, variante, tipo_producto,
			       coste_camiseta, coste_taza, coste_gorra, coste_calcetin,
			       coste_libreta, coste_poster, coste_cartera, activo
			FROM produccion_disenos
			ORDER BY coleccion, nombre
		"""
		rows = self.db.fetch_all(query)

		disenos: List[ProduccionDiseno] = []
		for row in rows:
			(codigo, coleccion, nombre, variante, tipo_producto,
			 coste_camiseta, coste_taza, coste_gorra, coste_calcetin,
			 coste_libreta, coste_poster, coste_cartera, activo) = row
			disenos.append(ProduccionDiseno(
				codigo=codigo,
				coleccion=coleccion,
				nombre=nombre,
				variante=variante,
				tipo_producto=tipo_producto,
				coste_camiseta=coste_camiseta or 0,
				coste_taza=coste_taza or 0,
				coste_gorra=coste_gorra or 0,
				coste_calcetin=coste_calcetin or 0,
				coste_libreta=coste_libreta or 0,
				coste_poster=coste_poster or 0,
				coste_cartera=coste_cartera or 0,
				activo=activo
			))
		return disenos

	def get_activos(self) -> List[ProduccionDiseno]:
		"""Obtener solo los diseños activos.

		Returns:
			Lista de objetos ProduccionDiseno con activo=1.
		"""
		query = """
			SELECT codigo, coleccion, nombre, variante, tipo_producto,
			       coste_camiseta, coste_taza, coste_gorra, coste_calcetin,
			       coste_libreta, coste_poster, coste_cartera, activo
			FROM produccion_disenos
			WHERE activo = 1
			ORDER BY coleccion, nombre
		"""
		rows = self.db.fetch_all(query)

		disenos: List[ProduccionDiseno] = []
		for row in rows:
			(codigo, coleccion, nombre, variante, tipo_producto,
			 coste_camiseta, coste_taza, coste_gorra, coste_calcetin,
			 coste_libreta, coste_poster, coste_cartera, activo) = row
			disenos.append(ProduccionDiseno(
				codigo=codigo,
				coleccion=coleccion,
				nombre=nombre,
				variante=variante,
				tipo_producto=tipo_producto,
				coste_camiseta=coste_camiseta or 0,
				coste_taza=coste_taza or 0,
				coste_gorra=coste_gorra or 0,
				coste_calcetin=coste_calcetin or 0,
				coste_libreta=coste_libreta or 0,
				coste_poster=coste_poster or 0,
				coste_cartera=coste_cartera or 0,
				activo=activo
			))
		return disenos

	def get_por_codigo(self, codigo: str) -> Optional[ProduccionDiseno]:
		"""Obtener un diseño por su código.

		Args:
			codigo: Código del diseño.

		Returns:
			Objeto ProduccionDiseno o None si no existe.
		"""
		query = """
			SELECT codigo, coleccion, nombre, variante, tipo_producto,
			       coste_camiseta, coste_taza, coste_gorra, coste_calcetin,
			       coste_libreta, coste_poster, coste_cartera, activo
			FROM produccion_disenos
			WHERE codigo = ?
		"""
		rows = self.db.fetch_all(query, (codigo,))

		if not rows:
			return None

		(codigo, coleccion, nombre, variante, tipo_producto,
		 coste_camiseta, coste_taza, coste_gorra, coste_calcetin,
		 coste_libreta, coste_poster, coste_cartera, activo) = rows[0]
		return ProduccionDiseno(
			codigo=codigo,
			coleccion=coleccion,
			nombre=nombre,
			variante=variante,
			tipo_producto=tipo_producto,
			coste_camiseta=coste_camiseta or 0,
			coste_taza=coste_taza or 0,
			coste_gorra=coste_gorra or 0,
			coste_calcetin=coste_calcetin or 0,
			coste_libreta=coste_libreta or 0,
			coste_poster=coste_poster or 0,
			coste_cartera=coste_cartera or 0,
			activo=activo
		)

	def buscar(self, filtro: str) -> List[ProduccionDiseno]:
		"""Buscar diseños por código, nombre o colección.

		Args:
			filtro: Término de búsqueda (coincidencia parcial).

		Returns:
			Lista de objetos ProduccionDiseno que coinciden.
		"""
		term = f"%{filtro}%"
		query = """
			SELECT codigo, coleccion, nombre, variante, tipo_producto,
			       coste_camiseta, coste_taza, coste_gorra, coste_calcetin,
			       coste_libreta, coste_poster, coste_cartera, activo
			FROM produccion_disenos
			WHERE activo = 1
			  AND (codigo LIKE ? OR nombre LIKE ? OR coleccion LIKE ?)
			ORDER BY coleccion, nombre
		"""
		rows = self.db.fetch_all(query, (term, term, term))

		disenos: List[ProduccionDiseno] = []
		for row in rows:
			(codigo, coleccion, nombre, variante, tipo_producto,
			 coste_camiseta, coste_taza, coste_gorra, coste_calcetin,
			 coste_libreta, coste_poster, coste_cartera, activo) = row
			disenos.append(ProduccionDiseno(
				codigo=codigo,
				coleccion=coleccion,
				nombre=nombre,
				variante=variante,
				tipo_producto=tipo_producto,
				coste_camiseta=coste_camiseta or 0,
				coste_taza=coste_taza or 0,
				coste_gorra=coste_gorra or 0,
				coste_calcetin=coste_calcetin or 0,
				coste_libreta=coste_libreta or 0,
				coste_poster=coste_poster or 0,
				coste_cartera=coste_cartera or 0,
				activo=activo
			))
		return disenos

	def crear(self, diseno: ProduccionDiseno) -> bool:
		"""Crear un nuevo diseño.

		Args:
			diseno: Objeto ProduccionDiseno con los datos.

		Returns:
			True si OK, False si error.
		"""
		try:
			query = """
				INSERT INTO produccion_disenos
				(codigo, coleccion, nombre, variante, tipo_producto,
				 coste_camiseta, coste_taza, coste_gorra, coste_calcetin,
				 coste_libreta, coste_poster, coste_cartera, activo)
				VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
			"""
			self.db.execute_query(query, (
				diseno.codigo, diseno.coleccion, diseno.nombre, diseno.variante,
				diseno.tipo_producto, diseno.coste_camiseta, diseno.coste_taza,
				diseno.coste_gorra, diseno.coste_calcetin, diseno.coste_libreta,
				diseno.coste_poster, diseno.coste_cartera, diseno.activo
			))
			return True
		except Exception:
			import logging
			logging.exception("Error creando diseño")
			return False

	def actualizar(self, diseno: ProduccionDiseno) -> bool:
		"""Actualizar un diseño existente.

		Args:
			diseno: Objeto ProduccionDiseno con los datos (debe tener código).

		Returns:
			True si OK, False si error.
		"""
		try:
			query = """
				UPDATE produccion_disenos
				SET coleccion = ?, nombre = ?, variante = ?, tipo_producto = ?,
				    coste_camiseta = ?, coste_taza = ?, coste_gorra = ?,
				    coste_calcetin = ?, coste_libreta = ?, coste_poster = ?,
				    coste_cartera = ?, activo = ?
				WHERE codigo = ?
			"""
			self.db.execute_query(query, (
				diseno.coleccion, diseno.nombre, diseno.variante, diseno.tipo_producto,
				diseno.coste_camiseta, diseno.coste_taza, diseno.coste_gorra,
				diseno.coste_calcetin, diseno.coste_libreta, diseno.coste_poster,
				diseno.coste_cartera, diseno.activo, diseno.codigo
			))
			return True
		except Exception:
			import logging
			logging.exception(f"Error actualizando diseño {diseno.codigo}")
			return False

	def eliminar(self, codigo: str) -> bool:
		"""Eliminar un diseño (soft delete: marcar como inactivo).

		Args:
			codigo: Código del diseño a eliminar.

		Returns:
			True si OK, False si error.
		"""
		try:
			query = "UPDATE produccion_disenos SET activo = 0 WHERE codigo = ?"
			self.db.execute_query(query, (codigo,))
			return True
		except Exception:
			import logging
			logging.exception(f"Error eliminando diseño {codigo}")
			return False
