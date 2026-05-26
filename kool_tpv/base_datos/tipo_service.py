from .db_wrapper import Database
import logging

from kool_tpv.modulos.almacen.tipo_repository import TipoRepository


class TipoService:
    def __init__(self, db):
        self.db = db
        self.repo = TipoRepository(db)

    def get_tipos_con_productos(self):
        try:
            return self.repo.get_con_productos()
        except Exception:
            logging.exception('Error obteniendo tipos con productos')
            return []

    def get_all_tipos(self):
        try:
            return self.repo.get_all()
        except Exception:
            logging.exception('Error listando tipos')
            return []

    def save_tipo(self, nombre: str, descripcion: str = '', fide_porcentaje: float = 0.0, shopify_taxonomy: str = '') -> int:
        try:
            return self.repo.insert(nombre, descripcion, shopify_taxonomy, fide_porcentaje)
        except Exception:
            logging.exception('Error guardando tipo')
            raise

    def update_tipo(self, id: int, nombre: str, descripcion: str = '', fide_porcentaje: float = 0.0, shopify_taxonomy: str = '') -> bool:
        try:
            self.repo.update(id, nombre, descripcion, shopify_taxonomy, fide_porcentaje)
            return True
        except Exception:
            logging.exception('Error actualizando tipo %s', id)
            return False

    def delete_tipo(self, id: int) -> bool:
        try:
            self.repo.delete(id)
            return True
        except Exception:
            logging.exception('Error eliminando tipo %s', id)
            return False

    def get_ventas_por_tipo(self, ticket_ids: List[int], line_tipo: str = None):
        """Delega al repo para obtener ventas por tipo.

        Args:
            ticket_ids: lista de IDs de tickets
            line_tipo: opcional, filtrar por tipo de línea ('venta'|'devolucion')
        """
        try:
            return self.repo.get_ventas_por_tipo(ticket_ids, line_tipo=line_tipo)
        except Exception:
            logging.exception('Error obteniendo ventas por tipo')
            return []
