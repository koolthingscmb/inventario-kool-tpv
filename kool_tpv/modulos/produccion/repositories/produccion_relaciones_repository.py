"""Acceso a datos para las relaciones de producción (Matriz).

Maneja las asociaciones entre:
- Tipos <-> Colores
- Tipos <-> Géneros
- Géneros <-> Tallas
- Géneros <-> Colores
"""
from typing import List, Set
from kool_tpv.base_datos.db_wrapper import Database

class ProduccionRelacionesRepository:
    def __init__(self, db: Database):
        self.db = db

    # --- Relaciones Género <-> Talla ---
    def get_tallas_id_por_genero(self, genero_id: int) -> Set[int]:
        """Obtener IDs de tallas asociadas a un género."""
        query = "SELECT talla_id FROM produccion_genero_tallas WHERE genero_id = ?"
        rows = self.db.fetch_all(query, (genero_id,))
        return {row[0] for row in rows}

    def actualizar_tallas_genero(self, genero_id: int, tallas_ids: List[int]):
        """Sincronizar tallas asociadas a un género (borrar y re-insertar)."""
        self.db.execute_query("DELETE FROM produccion_genero_tallas WHERE genero_id = ?", (genero_id,))
        for t_id in tallas_ids:
            self.db.execute_query(
                "INSERT INTO produccion_genero_tallas (genero_id, talla_id) VALUES (?, ?)",
                (genero_id, t_id)
            )

    # --- Relaciones Género <-> Color ---
    def get_colores_id_por_genero(self, genero_id: int) -> Set[int]:
        """Obtener IDs de colores asociados a un género."""
        query = "SELECT color_id FROM produccion_genero_colores WHERE genero_id = ?"
        rows = self.db.fetch_all(query, (genero_id,))
        return {row[0] for row in rows}

    def actualizar_colores_genero(self, genero_id: int, colores_ids: List[int]):
        """Sincronizar colores asociados a un género (borrar y re-insertar)."""
        self.db.execute_query("DELETE FROM produccion_genero_colores WHERE genero_id = ?", (genero_id,))
        for c_id in colores_ids:
            self.db.execute_query(
                "INSERT INTO produccion_genero_colores (genero_id, color_id) VALUES (?, ?)",
                (genero_id, c_id)
            )

    # --- Matriz 3D: Género <-> Color <-> Talla ---

    def get_colores_id_por_genero_3d(self, genero_id: int) -> Set[int]:
        """Obtener IDs de colores asignados a un género (DISTINCT desde la tabla 3D)."""
        query = "SELECT DISTINCT color_id FROM produccion_genero_color_tallas WHERE genero_id = ?"
        rows = self.db.fetch_all(query, (genero_id,))
        return {row[0] for row in rows}

    def get_tallas_id_por_genero_color_3d(self, genero_id: int, color_id: int) -> Set[int]:
        """Obtener IDs de tallas disponibles para una combinación género+color."""
        query = "SELECT talla_id FROM produccion_genero_color_tallas WHERE genero_id = ? AND color_id = ?"
        rows = self.db.fetch_all(query, (genero_id, color_id))
        return {row[0] for row in rows}

    def actualizar_tallas_genero_color_3d(self, genero_id: int, color_id: int, tallas_ids: List[int]):
        """Sincronizar tallas para una combinación género+color (borrar y re-insertar)."""
        self.db.execute_query(
            "DELETE FROM produccion_genero_color_tallas WHERE genero_id = ? AND color_id = ?",
            (genero_id, color_id)
        )
        for t_id in tallas_ids:
            self.db.execute_query(
                "INSERT INTO produccion_genero_color_tallas (genero_id, color_id, talla_id) VALUES (?, ?, ?)",
                (genero_id, color_id, t_id)
            )

    def remove_color_de_genero_3d(self, genero_id: int, color_id: int):
        """Eliminar un color y todas sus tallas de un género."""
        self.db.execute_query(
            "DELETE FROM produccion_genero_color_tallas WHERE genero_id = ? AND color_id = ?",
            (genero_id, color_id)
        )

    # --- Relaciones Tipo <-> Género ---
    def get_generos_id_por_tipo(self, tipo_id: int) -> Set[int]:
        """Obtener IDs de géneros asociados a un tipo de producto."""
        query = "SELECT genero_id FROM produccion_tipos_generos WHERE tipo_id = ?"
        rows = self.db.fetch_all(query, (tipo_id,))
        return {row[0] for row in rows}

    def actualizar_generos_tipo(self, tipo_id: int, generos_ids: List[int]):
        """Sincronizar géneros asociados a un tipo (borrar y re-insertar)."""
        self.db.execute_query("DELETE FROM produccion_tipos_generos WHERE tipo_id = ?", (tipo_id,))
        for g_id in generos_ids:
            self.db.execute_query(
                "INSERT INTO produccion_tipos_generos (tipo_id, genero_id) VALUES (?, ?)",
                (tipo_id, g_id)
            )
