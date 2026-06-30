"""Acceso a datos para la tabla `produccion_menu_tipos` (relación N:M)."""
from typing import List, Set
from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.produccion.models.produccion_tipos_model import ProduccionTipo


class ProduccionMenuTiposRepository:
    """DAO para la relación N:M entre produccion_menu y tipos."""

    def __init__(self, db: Database):
        self.db = db

    def get_tipos_por_menu(self, menu_id: int) -> List[ProduccionTipo]:
        """Obtener los tipos asignados a un menú."""
        query = """
            SELECT t.id, t.nombre, t.descripcion, t.color, t.icono,
                   t.coste_base, t.requiere_talla, t.requiere_color,
                   t.activo, t.orden
            FROM tipos t
            JOIN produccion_menu_tipos pmt ON t.id = pmt.tipo_id
            WHERE pmt.menu_id = ? AND t.activo = 1
              AND t.id IN (SELECT DISTINCT tipo_id FROM produccion_stock_colores_tallas WHERE cantidad > 0)
            ORDER BY t.orden
        """
        rows = self.db.fetch_all(query, (menu_id,))
        return [
            ProduccionTipo(
                id=r[0], nombre=r[1], descripcion=r[2], color=r[3], icono=r[4],
                coste_base=r[5] or 0.0, requiere_talla=r[6] or 0,
                requiere_color=r[7] or 0,
                activo=r[8] if r[8] is not None else 1, orden=r[9] or 0
            )
            for r in rows
        ]

    def get_tipos_id_por_menu(self, menu_id: int) -> Set[int]:
        """Obtener solo los IDs de tipos asignados a un menú."""
        query = "SELECT tipo_id FROM produccion_menu_tipos WHERE menu_id = ?"
        rows = self.db.fetch_all(query, (menu_id,))
        return {r[0] for r in rows}

    def actualizar_tipos_menu(self, menu_id: int, tipos_ids: List[int]):
        """Sincronizar tipos asignados a un menú (delete all + insert)."""
        self.db.execute_query(
            "DELETE FROM produccion_menu_tipos WHERE menu_id = ?", (menu_id,))
        for tid in tipos_ids:
            self.db.execute_query(
                "INSERT INTO produccion_menu_tipos (menu_id, tipo_id) VALUES (?, ?)",
                (menu_id, tid)
            )

    def get_tipos_todos_menus_ordenados(self) -> List[ProduccionTipo]:
        """Obtener todos los tipos asociados a cualquier menú, ordenados por menú y luego por tipo."""
        query = """
            SELECT DISTINCT t.id, t.nombre, t.descripcion, t.color, t.icono,
                   t.coste_base, t.requiere_talla, t.requiere_color,
                   t.activo, t.orden
            FROM tipos t
            JOIN produccion_menu_tipos pmt ON t.id = pmt.tipo_id
            JOIN produccion_menu m ON pmt.menu_id = m.id
            WHERE t.activo = 1 AND m.activo = 1
              AND t.id IN (SELECT DISTINCT tipo_id FROM produccion_stock_colores_tallas WHERE cantidad > 0)
            ORDER BY m.orden, t.orden
        """
        rows = self.db.fetch_all(query)
        return [
            ProduccionTipo(
                id=r[0], nombre=r[1], descripcion=r[2], color=r[3], icono=r[4],
                coste_base=r[5] or 0.0, requiere_talla=r[6] or 0,
                requiere_color=r[7] or 0,
                activo=r[8] if r[8] is not None else 1, orden=r[9] or 0
            )
            for r in rows
        ]

    def eliminar_tipos_menu(self, menu_id: int):
        """Eliminar todas las asignaciones de tipos de un menú."""
        self.db.execute_query(
            "DELETE FROM produccion_menu_tipos WHERE menu_id = ?", (menu_id,))
