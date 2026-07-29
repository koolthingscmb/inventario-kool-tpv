"""Servicio de negocio para la gestión de pedidos de clientes (Cabecera + Líneas)."""
import logging
from typing import List, Dict, Any, Optional
from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.clientes.services.pedidos_repository import PedidosRepository

logger = logging.getLogger(__name__)

class PedidosService:
    def __init__(self, db: Database):
        self.db = db
        self.repo = PedidosRepository(db)

    def get_pedidos(self, estado: Optional[str] = None, cliente_id: Optional[int] = None, termino: str = "") -> List[Dict[str, Any]]:
        return self.repo.get_pedidos(estado, cliente_id, termino)

    def get_lineas_pedido(self, pedido_id: int) -> List[Dict[str, Any]]:
        return self.repo.get_lineas_pedido(pedido_id)

    def get_pedido_por_id(self, pedido_id: int) -> Optional[Dict[str, Any]]:
        return self.repo.get_pedido_por_id(pedido_id)

    def borrar_pedido(self, pedido_id: int) -> bool:
        return self.repo.borrar_pedido(pedido_id)

    def guardar_pedido(self, cabecera: Dict[str, Any], lineas: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Orquestar el guardado de un pedido completo."""
        if not lineas:
            return {'success': False, 'error': 'El pedido debe tener al menos una línea.'}
        
        # Validar si alguna línea ya está en stock antes de guardar
        from kool_tpv.base_datos.producto_service import ProductoService
        prod_service = ProductoService(self.db)
        
        for lin in lineas:
            if lin.get('producto_id'):
                prod = prod_service.get_producto_completo(lin['producto_id'])
                if prod and prod.get('stock_actual', 0) >= lin.get('cantidad', 1):
                    lin['estado_linea'] = 'distribuidor'

        pedido_id = self.repo.guardar_pedido_completo(cabecera, lineas)
        if pedido_id:
            # Si tiene vale asociado, marcarlo como reservado en el archivo JSON
            vale_id = cabecera.get('vale_id')
            if vale_id:
                try:
                    from kool_tpv.modulos.tpv.vale_devolucion_service import ValeDevolucionService
                    vale_service = ValeDevolucionService()
                    vale_service.marcar_reservado(vale_id, pedido_id)
                except Exception:
                    logger.exception(f"Error marcando vale {vale_id} como reservado al guardar pedido")
            
            return {'success': True, 'pedido_id': pedido_id}
        else:
            return {'success': False, 'error': 'Error interno al guardar en la base de datos.'}

    def actualizar_estado_linea(self, linea_id: int, nuevo_estado: str) -> bool:
        return self.repo.actualizar_estado_linea(linea_id, nuevo_estado)

    def actualizar_estado(self, pedido_id: int, nuevo_estado: str) -> bool:
        """Actualizar el estado del pedido (cabecera)."""
        return self.repo.actualizar_estado_pedido(pedido_id, nuevo_estado)

    def asociar_vale(self, pedido_id: int, vale_id: str) -> bool:
        """Vincular un vale de devolución a un pedido."""
        if self.repo.asociar_vale(pedido_id, vale_id):
            try:
                from kool_tpv.modulos.tpv.vale_devolucion_service import ValeDevolucionService
                vale_service = ValeDevolucionService()
                vale_service.marcar_reservado(vale_id, pedido_id)
            except Exception:
                logger.exception(f"Error marcando vale {vale_id} como reservado al asociar a pedido {pedido_id}")
            return True
        return False

    def marcar_entregado_por_vale(self, vale_id: str) -> bool:
        """Marcar como entregado el pedido asociado a un vale."""
        return self.repo.marcar_entregado_por_vale(vale_id)

    def get_lineas_pendientes_por_producto(self, producto_id: int) -> List[Dict[str, Any]]:
        """Obtener líneas pendientes asociadas a un producto."""
        return self.repo.get_lineas_pendientes_por_producto(producto_id)

    def actualizar_pedidos_por_stock(self, producto_ids: List[int]) -> int:
        """Llamado desde AlbaranService para actualizar estados de líneas."""
        return self.repo.actualizar_lineas_por_stock(producto_ids)

    def get_estados(self) -> List[Dict[str, str]]:
        return [
            {'id': 'pendiente', 'nombre': 'PENDIENTE', 'color': '#FFBB00'},
            {'id': 'distribuidor', 'nombre': 'DISTRIBUIDOR', 'color': '#00CC66'},
            {'id': 'avisado', 'nombre': 'AVISADO', 'color': '#00A4DF'},
            {'id': 'entregado', 'nombre': 'ENTREGADO', 'color': '#888888'},
            {'id': 'cancelado', 'nombre': 'CANCELADO', 'color': '#FF4444'}
        ]
