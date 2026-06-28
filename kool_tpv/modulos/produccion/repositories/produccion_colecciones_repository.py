"""Acceso a datos para colecciones de producción."""
from typing import List, Optional
from dataclasses import dataclass

from kool_tpv.base_datos.db_wrapper import Database


@dataclass
class ProduccionColeccion:
    id: int
    nombre: str
    activo: int = 1


class ProduccionColeccionesRepository:
    """DAO para `produccion_colecciones`."""

    def __init__(self, db: Database):
        self.db = db

    def get_todas(self) -> List[ProduccionColeccion]:
        query = "SELECT id, nombre, activo FROM produccion_colecciones ORDER BY nombre"
        rows = self.db.fetch_all(query)
        return [ProduccionColeccion(id=r[0], nombre=r[1], activo=r[2]) for r in rows]

    def get_activas(self) -> List[ProduccionColeccion]:
        query = "SELECT id, nombre, activo FROM produccion_colecciones WHERE activo = 1 ORDER BY nombre"
        rows = self.db.fetch_all(query)
        return [ProduccionColeccion(id=r[0], nombre=r[1], activo=r[2]) for r in rows]

    def get_por_id(self, id: int) -> Optional[ProduccionColeccion]:
        query = "SELECT id, nombre, activo FROM produccion_colecciones WHERE id = ?"
        rows = self.db.fetch_all(query, (id,))
        if not rows:
            return None
        return ProduccionColeccion(id=rows[0][0], nombre=rows[0][1], activo=rows[0][2])

    def get_por_nombre(self, nombre: str) -> Optional[ProduccionColeccion]:
        query = "SELECT id, nombre, activo FROM produccion_colecciones WHERE LOWER(nombre) = LOWER(?)"
        rows = self.db.fetch_all(query, (nombre,))
        if not rows:
            return None
        return ProduccionColeccion(id=rows[0][0], nombre=rows[0][1], activo=rows[0][2])

    def crear(self, nombre: str) -> Optional[int]:
        try:
            self.db.execute_query(
                "INSERT INTO produccion_colecciones (nombre, activo) VALUES (?, 1)",
                (nombre.strip(),)
            )
            rows = self.db.fetch_all("SELECT last_insert_rowid()")
            return rows[0][0] if rows else None
        except Exception:
            return None

    def actualizar(self, id: int, nombre: str, activo: int) -> bool:
        try:
            self.db.execute_query(
                "UPDATE produccion_colecciones SET nombre = ?, activo = ? WHERE id = ?",
                (nombre.strip(), activo, id)
            )
            return True
        except Exception:
            return False

    def eliminar(self, id: int) -> bool:
        try:
            self.db.execute_query("UPDATE produccion_colecciones SET activo = 0 WHERE id = ?", (id,))
            return True
        except Exception:
            return False
