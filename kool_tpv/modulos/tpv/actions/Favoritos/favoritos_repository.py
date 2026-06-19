import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

class FavoritosRepository:
    def __init__(self, db):
        self.db = db

    def get_all(self) -> List[dict]:
        """Obtiene todos los favoritos con datos del producto y color del tipo/categoría."""
        query = """
        SELECT 
            f.id, 
            f.producto_id, 
            f.nombre as nombre_favorito, 
            f.posicion,
            p.nombre as nombre_producto,
            p.sku,
            pr.pvp,
            p.tipo_iva,
            p.tipo as tipo_id,
            t.nombre as tipo_nombre,
            p.categoria as categoria_id,
            c.nombre as categoria_nombre,
            COALESCE(t.color, c.color, '#333333') as color,
            COALESCE(t.icono, c.icono) as icono
        FROM favoritos f
        JOIN productos p ON f.producto_id = p.id
        LEFT JOIN precios pr ON pr.producto_id = p.id AND pr.activo = 1
        LEFT JOIN tipos t ON p.tipo = t.id
        LEFT JOIN categorias c ON p.categoria = c.id
        ORDER BY f.posicion ASC
        """
        try:
            rows = self.db.fetch_all(query)
            return [dict(r) for r in rows] if rows else []
        except Exception:
            logger.exception("Error en FavoritosRepository.get_all")
            return []

    def add(self, producto_id: int, nombre: str, posicion: int) -> bool:
        """Añade un nuevo producto a favoritos."""
        query = "INSERT INTO favoritos (producto_id, nombre, posicion) VALUES (?, ?, ?)"
        try:
            return self.db.execute_query(query, (producto_id, nombre, posicion))
        except Exception:
            logger.exception("Error en FavoritosRepository.add")
            return False

    def remove(self, favorito_id: int) -> bool:
        """Elimina un producto de favoritos."""
        query = "DELETE FROM favoritos WHERE id = ?"
        try:
            return self.db.execute_query(query, (favorito_id,))
        except Exception:
            logger.exception("Error en FavoritosRepository.remove")
            return False

    def update_posicion(self, favorito_id: int, nueva_posicion: int) -> bool:
        """Actualiza la posición de un favorito."""
        query = "UPDATE favoritos SET posicion = ? WHERE id = ?"
        try:
            return self.db.execute_query(query, (nueva_posicion, favorito_id))
        except Exception:
            logger.exception("Error en FavoritosRepository.update_posicion")
            return False

    def update_nombre(self, favorito_id: int, nuevo_nombre: str) -> bool:
        """Actualiza el nombre personalizado de un favorito."""
        query = "UPDATE favoritos SET nombre = ? WHERE id = ?"
        try:
            return self.db.execute_query(query, (nuevo_nombre, favorito_id))
        except Exception:
            logger.exception("Error en FavoritosRepository.update_nombre")
            return False

    def update_posiciones_masivo(self, mapeo_posiciones: List[tuple]) -> bool:
        """Actualiza múltiples posiciones a la vez. 
        Recibe una lista de tuples (id, nueva_posicion).
        """
        try:
            with self.db.transaction() as cur:
                for fav_id, pos in mapeo_posiciones:
                    cur.execute("UPDATE favoritos SET posicion = ? WHERE id = ?", (pos, fav_id))
            return True
        except Exception:
            logger.exception("Error en FavoritosRepository.update_posiciones_masivo")
            return False

    def get_next_posicion(self) -> int:
        """Obtiene la siguiente posición disponible."""
        query = "SELECT MAX(posicion) FROM favoritos"
        try:
            res = self.db.fetch_one(query)
            return (res[0] + 1) if res and res[0] is not None else 0
        except Exception:
            return 0
