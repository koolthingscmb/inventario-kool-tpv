"""Acceso a datos para la tabla `produccion_menu`."""
from typing import List
from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.produccion.models.produccion_menu_model import ProduccionMenuItem

class ProduccionMenuRepository:
    def __init__(self, db: Database):
        self.db = db

    def get_activos(self) -> List[ProduccionMenuItem]:
        """Obtener los elementos del menú activos."""
        query = "SELECT id, nombre, sistema_produccion, orden, activo, tipo_id FROM produccion_menu WHERE activo = 1 ORDER BY orden"
        rows = self.db.fetch_all(query)
        return [
            ProduccionMenuItem(
                id=row[0],
                nombre=row[1],
                sistema_produccion=row[2],
                orden=row[3],
                activo=row[4],
                tipo_id=row[5]
            ) for row in rows
        ]
