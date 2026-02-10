"""Servicio de negocio para clientes.

Expone una capa de servicio que utiliza `ClientesDB` para consultar
clientes y aplicar pequeñas transformaciones (ej. formateo de nivel).
"""
from typing import List, Dict, Any

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
		mapping = {
			1: "BRONCE",
			2: "PLATA",
			3: "ORO",
			4: "PLATINO",
		}
		try:
			key = int(id_nivel) if id_nivel is not None else 0
		except Exception:
			key = 0

		return mapping.get(key, "SIN NIVEL")

