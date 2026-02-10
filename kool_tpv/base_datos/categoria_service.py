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
