"""Acceso a datos para la tabla `produccion_extras`.
"""
from typing import List, Optional
from kool_tpv.base_datos.db_wrapper import Database
from dataclasses import dataclass
import datetime

@dataclass
class ProduccionExtra:
    id: Optional[int] = None
    nombre: str = ""
    descripcion: Optional[str] = None
    coste: int = 0  # en céntimos
    activo: int = 1
    fecha_creacion: Optional[str] = None
    fecha_modificacion: Optional[str] = None

class ProduccionExtrasRepository:
    def __init__(self, db: Database):
        self.db = db

    def get_todos(self, solo_activos: bool = False) -> List[ProduccionExtra]:
        query = "SELECT id, nombre, descripcion, coste, activo, fecha_creacion, fecha_modificacion FROM produccion_extras"
        if solo_activos:
            query += " WHERE activo = 1"
        query += " ORDER BY nombre"
        
        rows = self.db.fetch_all(query)
        return [self._row_to_extra(row) for row in rows]

    def get_por_id(self, extra_id: int) -> Optional[ProduccionExtra]:
        query = "SELECT id, nombre, descripcion, coste, activo, fecha_creacion, fecha_modificacion FROM produccion_extras WHERE id = ?"
        rows = self.db.fetch_all(query, (extra_id,))
        if not rows:
            return None
        return self._row_to_extra(rows[0])

    def crear(self, extra: ProduccionExtra) -> Optional[int]:
        query = """
            INSERT INTO produccion_extras (nombre, descripcion, coste, activo)
            VALUES (?, ?, ?, ?)
        """
        try:
            self.db.execute_query(query, (extra.nombre, extra.descripcion, extra.coste, extra.activo))
            res = self.db.fetch_all("SELECT last_insert_rowid()")
            return res[0][0] if res else None
        except Exception:
            import logging
            logging.exception("Error creando extra de producción")
            return None

    def actualizar(self, extra: ProduccionExtra) -> bool:
        if not extra.id:
            return False
        query = """
            UPDATE produccion_extras 
            SET nombre = ?, descripcion = ?, coste = ?, activo = ?, fecha_modificacion = (datetime('now', 'localtime'))
            WHERE id = ?
        """
        try:
            self.db.execute_query(query, (extra.nombre, extra.descripcion, extra.coste, extra.activo, extra.id))
            return True
        except Exception:
            import logging
            logging.exception(f"Error actualizando extra {extra.id}")
            return False

    def eliminar(self, extra_id: int) -> bool:
        query = "DELETE FROM produccion_extras WHERE id = ?"
        try:
            self.db.execute_query(query, (extra_id,))
            return True
        except Exception:
            import logging
            logging.exception(f"Error eliminando extra {extra_id}")
            return False

    def _row_to_extra(self, row) -> ProduccionExtra:
        return ProduccionExtra(
            id=row[0],
            nombre=row[1],
            descripcion=row[2],
            coste=row[3],
            activo=row[4],
            fecha_creacion=row[5],
            fecha_modificacion=row[6]
        )
