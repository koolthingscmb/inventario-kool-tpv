"""Servicio de negocio para clientes.

Expone una capa de servicio que utiliza `ClientesDB` para consultar
clientes y aplicar pequeñas transformaciones (ej. formateo de nivel).
"""
from typing import List, Dict, Any
import logging

from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.clientes.clientes_db import ClientesDB


class ClienteService:
	"""Servicio que encapsula operaciones de negocio relacionadas con clientes.

	Args:
		db: instancia de `Database` ya conectada.
	"""

	def __init__(self, db: Database):
		self.db = db
		self._clientes_db = ClientesDB(db)

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
			query = """
				SELECT c.*, 
				       n.level, n.nombre_nivel, n.grafismo_nivel, n.gasto_minimo
				FROM clientes c
				LEFT JOIN niveles_fidelidad n ON c.id_nivel = n.id
				WHERE c.id = ?
			"""
			row = self.db.fetch_one(query, (cliente_id,))

			if not row:
				return None

			return {
				'id': row[0],
				'nombre': row[1] or '',
				'telefono': row[2] or '',
				'email': row[3] or '',
				'dni': row[4] or '',
				'direccion': row[5] or '',
				'ciudad': row[6] or '',
				'cp': row[7] or '',
				'pais': row[8] or '',
				'fecha_nacimiento': row[9] or None,
				'tags': row[10] or '',
				'notes_internas': row[11] or '',
				'tesoro_total': float(row[12] or 0.0),
				'tesoro_gastado_total': float(row[13] or 0.0),
				'tesoro_historico': float(row[14] or 0.0),
				'id_nivel': row[15],
				'fidelidad_activa': int(row[16] or 1),
				'fecha_alta': row[17],
				'fecha_vencimiento_tesoro': row[18] or None,
				'fecha_ultima_compra': row[19] or None,
				'total_compras': int(row[20] or 0),
				'fecha_ultima_comunicacion': row[21] or None,
				# Datos del nivel (desde JOIN)
				'nivel_level': row[22] if len(row) > 22 else None,
				'nivel_nombre': row[23] if len(row) > 23 else 'Forastero',
				'nivel_grafismo': row[24] if len(row) > 24 else '~',
				'nivel_gasto_minimo': float(row[25]) if len(row) > 25 and row[25] else 0.0
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
			query = """
				INSERT INTO clientes 
				(nombre, telefono, email, dni, direccion, ciudad, cp, pais, 
				 fecha_nacimiento, tags, fidelidad_activa, id_nivel)
				VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
			"""
			# Nivel 1 por defecto (Forastero)
			self.db.execute_query(query, (
				nombre, telefono, email, dni, direccion, ciudad, cp, pais,
				fecha_nacimiento, tags, fidelidad_activa
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

