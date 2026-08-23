"""Acceso a datos para grupos de tallas de producción."""
from typing import List, Optional
import logging

from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.produccion.models.produccion_talla_grupo_model import ProduccionTallaGrupo


class ProduccionTallasGruposRepository:
    """DAO para `produccion_tallas_grupos` y su relación con tallas."""

    def __init__(self, db: Database):
        self.db = db

    def get_todos(self) -> List[ProduccionTallaGrupo]:
        """Obtener todos los grupos de tallas."""
        query = "SELECT id, nombre FROM produccion_tallas_grupos ORDER BY nombre"
        rows = self.db.fetch_all(query)
        grupos = []
        for r in rows:
            grupo = ProduccionTallaGrupo(id=r[0], nombre=r[1])
            grupo.talla_ids = self.get_talla_ids_por_grupo(grupo.id)
            grupos.append(grupo)
        return grupos

    def get_por_id(self, grupo_id: int) -> Optional[ProduccionTallaGrupo]:
        """Obtener un grupo por su ID."""
        row = self.db.fetch_one("SELECT id, nombre FROM produccion_tallas_grupos WHERE id = ?", (grupo_id,))
        if row:
            grupo = ProduccionTallaGrupo(id=row[0], nombre=row[1])
            grupo.talla_ids = self.get_talla_ids_por_grupo(grupo.id)
            return grupo
        return None

    def get_talla_ids_por_grupo(self, grupo_id: int) -> List[int]:
        """Obtener los IDs de las tallas asociadas a un grupo."""
        query = "SELECT talla_id FROM produccion_tallas_grupo_items WHERE grupo_id = ?"
        rows = self.db.fetch_all(query, (grupo_id,))
        return [r[0] for r in rows]

    def crear(self, nombre: str) -> Optional[int]:
        """Crear un nuevo grupo de tallas."""
        try:
            query = "INSERT INTO produccion_tallas_grupos (nombre) VALUES (?)"
            self.db.execute_query(query, (nombre,))
            res = self.db.fetch_one("SELECT last_insert_rowid()")
            return res[0] if res else None
        except Exception as e:
            logging.error(f"Error al crear grupo de tallas: {e}")
            return None

    def eliminar(self, grupo_id: int) -> bool:
        """Eliminar un grupo de tallas (la tabla intermedia se limpia por ON DELETE CASCADE)."""
        try:
            self.db.execute_query("DELETE FROM produccion_tallas_grupos WHERE id = ?", (grupo_id,))
            return True
        except Exception as e:
            logging.error(f"Error al eliminar grupo de tallas: {e}")
            return False

    def guardar_asociaciones(self, grupo_id: int, talla_ids: List[int]) -> bool:
        """Actualizar las tallas asociadas a un grupo (borrar e insertar en transacción)."""
        try:
            with self.db.transaction() as cur:
                # 1. Limpiar asociaciones actuales
                cur.execute("DELETE FROM produccion_tallas_grupo_items WHERE grupo_id = ?", (grupo_id,))
                
                # 2. Insertar nuevas asociaciones
                for talla_id in talla_ids:
                    cur.execute(
                        "INSERT INTO produccion_tallas_grupo_items (grupo_id, talla_id) VALUES (?, ?)",
                        (grupo_id, talla_id)
                    )
            return True
        except Exception as e:
            logging.error(f"Error al guardar asociaciones de grupo de tallas: {e}")
            return False

    def get_tallas_por_variante(self, variante_id: int) -> List[int]:
        """Obtener los IDs de tallas permitidas para una variante específica a través de su grupo."""
        query = """
            SELECT i.talla_id 
            FROM produccion_tallas_grupo_items i
            JOIN tipos_variantes v ON v.grupo_talla_id = i.grupo_id
            WHERE v.id = ?
        """
        rows = self.db.fetch_all(query, (variante_id,))
        return [r[0] for r in rows]
