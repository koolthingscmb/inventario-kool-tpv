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
from kool_tpv.modulos.ticket.devolucion_processor import DevolucionProcessor
from kool_tpv.base_datos.money_adapter import prepare_for_db


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

            # NOTE: Do NOT update DB here. Stock updates are centralized in save_ticket().
            # DevolucionesService should only prepare the carrito line and set devolucion mode.

            # Build product data for carrito: ensure pvp and tipo_iva exist
            prod_for_cart = {
                'id': producto.get('id'),
                'sku': producto.get('sku', ''),
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

    def confirmar_devolucion(
        self,
        usuario: str = None,
        cliente_id: int = None,
        efectivo: Decimal = None,
        forma_pago: str = 'Efectivo',
        importe_efectivo: Decimal = None,
        importe_tarjeta: Decimal = None,
        descuento_data: Dict = None
    ):
        """Confirmar devolución delegando a save_ticket y finalizando modo devolución.

        Wrapper que:
        1. Obtiene items del carrito
        2. Delega a save_ticket con parámetros normalizados
        3. Finaliza modo devolución automáticamente
        4. Retorna (ticket_id, num_ticket) igual que save_ticket

        Args:
            usuario: Nombre del cajero/usuario
            cliente_id: ID del cliente (opcional)
            efectivo: Cantidad pagada/devuelta
            forma_pago: Método de pago
            importe_efectivo: Desglose efectivo
            importe_tarjeta: Desglose tarjeta
            descuento_data: Datos de descuento aplicado

        Returns:
            tuple: (ticket_id, num_ticket)

        Raises:
            RuntimeError: Si el carrito está vacío o save_ticket falla
        """
        try:
            # Validar que hay items en el carrito
            if not self.carrito or not hasattr(self.carrito, 'get_items'):
                raise RuntimeError('Carrito no disponible')

            items = self.carrito.get_items()
            if not items:
                raise RuntimeError('No hay items en el carrito para devolver')

            # Obtener resumen financiero
            try:
                resumen = self.carrito.get_resumen_financiero()
            except Exception:
                logging.exception('Error obteniendo resumen financiero')
                resumen = {}

            # Normalizar efectivo a Decimal
            try:
                if efectivo is None:
                    # Si no se proporciona, usar total del resumen
                    efectivo = Decimal(str(resumen.get('total', 0)))
                else:
                    efectivo = Decimal(str(efectivo))
            except Exception:
                efectivo = Decimal('0')

            # Normalizar importes
            try:
                importe_efectivo = Decimal(str(importe_efectivo)) if importe_efectivo is not None else Decimal('0')
            except Exception:
                importe_efectivo = Decimal('0')

            try:
                importe_tarjeta = Decimal(str(importe_tarjeta)) if importe_tarjeta is not None else Decimal('0')
            except Exception:
                importe_tarjeta = Decimal('0')

            # Obtener cliente desde carrito si no se proporcionó
            cliente_nombre = None
            if cliente_id is None:
                try:
                    cliente_data = self.carrito.get_cliente()
                    if cliente_data:
                        cliente_id = cliente_data.get('id')
                        cliente_nombre = cliente_data.get('nombre')
                except Exception:
                    pass

            # Delegar a DevolucionProcessor directamente para asegurar NULLs en BD
            logging.info(f'DevolucionesService: confirmando devolución usuario={usuario} cliente_id={cliente_id}')

            # Convertir importes/resumen a céntimos y construir payload para el processor
            try:
                subtotal_cents = prepare_for_db(Decimal(str(resumen.get('subtotal', 0))))
            except Exception:
                subtotal_cents = prepare_for_db(Decimal('0'))
            try:
                total_cents = prepare_for_db(Decimal(str(resumen.get('total', 0))))
            except Exception:
                total_cents = prepare_for_db(Decimal('0'))

            pagado_cents = prepare_for_db(efectivo) if efectivo is not None else None
            try:
                cambio_cents = prepare_for_db(efectivo - Decimal(str(resumen.get('total', 0)))) if efectivo is not None else None
            except Exception:
                cambio_cents = None

            # For devoluciones we do not persist a payment method or importe desglose: pass None
            payload = {
                'created_at': None,
                'num_ticket': None,
                'cajero': usuario,
                'cliente': cliente_nombre,
                'cliente_id': cliente_id,
                'subtotal_cents': subtotal_cents,
                'total_cents': total_cents,
                'pagado_cents': pagado_cents,
                'cambio_cents': cambio_cents,
                'importe_efectivo_cents': None,
                'importe_tarjeta_cents': None,
                'descuento_euros_cents': 0,
                'descuento_tipo': (descuento_data.get('tipo') if descuento_data else None),
                'descuento_valor': (descuento_data.get('valor') if descuento_data else None),
                'forma_pago': None,
                'puntos_otorgar_cents': 0,
                'puntos_gastados_cents': 0,
                'ticket_text_snapshot': None,
                'carrito_items': items,
                'resumen': resumen,
                'pagos': [],
            }

            processor = DevolucionProcessor(self.db)
            ticket_id = processor.process(**payload)
            num_ticket = None

            # Finalizar modo devolución tras éxito
            try:
                self.end_devolucion()
            except Exception:
                logging.exception('Error finalizando modo devolución tras confirmar')

            logging.info(f'DevolucionesService: devolución confirmada ticket_id={ticket_id} num={num_ticket}')

            return (ticket_id, num_ticket)

        except Exception as e:
            # Cleanup: finalizar modo devolución aunque falle
            try:
                self.end_devolucion()
            except Exception:
                pass

            logging.exception('Error confirmando devolución')
            raise RuntimeError(f'Error confirmando devolución: {e}')
