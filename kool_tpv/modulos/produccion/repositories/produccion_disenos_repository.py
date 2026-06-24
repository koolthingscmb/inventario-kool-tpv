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

	def _get_tipos_para_disenos(self, codigos: List[str]) -> dict:
		"""Obtener un mapeo {codigo: [tipo_id, ...]} para una lista de diseños."""
		if not codigos:
			return {}
		placeholders = ', '.join(['?'] * len(codigos))
		query = f"SELECT diseno_codigo, tipo_id FROM produccion_disenos_tipos WHERE diseno_codigo IN ({placeholders})"
		rows = self.db.fetch_all(query, tuple(codigos))
		
		mapping = {c: [] for c in codigos}
		for dis_cod, tip_id in rows:
			if dis_cod in mapping:
				mapping[dis_cod].append(tip_id)
		return mapping

	def get_todos(self) -> List[ProduccionDiseno]:
		"""Obtener todos los diseños.

		Returns:
			Lista de objetos ProduccionDiseno.
		"""
		query = """
			SELECT codigo, coleccion, nombre, sufijo,
			       coste_camiseta, coste_taza, coste_gorra, coste_calcetin,
			       coste_libreta, coste_poster, coste_cartera, activo
			FROM produccion_disenos
			ORDER BY coleccion, nombre
		"""
		rows = self.db.fetch_all(query)
		codigos = [r[0] for r in rows]
		tipos_map = self._get_tipos_para_disenos(codigos)

		disenos: List[ProduccionDiseno] = []
		for row in rows:
			(codigo, coleccion, nombre, sufijo,
			 coste_camiseta, coste_taza, coste_gorra, coste_calcetin,
			 coste_libreta, coste_poster, coste_cartera, activo) = row
			disenos.append(ProduccionDiseno(
				codigo=codigo,
				coleccion=coleccion,
				nombre=nombre,
				sufijo=sufijo,
				tipos=tipos_map.get(codigo, []),
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
			SELECT codigo, coleccion, nombre, sufijo,
			       coste_camiseta, coste_taza, coste_gorra, coste_calcetin,
			       coste_libreta, coste_poster, coste_cartera, activo
			FROM produccion_disenos
			WHERE activo = 1
			ORDER BY coleccion, nombre
		"""
		rows = self.db.fetch_all(query)
		codigos = [r[0] for r in rows]
		tipos_map = self._get_tipos_para_disenos(codigos)

		disenos: List[ProduccionDiseno] = []
		for row in rows:
			(codigo, coleccion, nombre, sufijo,
			 coste_camiseta, coste_taza, coste_gorra, coste_calcetin,
			 coste_libreta, coste_poster, coste_cartera, activo) = row
			disenos.append(ProduccionDiseno(
				codigo=codigo,
				coleccion=coleccion,
				nombre=nombre,
				sufijo=sufijo,
				tipos=tipos_map.get(codigo, []),
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
			SELECT codigo, coleccion, nombre, sufijo,
			       coste_camiseta, coste_taza, coste_gorra, coste_calcetin,
			       coste_libreta, coste_poster, coste_cartera, activo
			FROM produccion_disenos
			WHERE codigo = ?
		"""
		rows = self.db.fetch_all(query, (codigo,))

		if not rows:
			return None

		tipos_map = self._get_tipos_para_disenos([codigo])

		(codigo, coleccion, nombre, sufijo,
		 coste_camiseta, coste_taza, coste_gorra, coste_calcetin,
		 coste_libreta, coste_poster, coste_cartera, activo) = rows[0]
		return ProduccionDiseno(
			codigo=codigo,
			coleccion=coleccion,
			nombre=nombre,
			sufijo=sufijo,
			tipos=tipos_map.get(codigo, []),
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
		"""Buscar diseños por código, nombre o colección de forma simple y efectiva."""
		filtro = filtro.strip().lower()
		if not filtro:
			return []

		# Buscamos por el término completo y por palabras individuales si hay varias
		palabras = filtro.split()
		condiciones = []
		params = []

		# Término completo
		condiciones.append("(codigo LIKE ? OR nombre LIKE ? OR coleccion LIKE ?)")
		term_completo = f"%{filtro}%"
		params.extend([term_completo, term_completo, term_completo])

		# Palabras individuales (para que 'Gear 6' encuentre 'Gear 5')
		if len(palabras) > 1:
			for p in palabras:
				if len(p) > 2:
					condiciones.append("(nombre LIKE ? OR coleccion LIKE ?)")
					term_p = f"%{p}%"
					params.extend([term_p, term_p])

		query = f"""
			SELECT DISTINCT codigo, coleccion, nombre, sufijo,
			       coste_camiseta, coste_taza, coste_gorra, coste_calcetin,
			       coste_libreta, coste_poster, coste_cartera, activo
			FROM produccion_disenos
			WHERE activo = 1
			  AND ({" OR ".join(condiciones)})
			ORDER BY coleccion, nombre
		"""
		
		rows = self.db.fetch_all(query, tuple(params))
		if not rows:
			return []

		codigos = [r[0] for r in rows]
		tipos_map = self._get_tipos_para_disenos(codigos)

		disenos: List[ProduccionDiseno] = []
		for row in rows:
			(codigo, coleccion, nombre, sufijo,
			 coste_camiseta, coste_taza, coste_gorra, coste_calcetin,
			 coste_libreta, coste_poster, coste_cartera, activo) = row
			disenos.append(ProduccionDiseno(
				codigo=codigo,
				coleccion=coleccion,
				nombre=nombre,
				sufijo=sufijo,
				tipos=tipos_map.get(codigo, []),
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
			# 1. Insertar diseño
			query = """
				INSERT INTO produccion_disenos
				(codigo, coleccion, nombre, sufijo,
				 coste_camiseta, coste_taza, coste_gorra, coste_calcetin,
				 coste_libreta, coste_poster, coste_cartera, activo)
				VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
			"""
			self.db.execute_query(query, (
				diseno.codigo, diseno.coleccion, diseno.nombre, diseno.sufijo,
				diseno.coste_camiseta, diseno.coste_taza,
				diseno.coste_gorra, diseno.coste_calcetin, diseno.coste_libreta,
				diseno.coste_poster, diseno.coste_cartera, diseno.activo
			))

			# 2. Insertar tipos
			if diseno.tipos:
				for tipo_id in diseno.tipos:
					self.db.execute_query(
						"INSERT INTO produccion_disenos_tipos (diseno_codigo, tipo_id) VALUES (?, ?)",
						(diseno.codigo, tipo_id)
					)

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
			# 1. Actualizar diseño
			query = """
				UPDATE produccion_disenos
				SET coleccion = ?, nombre = ?, sufijo = ?,
				    coste_camiseta = ?, coste_taza = ?, coste_gorra = ?,
				    coste_calcetin = ?, coste_libreta = ?, coste_poster = ?,
				    coste_cartera = ?, activo = ?
				WHERE codigo = ?
			"""
			self.db.execute_query(query, (
				diseno.coleccion, diseno.nombre, diseno.sufijo,
				diseno.coste_camiseta, diseno.coste_taza, diseno.coste_gorra,
				diseno.coste_calcetin, diseno.coste_libreta, diseno.coste_poster,
				diseno.coste_cartera, diseno.activo, diseno.codigo
			))

			# 2. Actualizar tipos (borrar y re-insertar)
			self.db.execute_query("DELETE FROM produccion_disenos_tipos WHERE diseno_codigo = ?", (diseno.codigo,))
			if diseno.tipos:
				for tipo_id in diseno.tipos:
					self.db.execute_query(
						"INSERT INTO produccion_disenos_tipos (diseno_codigo, tipo_id) VALUES (?, ?)",
						(diseno.codigo, tipo_id)
					)

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

	def obtener_max_numero_coleccion(self, prefijo: str) -> int:
		"""Obtener el número secuencial máximo para un prefijo de colección.

		Args:
			prefijo: Prefijo del código (ej: 'ANIME').

		Returns:
			Número máximo encontrado (0 si no hay ninguno).
		"""
		try:
			rows = self.db.fetch_all(
				"SELECT codigo FROM produccion_disenos WHERE codigo LIKE ? ORDER BY codigo",
				(f"{prefijo}%",)
			)
			max_num = 0
			for row in rows:
				try:
					sufijo = row[0][len(prefijo):]
					n = int(sufijo)
					if n > max_num:
						max_num = n
				except (ValueError, IndexError):
					pass
			return max_num
		except Exception:
			import logging
			logging.exception(f"Error obteniendo max número para prefijo {prefijo}")
			return 0

	def existe_diseno(self, coleccion: str, nombre: str, sufijo: Optional[str] = None) -> bool:
		"""Comprobar si ya existe un diseño con esa colección, nombre y sufijo.

		Args:
			coleccion: Colección del diseño.
			nombre: Nombre del diseño.
			sufijo: Sufijo (opcional).

		Returns:
			True si ya existe, False si no.
		"""
		try:
			if sufijo:
				rows = self.db.fetch_all(
					"SELECT 1 FROM produccion_disenos WHERE LOWER(coleccion) = LOWER(?) AND LOWER(nombre) = LOWER(?) AND LOWER(sufijo) = LOWER(?) AND activo = 1 LIMIT 1",
					(coleccion, nombre, sufijo)
				)
			else:
				rows = self.db.fetch_all(
					"SELECT 1 FROM produccion_disenos WHERE LOWER(coleccion) = LOWER(?) AND LOWER(nombre) = LOWER(?) AND (sufijo IS NULL OR sufijo = '') AND activo = 1 LIMIT 1",
					(coleccion, nombre)
				)
			return len(rows) > 0
		except Exception:
			import logging
			logging.exception("Error comprobando existencia de diseño")
			return False
