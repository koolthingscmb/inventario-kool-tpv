"""Servicio de negocio para clientes.

Expone una capa de servicio que utiliza `ClientesDB` para consultar
clientes y aplicar pequeñas transformaciones (ej. formateo de nivel).
"""
from typing import List, Dict, Any
import logging

from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.clientes.clientes_db import ClientesDB
from kool_tpv.base_datos.money_adapter import read_from_db
from kool_tpv.modulos.fidelizacion.niveles_repository import NivelesRepository


class ClienteService:
	"""Servicio que encapsula operaciones de negocio relacionadas con clientes.

	Args:
		db: instancia de `Database` ya conectada.
	"""

	def __init__(self, db: Database):
		self.db = db
		self._clientes_db = ClientesDB(db)
		self._niveles_repo = NivelesRepository(db)

	def buscar_clientes(self, termino: str) -> List[Dict[str, Any]]:
		"""Buscar clientes por término en nombre, dni o teléfono.

		Args:
			termino: término de búsqueda (coincidencia parcial).

		Returns:
			Lista de clientes (cada uno como diccionario con claves
			`id`, `nombre`, `telefono`, `tesoro_total`, `id_nivel`).
		"""
		termino = termino or ""
		return self._clientes_db.get_clientes(termino)

	def formatear_nivel(self, id_nivel: int) -> str:
		"""Mapear `id_nivel` a su etiqueta legible.

		El mapeo es intencionalmente simple y sirve como ejemplo. Se
		puede externalizar a configuración o a una tabla en la base de
		datos en un siguiente paso.
		"""
		# Resolve the level label from the `niveles_fidelidad` table using the
		# provided `id_nivel`. This avoids hard-coded mappings and keeps the UI
		# consistent with the DB configuration.
		try:
			if id_nivel is None:
				return "SIN NIVEL"
			row = None
			try:
				row = self.db.fetch_one(
					"SELECT nombre_nivel FROM niveles_fidelidad WHERE id = ?",
					(id_nivel,)
				)
			except Exception:
				row = None
			if row and len(row) > 0 and row[0]:
				return str(row[0])
			return "SIN NIVEL"
		except Exception:
			# Defensive fallback
			return "SIN NIVEL"

	def get_cliente(self, cliente_id: int) -> Dict[str, Any]:
		"""Obtener cliente completo por ID con datos de nivel.

		Args:
			cliente_id: ID del cliente

		Returns:
			Dict con todos los campos del cliente + datos del nivel, o None si no existe
		"""
		try:
			# Select explicit columns to avoid dependence on physical column order
			query = """
			SELECT
			    c.id AS id,
			    c.nombre AS nombre,
			    c.telefono AS telefono,
			    c.email AS email,
			    c.dni AS dni,
			    c.direccion AS direccion,
			    c.ciudad AS ciudad,
			    c.cp AS cp,
			    c.pais AS pais,
			    c.fecha_nacimiento AS fecha_nacimiento,
			    c.tags AS tags,
			    c.notes_internas AS notes_internas,
			    c.tesoro_total AS tesoro_total,
			    c.tesoro_gastado_total AS tesoro_gastado_total,
			    c.tesoro_historico AS tesoro_historico,
			    c.id_nivel AS id_nivel,
			    c.fidelidad_activa AS fidelidad_activa,
			    c.fecha_alta AS fecha_alta,
			    c.fecha_vencimiento_tesoro AS fecha_vencimiento_tesoro,
			    c.fecha_ultima_compra AS fecha_ultima_compra,
			    c.total_compras AS total_compras,
			    c.fecha_ultima_comunicacion AS fecha_ultima_comunicacion,
			    n.level AS nivel_level,
			    n.nombre_nivel AS nivel_nombre,
			    n.grafismo_nivel AS nivel_grafismo,
			    n.tesoro_minimo AS nivel_tesoro_minimo
			FROM clientes c
			LEFT JOIN niveles_fidelidad n ON c.id_nivel = n.id
			WHERE c.id = ?
			"""

			row = self.db.fetch_one(query, (cliente_id,))

			if not row:
				return None

			# row is a sqlite3.Row (db_wrapper sets row_factory), access by name
			return {
				'id': row['id'],
				'nombre': row['nombre'] or '',
				'telefono': row['telefono'] or '',
				'email': row['email'] or '',
				'dni': row['dni'] or '',
				'direccion': row['direccion'] or '',
				'ciudad': row['ciudad'] or '',
				'cp': row['cp'] or '',
				'pais': row['pais'] or '',
				'fecha_nacimiento': row['fecha_nacimiento'] or None,
				'tags': row['tags'] or '',
				'notes_internas': row['notes_internas'] or '',
				'tesoro_total': read_from_db(int(row['tesoro_total'] or 0)),
				'tesoro_gastado_total': read_from_db(int(row['tesoro_gastado_total'] or 0)),
				'tesoro_historico': read_from_db(int(row['tesoro_historico'] or 0)),
				'id_nivel': row['id_nivel'],
				'fidelidad_activa': int(row['fidelidad_activa'] or 1),
				'fecha_alta': row['fecha_alta'],
				'fecha_vencimiento_tesoro': row['fecha_vencimiento_tesoro'] or None,
				'fecha_ultima_compra': row['fecha_ultima_compra'] or None,
				'total_compras': int(row['total_compras'] or 0),
				'fecha_ultima_comunicacion': row['fecha_ultima_comunicacion'] or None,
				# Datos del nivel (desde JOIN)
				'nivel_level': row['nivel_level'] if 'nivel_level' in row.keys() else None,
				'nivel_nombre': row['nivel_nombre'] if 'nivel_nombre' in row.keys() and row['nivel_nombre'] else 'Forastero',
				'nivel_grafismo': row['nivel_grafismo'] if 'nivel_grafismo' in row.keys() and row['nivel_grafismo'] else '~',
				'nivel_tesoro_minimo': float(row['nivel_tesoro_minimo']) if 'nivel_tesoro_minimo' in row.keys() and row['nivel_tesoro_minimo'] else 0.0
			}
		except Exception:
			logging.exception(f'Error obteniendo cliente {cliente_id}')
			return None

	def save_cliente(self, nombre: str, telefono: str = '', email: str = '', 
				dni: str = '', direccion: str = '', ciudad: str = '', 
				cp: str = '', pais: str = '', fecha_nacimiento: str = None,
				tags: str = '', fidelidad_activa: int = 1) -> bool:
		"""Crear nuevo cliente.

		Args:
			nombre: Nombre completo (obligatorio)
			telefono, email, dni, direccion, ciudad, cp, pais: Datos contacto
			fecha_nacimiento: Formato 'YYYY-MM-DD' o None
			tags: Tags separados por comas
			fidelidad_activa: 1=activado, 0=desactivado

		Returns:
			bool: True si OK, False si error
		"""
		try:
			nivel_base_id = self._niveles_repo.obtener_nivel_base()
			query = """
				INSERT INTO clientes 
				(nombre, telefono, email, dni, direccion, ciudad, cp, pais, 
				 fecha_nacimiento, tags, fidelidad_activa, id_nivel)
				VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
			"""
			self.db.execute_query(query, (
				nombre, telefono, email, dni, direccion, ciudad, cp, pais,
				fecha_nacimiento, tags, fidelidad_activa, nivel_base_id
			))
			logging.info(f'Cliente {nombre} creado correctamente')
			return True
		except Exception:
			logging.exception('Error guardando cliente')
			return False

	def update_cliente(self, cliente_id: int, nombre: str, telefono: str = '', 
				   email: str = '', dni: str = '', direccion: str = '', 
				   ciudad: str = '', cp: str = '', pais: str = '', 
				   fecha_nacimiento: str = None, tags: str = '', 
				   fidelidad_activa: int = 1) -> bool:
		"""Actualizar cliente existente.

		Args:
			cliente_id: ID del cliente a actualizar
			nombre, telefono, email, etc: Datos actualizados

		Returns:
			bool: True si OK, False si error
		"""
		try:
			query = """
				UPDATE clientes SET 
				nombre=?, telefono=?, email=?, dni=?, direccion=?, ciudad=?, 
				cp=?, pais=?, fecha_nacimiento=?, tags=?, fidelidad_activa=?
				WHERE id=?
			"""
			self.db.execute_query(query, (
				nombre, telefono, email, dni, direccion, ciudad, cp, pais,
				fecha_nacimiento, tags, fidelidad_activa, cliente_id
			))
			logging.info(f'Cliente {cliente_id} actualizado correctamente')
			return True
		except Exception:
			logging.exception(f'Error actualizando cliente {cliente_id}')
			return False

