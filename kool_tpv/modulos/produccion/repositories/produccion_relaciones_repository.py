"""Acceso a datos para las relaciones de producción (Matriz).

Maneja las asociaciones entre:
- Tipos <-> Colores
- Tipos <-> Tallas
"""
from typing import List, Set, Optional
from kool_tpv.base_datos.db_wrapper import Database

class ProduccionRelacionesRepository:
    def __init__(self, db: Database):
        self.db = db

    # --- Matriz 3D para TIPOS y VARIANTES (usa produccion_tipo_color_tallas) ---

    def get_colores_id_por_tipo_3d(self, tipo_id: int, variante_id: Optional[int] = None) -> Set[int]:
        """Obtener IDs de colores asignados a un tipo o variante (Libro de Recetas)."""
        if variante_id:
            query = "SELECT DISTINCT color_id FROM produccion_tipo_color_tallas WHERE tipo_id = ? AND variante_id = ?"
            rows = self.db.fetch_all(query, (tipo_id, variante_id))
        else:
            query = "SELECT DISTINCT color_id FROM produccion_tipo_color_tallas WHERE tipo_id = ? AND variante_id IS NULL"
            rows = self.db.fetch_all(query, (tipo_id,))
        return {row[0] for row in rows if row[0] is not None}

    def get_tallas_id_por_tipo_color_3d(self, tipo_id: int, color_id: int, variante_id: Optional[int] = None) -> Set[int]:
        """Obtener IDs de tallas disponibles para una combinación tipo+color (o variante+color)."""
        if variante_id:
            query = "SELECT talla_id FROM produccion_tipo_color_tallas WHERE tipo_id = ? AND variante_id = ? AND color_id = ? AND talla_id IS NOT NULL"
            rows = self.db.fetch_all(query, (tipo_id, variante_id, color_id))
        else:
            query = "SELECT talla_id FROM produccion_tipo_color_tallas WHERE tipo_id = ? AND variante_id IS NULL AND color_id = ? AND talla_id IS NOT NULL"
            rows = self.db.fetch_all(query, (tipo_id, color_id))
        return {row[0] for row in rows if row[0] is not None}

    def actualizar_tallas_tipo_color_3d(self, tipo_id: int, color_id: int, tallas_ids: List[int], variante_id: Optional[int] = None):
        """Sincronizar tallas para una combinación tipo+color o variante+color."""
        # Borrar registros de esta combinación
        if variante_id:
            self.db.execute_query(
                "DELETE FROM produccion_tipo_color_tallas WHERE tipo_id = ? AND variante_id = ? AND color_id = ?",
                (tipo_id, variante_id, color_id)
            )
        else:
            self.db.execute_query(
                "DELETE FROM produccion_tipo_color_tallas WHERE tipo_id = ? AND variante_id IS NULL AND color_id = ?",
                (tipo_id, color_id)
            )

        if not tallas_ids:
            # Si no hay tallas, insertar un registro con talla_id NULL para guardar el color
            self.db.execute_query(
                "INSERT INTO produccion_tipo_color_tallas (tipo_id, variante_id, color_id, talla_id) VALUES (?, ?, ?, NULL)",
                (tipo_id, variante_id, color_id)
            )
        else:
            for t_id in tallas_ids:
                self.db.execute_query(
                    "INSERT INTO produccion_tipo_color_tallas (tipo_id, variante_id, color_id, talla_id) VALUES (?, ?, ?, ?)",
                    (tipo_id, variante_id, color_id, t_id)
                )

    def asegurar_relacion(self, tipo_id: int, color_id: int, talla_id: int,
                          variante_id: Optional[int] = None) -> bool:
        """Asegurar que una combinación tipo+variante+color+talla existe en la matriz.
        
        Si no existe, la inserta. Si ya existe, no hace nada.
        Returns True si se insertó, False si ya existía.
        """
        if variante_id:
            check = "SELECT 1 FROM produccion_tipo_color_tallas WHERE tipo_id = ? AND variante_id = ? AND color_id = ? AND talla_id = ?"
            row = self.db.fetch_all(check, (tipo_id, variante_id, color_id, talla_id))
        else:
            check = "SELECT 1 FROM produccion_tipo_color_tallas WHERE tipo_id = ? AND variante_id IS NULL AND color_id = ? AND talla_id = ?"
            row = self.db.fetch_all(check, (tipo_id, color_id, talla_id))
        
        if row:
            return False
        
        self.db.execute_query(
            "INSERT INTO produccion_tipo_color_tallas (tipo_id, variante_id, color_id, talla_id) VALUES (?, ?, ?, ?)",
            (tipo_id, variante_id, color_id, talla_id)
        )
        return True

    def remove_color_de_tipo_3d(self, tipo_id: int, color_id: int, variante_id: Optional[int] = None):
        """Eliminar un color y todas sus tallas de un tipo o variante."""
        if variante_id:
            self.db.execute_query(
                "DELETE FROM produccion_tipo_color_tallas WHERE tipo_id = ? AND variante_id = ? AND color_id = ?",
                (tipo_id, variante_id, color_id)
            )
        else:
            self.db.execute_query(
                "DELETE FROM produccion_tipo_color_tallas WHERE tipo_id = ? AND variante_id IS NULL AND color_id = ?",
                (tipo_id, color_id)
            )
