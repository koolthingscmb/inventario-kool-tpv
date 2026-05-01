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

    def get_all_tipos(self):
        """Retorna todos los tipos ordenados por nombre."""
        try:
            rows = self.db.fetch_all('SELECT id, nombre, descripcion, shopify_taxonomy, fide_porcentaje FROM tipos ORDER BY nombre')
            return [dict(id=r[0], nombre=r[1], descripcion=r[2], shopify_taxonomy=r[3], fide_porcentaje=r[4]) for r in rows] if rows else []
        except Exception as e:
            logging.error(f"Error en get_all_tipos: {e}")
            return []

    def save_tipo(self, nombre: str, descripcion: str = '', fide_porcentaje: float = 0.0, shopify_taxonomy: str = '') -> int:
        """Inserta un nuevo tipo y retorna su id."""
        try:
            cur = self.db.execute_query('INSERT INTO tipos (nombre, descripcion, shopify_taxonomy, fide_porcentaje) VALUES (?, ?, ?, ?)', (nombre, descripcion, shopify_taxonomy, float(fide_porcentaje)))
            return cur.lastrowid
        except Exception as e:
            logging.error(f"Error guardando tipo: {e}")
            raise

    def update_tipo(self, id: int, nombre: str, descripcion: str = '', fide_porcentaje: float = 0.0, shopify_taxonomy: str = '') -> bool:
        """Actualiza un tipo existente."""
        try:
            self.db.execute_query('UPDATE tipos SET nombre = ?, descripcion = ?, shopify_taxonomy = ?, fide_porcentaje = ? WHERE id = ?', (nombre, descripcion, shopify_taxonomy, float(fide_porcentaje), id))
            return True
        except Exception as e:
            logging.error(f"Error actualizando tipo {id}: {e}")
            return False

    def delete_tipo(self, id: int) -> bool:
        """Elimina un tipo por id."""
        try:
            self.db.execute_query('DELETE FROM tipos WHERE id = ?', (id,))
            return True
        except Exception as e:
            logging.error(f"Error eliminando tipo {id}: {e}")
            return False
