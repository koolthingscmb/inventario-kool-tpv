import logging
from typing import List, Dict, Any
from kool_tpv.modulos.almacen.stock_movement_repository import StockMovementRepository

logger = logging.getLogger(__name__)

class StockMovementService:
    def __init__(self, db):
        self.db = db
        self.repo = StockMovementRepository(db)

    def obtener_historial_producto(self, producto_id: int) -> List[Dict[str, Any]]:
        """Obtiene y formatea el historial de movimientos para la UI."""
        if not producto_id:
            return []
        
        movements = self.repo.get_by_producto(producto_id)
        
        # Podríamos añadir lógica de formateo aquí si fuera necesario
        return movements

    def registrar_ajuste_manual(self, producto_id: int, cantidad: int, motivo: str, usuario_id: int, cur=None) -> bool:
        """Registra un ajuste manual a través del repositorio."""
        return self.repo.registrar_movimiento(
            producto_id=producto_id,
            cantidad=cantidad,
            motivo=f"AJUSTE MANUAL: {motivo}",
            usuario_id=usuario_id,
            cur=cur
        )
