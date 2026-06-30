"""Acceso a datos para la tabla `produccion_disenos`.

Contiene la clase `ProduccionDisenosRepository` que expone métodos para consultar
y gestionar diseños desde la base de datos usando el wrapper
`kool_tpv.base_datos.db_wrapper.Database`.
"""
from typing import List, Optional

from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.produccion.models.produccion_diseno_model import ProduccionDiseno, DisenoCoste


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

	def _get_costes_para_disenos(self, codigos: List[str]) -> dict:
		"""Obtener un mapeo {codigo: [DisenoCoste, ...]} para una lista de diseños."""
		if not codigos:
			return {}
		placeholders = ', '.join(['?'] * len(codigos))
		query = f"""
			SELECT diseno_codigo, tipo_id, variante_id, talla_id, coste
			FROM produccion_disenos_costes
			WHERE diseno_codigo IN ({placeholders})
		"""
		rows = self.db.fetch_all(query, tuple(codigos))
		
		mapping = {c: [] for c in codigos}
		for row in rows:
			dis_cod = row[0]
			if dis_cod in mapping:
				mapping[dis_cod].append(DisenoCoste(
					diseno_codigo=row[0],
					tipo_id=row[1],
					variante_id=row[2],
					talla_id=row[3],
					coste=row[4] or 0
				))
		return mapping

	def get_todos(self) -> List[ProduccionDiseno]:
		"""Obtener todos los diseños.

		Returns:
			Lista de objetos ProduccionDiseno.
		"""
		query = """
			SELECT d.codigo, d.coleccion_id, d.nombre, d.sufijo_id, d.activo
			FROM produccion_disenos d
			ORDER BY (SELECT nombre FROM produccion_colecciones WHERE id = d.coleccion_id), d.nombre
		"""
		rows = self.db.fetch_all(query)
		codigos = [r[0] for r in rows]
		tipos_map = self._get_tipos_para_disenos(codigos)

		disenos: List[ProduccionDiseno] = []
		for row in rows:
			(codigo, coleccion_id, nombre, sufijo_id, activo) = row
			disenos.append(ProduccionDiseno(
				codigo=codigo,
				coleccion_id=coleccion_id or 0,
				nombre=nombre,
				sufijo_id=sufijo_id,
				tipos=tipos_map.get(codigo, []),
				activo=activo
			))
		return disenos

	def get_activos(self) -> List[ProduccionDiseno]:
		"""Obtener solo los diseños activos.

		Returns:
			Lista de objetos ProduccionDiseno con activo=1.
		"""
		query = """
			SELECT d.codigo, d.coleccion_id, d.nombre, d.sufijo_id, d.activo
			FROM produccion_disenos d
			WHERE d.activo = 1
			ORDER BY (SELECT nombre FROM produccion_colecciones WHERE id = d.coleccion_id), d.nombre
		"""
		rows = self.db.fetch_all(query)
		codigos = [r[0] for r in rows]
		tipos_map = self._get_tipos_para_disenos(codigos)

		disenos: List[ProduccionDiseno] = []
		for row in rows:
			(codigo, coleccion_id, nombre, sufijo_id, activo) = row
			disenos.append(ProduccionDiseno(
				codigo=codigo,
				coleccion_id=coleccion_id or 0,
				nombre=nombre,
				sufijo_id=sufijo_id,
				tipos=tipos_map.get(codigo, []),
				activo=activo
			))
		return disenos

	def get_por_codigo(self, codigo: str) -> Optional[ProduccionDiseno]:
		"""Obtener un diseño por su código."""
		query = """
			SELECT codigo, coleccion_id, nombre, sufijo_id, activo
			FROM produccion_disenos
			WHERE codigo = ?
		"""
		rows = self.db.fetch_all(query, (codigo,))

		if not rows:
			return None

		tipos_map = self._get_tipos_para_disenos([codigo])

		(codigo, coleccion_id, nombre, sufijo_id, activo) = rows[0]
		return ProduccionDiseno(
			codigo=codigo,
			coleccion_id=coleccion_id or 0,
			nombre=nombre,
			sufijo_id=sufijo_id,
			tipos=tipos_map.get(codigo, []),
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
		condiciones.append("d.nombre LIKE ?")
		term_completo = f"%{filtro}%"
		params.append(term_completo)

		# Palabras individuales (para que 'Gear 6' encuentre 'Gear 5')
		if len(palabras) > 1:
			for p in palabras:
				if len(p) > 2:
					condiciones.append("d.nombre LIKE ?")
					term_p = f"%{p}%"
					params.append(term_p)

		query = f"""
			SELECT DISTINCT d.codigo, d.coleccion_id, d.nombre, d.sufijo_id, d.activo
			FROM produccion_disenos d
			LEFT JOIN produccion_colecciones c ON c.id = d.coleccion_id
			WHERE d.activo = 1
			  AND ({" OR ".join(condiciones)})
			ORDER BY c.nombre, d.nombre
		"""
		
		rows = self.db.fetch_all(query, tuple(params))
		if not rows:
			return []

		codigos = [r[0] for r in rows]
		tipos_map = self._get_tipos_para_disenos(codigos)

		disenos: List[ProduccionDiseno] = []
		for row in rows:
			(codigo, coleccion_id, nombre, sufijo_id, activo) = row
			disenos.append(ProduccionDiseno(
				codigo=codigo,
				coleccion_id=coleccion_id or 0,
				nombre=nombre,
				sufijo_id=sufijo_id,
				tipos=tipos_map.get(codigo, []),
				activo=activo
			))
		return disenos

	def crear(self, diseno: ProduccionDiseno) -> bool:
		"""Crear un nuevo diseño."""
		try:
			# 1. Insertar diseño
			query = """
				INSERT INTO produccion_disenos
				(codigo, coleccion_id, nombre, sufijo_id, activo)
				VALUES (?, ?, ?, ?, ?)
			"""
			self.db.execute_query(query, (
				diseno.codigo, diseno.coleccion_id, diseno.nombre, diseno.sufijo_id, diseno.activo
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
		"""Actualizar un diseño existente."""
		try:
			# 1. Actualizar diseño
			query = """
				UPDATE produccion_disenos
				SET coleccion_id = ?, nombre = ?, sufijo_id = ?, activo = ?
				WHERE codigo = ?
			"""
			self.db.execute_query(query, (
				diseno.coleccion_id, diseno.nombre, diseno.sufijo_id, diseno.activo, diseno.codigo
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

	def existe_diseno(self, coleccion_id: int, nombre: str, sufijo_id: Optional[int] = None) -> bool:
		"""Comprobar si ya existe un diseño con esa colección, nombre y sufijo.

		Args:
			coleccion_id: ID de la colección del diseño.
			nombre: Nombre del diseño.
			sufijo_id: ID del sufijo (opcional).

		Returns:
			True si ya existe, False si no.
		"""
		try:
			if sufijo_id:
				rows = self.db.fetch_all(
					"SELECT 1 FROM produccion_disenos WHERE coleccion_id = ? AND LOWER(nombre) = LOWER(?) AND sufijo_id = ? AND activo = 1 LIMIT 1",
					(coleccion_id, nombre, sufijo_id)
				)
			else:
				rows = self.db.fetch_all(
					"SELECT 1 FROM produccion_disenos WHERE coleccion_id = ? AND LOWER(nombre) = LOWER(?) AND (sufijo_id IS NULL) AND activo = 1 LIMIT 1",
					(coleccion_id, nombre)
				)
			return len(rows) > 0
		except Exception:
			import logging
			logging.exception("Error comprobando existencia de diseño")
			return False

	def get_estadisticas_disenos(self, codigos: List[str]) -> dict:
		"""Obtener estadísticas (total producido y costes por método) para una lista de diseños."""
		if not codigos:
			return {}
			
		placeholders = ', '.join(['?'] * len(codigos))
		
		# 1. Obtener total producido
		q_producido = f"""
			SELECT diseno_codigo, SUM(cantidad) 
			FROM produccion_lineas 
			WHERE diseno_codigo IN ({placeholders})
			GROUP BY diseno_codigo
		"""
		rows_producido = self.db.fetch_all(q_producido, tuple(codigos))
		producido_map = {row[0]: row[1] or 0 for row in rows_producido}
		
		# 2. Obtener costes por método
		q_costes = f"""
			SELECT dm.diseno_codigo, m.nombre, dm.coste
			FROM produccion_disenos_metodos dm
			JOIN produccion_metodos m ON m.id = dm.metodo_id
			WHERE dm.diseno_codigo IN ({placeholders})
			ORDER BY dm.diseno_codigo, m.orden
		"""
		rows_costes = self.db.fetch_all(q_costes, tuple(codigos))
		
		costes_map = {c: [] for c in codigos}
		for dis_cod, met_nom, coste in rows_costes:
			if dis_cod in costes_map:
				costes_map[dis_cod].append((met_nom, coste))
				
		stats = {}
		for cod in codigos:
			stats[cod] = {
				"total_producido": producido_map.get(cod, 0),
				"costes_metodos": costes_map.get(cod, [])
			}
		return stats
