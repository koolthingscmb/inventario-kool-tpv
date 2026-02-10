from .db_wrapper import Database
import logging


class TipoService:
    def __init__(self, db):
        self.db = db
    
    def get_tipos_con_productos(self):
        """Solo tipos que tienen productos asociados"""
        try:
            query = """
            SELECT DISTINCT t.nombre 
            FROM tipos t 
            INNER JOIN productos p ON t.id = p.tipo
            ORDER BY t.nombre
            """
            rows = self.db.fetch_all(query)
            return [str(r[0]) for r in rows] if rows else []
        except Exception as e:
            logging.error(f"Error obteniendo tipos: {e}")
            return []
