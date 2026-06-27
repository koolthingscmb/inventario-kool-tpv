from .db_wrapper import Database
from typing import List
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

    def save_tipo(self, nombre: str, descripcion: str = '', fide_porcentaje: float = 0.0, shopify_taxonomy: str = '', color: str = None, icono: str = None, coste_base: float = 0.0, requiere_talla: int = 0, requiere_color: int = 0, activo: int = 1, orden: int = 0) -> int:
        try:
            return self.repo.insert(nombre, descripcion, shopify_taxonomy, fide_porcentaje, color, icono, coste_base, requiere_talla, requiere_color, activo, orden)
        except Exception:
            logging.exception('Error guardando tipo')
            raise

    def update_tipo(self, id: int, nombre: str, descripcion: str = '', fide_porcentaje: float = 0.0, shopify_taxonomy: str = '', color: str = None, icono: str = None, coste_base: float = 0.0, requiere_talla: int = 0, requiere_color: int = 0, activo: int = 1, orden: int = 0) -> bool:
        try:
            self.repo.update(id, nombre, descripcion, shopify_taxonomy, fide_porcentaje, color, icono, coste_base, requiere_talla, requiere_color, activo, orden)
            return True
        except Exception:
            logging.exception('Error actualizando tipo %s', id)
            return False

    def delete_tipo(self, id: int) -> tuple[bool, str]:
        """Elimina un tipo comprobando dependencias.
        Returns: (success, message)
        """
        try:
            # 1. Comprobar productos asociados
            res = self.db.fetch_one("SELECT COUNT(*) FROM productos WHERE tipo = ?", (id,))
            if res and res[0] > 0:
                return False, f"NO SE PUEDE ELIMINAR: TIENE {res[0]} PRODUCTOS ASOCIADOS"

            # 2. Comprobar relaciones de producción (si existen las tablas)
            try:
                res = self.db.fetch_one("SELECT COUNT(*) FROM produccion_tipos_colores WHERE tipo_id = ?", (id,))
                if res and res[0] > 0:
                    return False, "NO SE PUEDE ELIMINAR: TIENE COLORES ASOCIADOS EN MATRIZ"
            except Exception:
                # Si fallan estas queries es que las tablas no existen, ignoramos
                pass

            # 3. Intentar borrado físico
            self.repo.delete(id)
            return True, "TIPO ELIMINADO CORRECTAMENTE"

        except Exception as e:
            msg = str(e).upper()
            if "FOREIGN KEY" in msg:
                return False, "ERROR DE INTEGRIDAD: ESTÁ SIENDO USADO EN OTRA TABLA"
            logging.exception('Error eliminando tipo %s', id)
            return False, f"ERROR AL ELIMINAR: {msg}"

    def get_ventas_por_tipo(self, ticket_ids: List[int], line_tipo: str = None, as_dict: bool = False):
        """Delega al repo para obtener ventas por tipo.

        Args:
            ticket_ids: lista de IDs de tickets
            line_tipo: opcional, filtrar por tipo de línea ('venta'|'devolucion')
            as_dict: si True, devuelve lista de dicts con keys: nombre, tickets_cnt, uds, total
        """
        try:
            rows = self.repo.get_ventas_por_tipo(ticket_ids, line_tipo=line_tipo)
            if not as_dict:
                return rows

            result = []
            for r in (rows or []):
                try:
                    nombre = r[0]
                    tickets_cnt = int(r[1] or 0) if len(r) > 1 else 0
                    uds = int(r[2] or 0) if len(r) > 2 else 0
                    total = r[3] if len(r) > 3 else (r[2] if len(r) > 2 else 0)
                    result.append({'nombre': nombre, 'tickets_cnt': tickets_cnt, 'uds': uds, 'total': total})
                except Exception:
                    logging.exception('Error convirtiendo fila de ventas por tipo')
                    continue
            return result
        except Exception:
            logging.exception('Error obteniendo ventas por tipo')
            return []
