"""Acceso a datos para la tabla `produccion_menu`."""
from typing import List, Optional
from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.produccion.models.produccion_menu_model import ProduccionMenuItem

class ProduccionMenuRepository:
    def __init__(self, db: Database):
        self.db = db

    def get_todos(self) -> List[ProduccionMenuItem]:
        """Obtener todos los elementos del menú (incluyendo inactivos)."""
        query = "SELECT id, nombre, sistema_produccion, orden, activo, tipo_id FROM produccion_menu ORDER BY orden"
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

    def get_por_id(self, menu_id: int) -> Optional[ProduccionMenuItem]:
        """Obtener un elemento del menú por su ID."""
        query = "SELECT id, nombre, sistema_produccion, orden, activo, tipo_id FROM produccion_menu WHERE id = ?"
        rows = self.db.fetch_all(query, (menu_id,))
        if not rows:
            return None
        row = rows[0]
        return ProduccionMenuItem(
            id=row[0], nombre=row[1], sistema_produccion=row[2],
            orden=row[3], activo=row[4], tipo_id=row[5]
        )

    def crear(self, item: ProduccionMenuItem) -> Optional[int]:
        """Crear un nuevo elemento del menú."""
        query = "INSERT INTO produccion_menu (nombre, sistema_produccion, orden, activo, tipo_id) VALUES (?, ?, ?, ?, ?)"
        self.db.execute_query(query, (item.nombre, item.sistema_produccion, item.orden, item.activo, item.tipo_id))
        res = self.db.fetch_all("SELECT last_insert_rowid()")
        return res[0][0] if res else None

    def actualizar(self, item: ProduccionMenuItem) -> bool:
        """Actualizar un elemento del menú existente."""
        if not item.id:
            return False
        query = "UPDATE produccion_menu SET nombre = ?, sistema_produccion = ?, orden = ?, activo = ?, tipo_id = ? WHERE id = ?"
        self.db.execute_query(query, (item.nombre, item.sistema_produccion, item.orden, item.activo, item.tipo_id, item.id))
        return True

    def eliminar(self, menu_id: int) -> bool:
        """Borrar un elemento del menú."""
        self.db.execute_query("DELETE FROM produccion_menu WHERE id = ?", (menu_id,))
        return True
