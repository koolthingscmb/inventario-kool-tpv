from .db_wrapper import Database
import logging

from kool_tpv.modulos.almacen.categoria_repository import CategoriaRepository


class CategoriaService:
    def __init__(self, db):
        self.db = db
        self.repo = CategoriaRepository(db)

    def get_categorias_con_productos(self):
        try:
            return self.repo.get_con_productos()
        except Exception:
            logging.exception('Error obteniendo categorías con productos')
            return []

    def get_all(self):
        try:
            return self.repo.get_all()
        except Exception:
            logging.exception('Error listando categorías')
            return []

    def save(self, nombre: str, descripcion: str = '', shopify_taxonomy: str = '', fide_porcentaje: float = 0.0) -> int:
        try:
            return self.repo.insert(nombre, descripcion, shopify_taxonomy, fide_porcentaje)
        except Exception:
            logging.exception('Error guardando categoría')
            raise

    def update(self, id: int, nombre: str, descripcion: str = '', shopify_taxonomy: str = '', fide_porcentaje: float = 0.0) -> bool:
        try:
            self.repo.update(id, nombre, descripcion, shopify_taxonomy, fide_porcentaje)
            return True
        except Exception:
            logging.exception('Error actualizando categoría %s', id)
            return False

    def delete(self, id: int) -> bool:
        try:
            self.repo.delete(id)
            return True
        except Exception:
            logging.exception('Error eliminando categoría %s', id)
            return False
