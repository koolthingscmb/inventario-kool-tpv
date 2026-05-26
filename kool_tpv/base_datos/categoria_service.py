from .db_wrapper import Database
from typing import List
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

    def get_ventas_por_categoria(self, ticket_ids: List[int], line_tipo: str = None, as_dict: bool = False):
        """Delega al repo para obtener ventas por categoría.

        Args:
            ticket_ids: lista de IDs de tickets
            line_tipo: opcional, filtrar por tipo de línea ('venta'|'devolucion')
            as_dict: si True, devuelve lista de dicts con keys: nombre, tickets_cnt, uds, total
        """
        try:
            rows = self.repo.get_ventas_por_categoria(ticket_ids, line_tipo=line_tipo)
            if not as_dict:
                return rows

            # convertir tuples a dicts para un API explícito y menos frágil
            result = []
            for r in (rows or []):
                try:
                    # repo devuelve (nombre, tickets_cnt, uds, total_euros)
                    nombre = r[0]
                    tickets_cnt = int(r[1] or 0) if len(r) > 1 else 0
                    uds = int(r[2] or 0) if len(r) > 2 else 0
                    total = r[3] if len(r) > 3 else (r[2] if len(r) > 2 else 0)
                    result.append({'nombre': nombre, 'tickets_cnt': tickets_cnt, 'uds': uds, 'total': total})
                except Exception:
                    logging.exception('Error convirtiendo fila de ventas por categoría')
                    continue
            return result
        except Exception:
            logging.exception('Error obteniendo ventas por categoría')
            return []
