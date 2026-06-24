"""Servicio para gestionar las órdenes de producción.

Contiene la lógica para guardar las órdenes y actualizar el stock de diseños.
"""
import logging
from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime

from kool_tpv.base_datos.db_wrapper import Database

@dataclass
class ItemProduccion:
    tipo_nombre: str
    tipo_id: int
    genero: Optional[str]
    genero_id: Optional[int]
    talla: Optional[str]
    color_nombre: Optional[str]
    color_id: Optional[int]
    diseno_codigo: str
    diseno_nombre: str
    cantidad: int
    produccion_mixta: bool
    coste_unitario: float
    coste_total: float
    variante_nombre: Optional[str] = None
    variante_id: Optional[int] = None

class ProduccionOrdenesService:
    def __init__(self, db: Database):
        self.db = db
        self.logger = logging.getLogger(__name__)

    def guardar_orden(self, items: List[ItemProduccion], usuario_id: Optional[int] = None) -> bool:
        """Guardar una orden de producción completa y actualizar el stock."""
        if not items:
            return False

        try:
            # 1. Crear la cabecera de la orden
            query_orden = """
                INSERT INTO produccion_ordenes (usuario_id, estado)
                VALUES (?, 'COMPLETADA')
            """
            self.db.execute_query(query_orden, (usuario_id,))
            
            # Obtener el ID de la orden creada
            res = self.db.fetch_all("SELECT last_insert_rowid()")
            orden_id = res[0][0]

            # 2. Guardar cada línea y actualizar stock
            for item in items:
                # Guardar línea
                query_linea = """
                    INSERT INTO produccion_lineas 
                    (orden_id, diseno_codigo, tipo_producto, talla, color_id, 
                     cantidad, produccion_mixta, usuario_produccion_id,
                     coste_unitario, coste_total, variante_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                # Convertir costes a céntimos para la BD
                coste_u_cent = int(item.coste_unitario * 100)
                coste_t_cent = int(item.coste_total * 100)
                
                self.db.execute_query(query_linea, (
                    orden_id, item.diseno_codigo, item.tipo_nombre, 
                    item.talla, item.color_id, item.cantidad,
                    1 if item.produccion_mixta else 0,
                    usuario_id,
                    coste_u_cent, coste_t_cent,
                    item.variante_id
                ))

                # 3. Actualizar stock acumulado
                self._actualizar_stock_diseno(item)

            return True

        except Exception:
            self.logger.exception("Error al guardar la orden de producción")
            return False

    def _actualizar_stock_diseno(self, item: ItemProduccion):
        """Actualizar la tabla produccion_disenos_stock."""
        try:
            # Intentar insertar o actualizar
            query = """
                INSERT INTO produccion_disenos_stock 
                (diseno_codigo, tipo_id, color_id, talla, cantidad)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(diseno_codigo, tipo_id, color_id, talla) 
                DO UPDATE SET cantidad = cantidad + excluded.cantidad
            """
            self.db.execute_query(query, (
                item.diseno_codigo, item.tipo_id, item.color_id, 
                item.talla, item.cantidad
            ))
        except Exception:
            self.logger.exception(f"Error actualizando stock para diseño {item.diseno_codigo}")
