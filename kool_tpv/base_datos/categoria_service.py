from .db_wrapper import Database
import logging


class CategoriaService:
    def __init__(self, db):
        self.db = db
    
    def get_categorias_con_productos(self):
        """Solo categorías que tienen productos asociados"""
        try:
            query = """
            SELECT DISTINCT c.nombre 
            FROM categorias c 
            INNER JOIN productos p ON c.id = p.categoria
            ORDER BY c.nombre
            """
            rows = self.db.fetch_all(query)
            return [str(r[0]) for r in rows] if rows else []
        except Exception as e:
            logging.error(f"Error obteniendo categorías: {e}")
            return []

    def get_all(self):
        """Retorna todas las categorías ordenadas por nombre."""
        try:
            rows = self.db.fetch_all('SELECT id, nombre, descripcion, shopify_taxonomy, fide_porcentaje FROM categorias ORDER BY nombre')
            return [dict(id=r[0], nombre=r[1], descripcion=r[2], shopify_taxonomy=r[3], fide_porcentaje=r[4]) for r in rows] if rows else []
        except Exception as e:
            logging.error(f"Error en get_all categorias: {e}")
            return []

    def save(self, nombre: str, descripcion: str = '', shopify_taxonomy: str = '', fide_porcentaje: float = 0.0) -> int:
        """Inserta una nueva categoría y retorna su id."""
        try:
            cur = self.db.execute_query('INSERT INTO categorias (nombre, descripcion, shopify_taxonomy, fide_porcentaje) VALUES (?, ?, ?, ?)', (nombre, descripcion, shopify_taxonomy, float(fide_porcentaje)))
            return cur.lastrowid
        except Exception as e:
            logging.error(f"Error guardando categoría: {e}")
            raise

    def update(self, id: int, nombre: str, descripcion: str = '', shopify_taxonomy: str = '', fide_porcentaje: float = 0.0) -> bool:
        """Actualiza una categoría existente."""
        try:
            self.db.execute_query('UPDATE categorias SET nombre = ?, descripcion = ?, shopify_taxonomy = ?, fide_porcentaje = ? WHERE id = ?', (nombre, descripcion, shopify_taxonomy, float(fide_porcentaje), id))
            return True
        except Exception as e:
            logging.error(f"Error actualizando categoría {id}: {e}")
            return False

    def delete(self, id: int) -> bool:
        """Elimina una categoría por id."""
        try:
            self.db.execute_query('DELETE FROM categorias WHERE id = ?', (id,))
            return True
        except Exception as e:
            logging.error(f"Error eliminando categoría {id}: {e}")
            return False
