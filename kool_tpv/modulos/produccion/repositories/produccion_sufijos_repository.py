"""Acceso a datos para sufijos de producción."""
from typing import List, Optional
from dataclasses import dataclass

from kool_tpv.base_datos.db_wrapper import Database


@dataclass
class ProduccionSufijo:
    id: int
    nombre: str
    activo: int = 1


class ProduccionSufijosRepository:
    """DAO para `produccion_sufijos`."""

    def __init__(self, db: Database):
        self.db = db

    def get_todos(self) -> List[ProduccionSufijo]:
        query = "SELECT id, nombre, activo FROM produccion_sufijos ORDER BY nombre"
        rows = self.db.fetch_all(query)
        return [ProduccionSufijo(id=r[0], nombre=r[1], activo=r[2]) for r in rows]

    def get_activos(self) -> List[ProduccionSufijo]:
        query = "SELECT id, nombre, activo FROM produccion_sufijos WHERE activo = 1 ORDER BY nombre"
        rows = self.db.fetch_all(query)
        return [ProduccionSufijo(id=r[0], nombre=r[1], activo=r[2]) for r in rows]

    def get_por_id(self, id: int) -> Optional[ProduccionSufijo]:
        query = "SELECT id, nombre, activo FROM produccion_sufijos WHERE id = ?"
        rows = self.db.fetch_all(query, (id,))
        if not rows:
            return None
        return ProduccionSufijo(id=rows[0][0], nombre=rows[0][1], activo=rows[0][2])

    def get_por_nombre(self, nombre: str) -> Optional[ProduccionSufijo]:
        query = "SELECT id, nombre, activo FROM produccion_sufijos WHERE LOWER(nombre) = LOWER(?)"
        rows = self.db.fetch_all(query, (nombre,))
        if not rows:
            return None
        return ProduccionSufijo(id=rows[0][0], nombre=rows[0][1], activo=rows[0][2])

    def crear(self, nombre: str) -> Optional[int]:
        try:
            self.db.execute_query(
                "INSERT INTO produccion_sufijos (nombre, activo) VALUES (?, 1)",
                (nombre.strip(),)
            )
            rows = self.db.fetch_all("SELECT last_insert_rowid()")
            return rows[0][0] if rows else None
        except Exception:
            return None

    def actualizar(self, id: int, nombre: str, activo: int) -> bool:
        try:
            self.db.execute_query(
                "UPDATE produccion_sufijos SET nombre = ?, activo = ? WHERE id = ?",
                (nombre.strip(), activo, id)
            )
            return True
        except Exception:
            return False

    def eliminar(self, id: int) -> bool:
        try:
            self.db.execute_query("UPDATE produccion_sufijos SET activo = 0 WHERE id = ?", (id,))
            return True
        except Exception:
            return False
