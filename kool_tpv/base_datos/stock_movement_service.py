import logging
from typing import List, Dict, Any, Optional
from kool_tpv.base_datos.stock_movement_repository import StockMovementRepository

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

    def aplicar_movimiento(self, producto_id: int, cantidad: int, motivo: str,
                           usuario_id: Optional[int] = None,
                           ticket_line_id: Optional[int] = None,
                           ventas_change: int = 0,
                           encolar_sync: bool = True,
                           motivo_sync: Optional[str] = None,
                           cur=None) -> bool:
        """Aplica un cambio de stock completo: actualiza productos, registra el
        movimiento en el historial y encola la sincronización a Shopify.

        Pensado para llamarse dentro de la transacción del llamador: si ésta se
        deshace, el cambio, el movimiento y el encargo desaparecen juntos.
        `ventas_change` suma al contador de ventas del producto (tickets).
        `encolar_sync=False` para quien gestiona sus propios encargos (albaranes).
        `motivo_sync` etiqueta el encargo si difiere del motivo del movimiento.
        """
        if not producto_id:
            return False
        ok = self.repo.aplicar_movimiento(
            producto_id=producto_id,
            cantidad=cantidad,
            motivo=motivo,
            usuario_id=usuario_id,
            ticket_line_id=ticket_line_id,
            ventas_change=ventas_change,
            cur=cur
        )
        if not ok:
            return False
        if encolar_sync:
            try:
                from kool_tpv.modulos.shopify.services.shopify_sync_service import ShopifySyncService
                ShopifySyncService(self.db).encolar_sync_producto(producto_id, motivo_sync or motivo, cur=cur)
            except Exception:
                logger.exception('Error encolando sync Shopify para producto_id=%s', producto_id)
        return True

    def registrar_movimiento(self, producto_id: int, cantidad: int, motivo: str,
                             usuario_id: Optional[int] = None,
                             ticket_line_id: Optional[int] = None,
                             cur=None) -> bool:
        """Registra un movimiento genérico de stock."""
        return self.repo.registrar_movimiento(
            producto_id=producto_id,
            cantidad=cantidad,
            motivo=motivo,
            usuario_id=usuario_id,
            ticket_line_id=ticket_line_id,
            cur=cur
        )
