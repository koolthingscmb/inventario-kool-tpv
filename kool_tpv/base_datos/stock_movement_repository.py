import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class StockMovementRepository:
    def __init__(self, db):
        self.db = db

    def get_by_producto(self, producto_id: int) -> List[Dict[str, Any]]:
        """Obtiene el historial de movimientos de stock de un producto con info de usuario."""
        try:
            query = """
                SELECT 
                    sm.id,
                    sm.producto_id,
                    sm.cantidad,
                    sm.motivo,
                    sm.usuario_id,
                    sm.created_at,
                    u.nombre as usuario_nombre,
                    sm.ticket_line_id
                FROM stock_movements sm
                LEFT JOIN usuarios u ON sm.usuario_id = u.id
                WHERE sm.producto_id = ?
                ORDER BY sm.created_at DESC
            """
            rows = self.db.fetch_all(query, (producto_id,))
            
            result = []
            for row in rows:
                result.append({
                    'id': row[0],
                    'producto_id': row[1],
                    'cantidad': row[2],
                    'motivo': row[3],
                    'usuario_id': row[4],
                    'created_at': row[5],
                    'usuario_nombre': row[6] or 'Sistema/Auto',
                    'ticket_line_id': row[7]
                })
            return result
        except Exception:
            logger.exception(f"Error obteniendo movimientos para producto_id={producto_id}")
            return []

    def registrar_movimiento(self, producto_id: int, cantidad: int, motivo: str, 
                             usuario_id: Optional[int] = None, 
                             ticket_line_id: Optional[int] = None,
                             cur=None) -> bool:
        """Registra un nuevo movimiento de stock."""
        try:
            query = """
                INSERT INTO stock_movements (producto_id, cantidad, motivo, usuario_id, ticket_line_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """
            created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            params = (producto_id, cantidad, motivo, usuario_id, ticket_line_id, created_at)
            
            if cur:
                cur.execute(query, params)
            else:
                with self.db.transaction() as cur_trans:
                    cur_trans.execute(query, params)
            return True
        except Exception:
            logger.exception(f"Error registrando movimiento para producto_id={producto_id}")
            return False
