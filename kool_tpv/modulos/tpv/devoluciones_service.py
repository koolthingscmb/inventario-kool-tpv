"""Servicio para gestionar devoluciones: bloqueo de ventas, añadir líneas de devolución
y actualización de stock dentro de la base de datos.

Responsabilidades:
- start_devolucion / end_devolucion: marcar carrito en modo devolución (bloqueo ventas positivas)
- add_devolucion_item: actualizar stock en BD, registrar movimiento y añadir línea al carrito
"""
from __future__ import annotations
from typing import Any, Dict
import logging

from decimal import Decimal
from kool_tpv.base_datos.db_wrapper import Database


class DevolucionesService:
    def __init__(self, db: Database, carrito_service: Any):
        self.db = db
        self.carrito = carrito_service

    def start_devolucion(self) -> None:
        try:
            setattr(self.carrito, '_devolucion_active', True)
            logging.info('DevolucionesService: devolucion iniciada (ventas bloqueadas)')
        except Exception:
            logging.exception('Error iniciando devolucion')

    def end_devolucion(self) -> None:
        try:
            setattr(self.carrito, '_devolucion_active', False)
            logging.info('DevolucionesService: devolucion finalizada (ventas permitidas)')
        except Exception:
            logging.exception('Error finalizando devolucion')

    def add_devolucion_item(self, producto: Dict[str, Any], cantidad: int = 1) -> bool:
        """Añade una línea de devolución al carrito y actualiza stock en BD.

        Args:
            producto: diccionario con al menos `id`, `nombre`, `pvp`, `tipo_iva`.
            cantidad: unidades devueltas (positivas).
        Returns:
            True si se añadió correctamente, False si hubo error.
        """
        try:
            if not producto or 'id' not in producto:
                logging.error('add_devolucion_item: producto inválido')
                return False

            prod_id = int(producto.get('id'))
            qty = int(cantidad)

            # Update stock in DB: increment stock_actual by cantidad
            try:
                if self.db is None:
                    logging.warning('DevolucionesService: no hay DB, no se actualizará stock en BD')
                else:
                    # Use a transaction via execute_query
                    update_q = "UPDATE productos SET stock_actual = COALESCE(stock_actual,0) + ? WHERE id = ?"
                    self.db.execute_query(update_q, (qty, prod_id))
                    insert_sm = "INSERT INTO stock_movements (producto_id, cantidad, motivo) VALUES (?, ?, ?)"
                    self.db.execute_query(insert_sm, (prod_id, qty, 'devolucion'))
            except Exception:
                logging.exception('DevolucionesService: error actualizando stock en BD')

            # Build product data for carrito: ensure pvp and tipo_iva exist
            prod_for_cart = {
                'id': producto.get('id'),
                'nombre': producto.get('nombre', ''),
                'pvp': producto.get('pvp', producto.get('precio') or 0),
                'tipo_iva': producto.get('tipo_iva', producto.get('iva', 21)),
                'cantidad': qty,
                'line_tipo': 'devolucion'
            }

            try:
                # Ensure carrito is in devolucion mode
                self.start_devolucion()
                added = False
                if hasattr(self.carrito, 'add_item'):
                    added = self.carrito.add_item(prod_for_cart)
                else:
                    logging.error('Carrito no soporta add_item, no se añadió la línea')
                    added = False
                return bool(added)
            except Exception:
                logging.exception('DevolucionesService: error añadiendo item al carrito')
                return False
        except Exception:
            logging.exception('DevolucionesService: fallo en add_devolucion_item')
            return False
