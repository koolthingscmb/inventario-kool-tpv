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

    # --- Matriz 3D para TIPOS (usa produccion_stock_colores_tallas) ---

    def get_colores_id_por_tipo_3d(self, tipo_id: int) -> Set[int]:
        """Obtener IDs de colores asignados a un tipo (DISTINCT desde stock base)."""
        query = "SELECT DISTINCT color_id FROM produccion_stock_colores_tallas WHERE tipo_id = ? AND color_id IS NOT NULL"
        rows = self.db.fetch_all(query, (tipo_id,))
        return {row[0] for row in rows if row[0] is not None}

    def get_tallas_id_por_tipo_color_3d(self, tipo_id: int, color_id: int) -> Set[int]:
        """Obtener IDs de tallas disponibles para una combinación tipo+color."""
        query = "SELECT talla_id FROM produccion_stock_colores_tallas WHERE tipo_id = ? AND color_id = ? AND talla_id IS NOT NULL"
        rows = self.db.fetch_all(query, (tipo_id, color_id))
        return {row[0] for row in rows if row[0] is not None}

    def actualizar_tallas_tipo_color_3d(self, tipo_id: int, color_id: int, tallas_ids: List[int], all_tallas: dict):
        """Sincronizar tallas para una combinación tipo+color (borrar y re-insertar en stock base)."""
        # Borrar registros de esta combinación que tengan talla_id (los que no tienen talla_id pueden ser manuales)
        self.db.execute_query(
            "DELETE FROM produccion_stock_colores_tallas WHERE tipo_id = ? AND color_id = ? AND (talla_id IS NOT NULL OR talla IS NOT NULL)",
            (tipo_id, color_id)
        )
        for t_id in tallas_ids:
            talla_nombre = all_tallas[t_id].nombre if t_id in all_tallas else str(t_id)
            self.db.execute_query(
                """INSERT INTO produccion_stock_colores_tallas 
                   (tipo_id, color_id, talla_id, talla, cantidad) 
                   VALUES (?, ?, ?, ?, 0)""",
                (tipo_id, color_id, t_id, talla_nombre)
            )

    def remove_color_de_tipo_3d(self, tipo_id: int, color_id: int):
        """Eliminar un color y todas sus tallas de un tipo en el stock base."""
        self.db.execute_query(
            "DELETE FROM produccion_stock_colores_tallas WHERE tipo_id = ? AND color_id = ?",
            (tipo_id, color_id)
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
