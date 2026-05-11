from typing import Optional, Dict, Any, List

from kool_tpv.base_datos.db_wrapper import Database


class CategoriaRepository:
    """Repository de acceso a BD para la tabla `categorias`.

    Reglas:
     - Sin try/except (los errores escalan al caller)
     - Sin transformaciones de tipos
     - Sin normalización
     - Usa self.db.fetch_one / fetch_all / execute_query
    """

    def __init__(self, db: Database):
        self.db = db

    # ── LECTURA ──────────────────────────────────────────────────────────────

    def get_con_productos(self) -> List[str]:
        """Nombres de categorías que tienen al menos un producto asociado."""
        query = """
        SELECT DISTINCT c.nombre
        FROM categorias c
        INNER JOIN productos p ON c.id = p.categoria
        ORDER BY c.nombre
        """
        rows = self.db.fetch_all(query)
        return [str(r[0]) for r in rows] if rows else []

    def get_all(self) -> List[Dict[str, Any]]:
        """Todas las categorías ordenadas por nombre."""
        rows = self.db.fetch_all(
            'SELECT id, nombre, descripcion, shopify_taxonomy, fide_porcentaje '
            'FROM categorias ORDER BY nombre'
        )
        return [
            {
                'id': r[0],
                'nombre': r[1],
                'descripcion': r[2],
                'shopify_taxonomy': r[3],
                'fide_porcentaje': r[4],
            }
            for r in rows
        ] if rows else []

    def get_by_id(self, id: int) -> Optional[Dict[str, Any]]:
        """Categoría por id. Devuelve None si no existe."""
        row = self.db.fetch_one(
            'SELECT id, nombre, descripcion, shopify_taxonomy, fide_porcentaje '
            'FROM categorias WHERE id = ?',
            (id,),
        )
        if row is None:
            return None
        return {
            'id': row[0],
            'nombre': row[1],
            'descripcion': row[2],
            'shopify_taxonomy': row[3],
            'fide_porcentaje': row[4],
        }

    # ── ESCRITURA ─────────────────────────────────────────────────────────────

    def insert(
        self,
        nombre: str,
        descripcion: str,
        shopify_taxonomy: str,
        fide_porcentaje: float,
    ) -> int:
        """Inserta una nueva categoría. Devuelve el id generado."""
        cur = self.db.execute_query(
            'INSERT INTO categorias (nombre, descripcion, shopify_taxonomy, fide_porcentaje) '
            'VALUES (?, ?, ?, ?)',
            (nombre, descripcion, shopify_taxonomy, float(fide_porcentaje)),
        )
        return cur.lastrowid

    def update(
        self,
        id: int,
        nombre: str,
        descripcion: str,
        shopify_taxonomy: str,
        fide_porcentaje: float,
    ) -> None:
        """Actualiza una categoría existente."""
        self.db.execute_query(
            'UPDATE categorias SET nombre = ?, descripcion = ?, '
            'shopify_taxonomy = ?, fide_porcentaje = ? WHERE id = ?',
            (nombre, descripcion, shopify_taxonomy, float(fide_porcentaje), id),
        )

    def delete(self, id: int) -> None:
        """Elimina una categoría por id."""
        self.db.execute_query('DELETE FROM categorias WHERE id = ?', (id,))
