import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

class AuditService:
    """Servicio centralizado para la gestión de logs de auditoría."""

    def __init__(self, db):
        self.db = db

    def registrar(self, entidad: str, entidad_id: Optional[int], accion: str, 
                  usuario_id: Optional[int] = None, datos_previos: Optional[str] = None, 
                  datos_nuevos: Optional[str] = None, cur=None):
        """Inserta un registro en audit_logs.
        
        Args:
            entidad: Nombre de la tabla/entidad (ej: 'albaranes', 'productos')
            entidad_id: ID del registro afectado
            accion: Acción realizada (ej: 'CREACION', 'EDICION', 'AJUSTE_STOCK')
            usuario_id: ID del usuario que realiza la acción
            datos_previos: JSON o texto con el estado anterior
            datos_nuevos: JSON o texto con el nuevo estado
            cur: Cursor de base de datos (para transacciones externas)
        """
        try:
            created_at = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
            
            query = """
            INSERT INTO audit_logs 
            (entidad, entidad_id, accion, usuario_id, datos_previos, datos_nuevos, created_at) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            params = (entidad, entidad_id, accion, usuario_id, datos_previos, datos_nuevos, created_at)
            
            if cur:
                cur.execute(query, params)
            else:
                with self.db.transaction() as cur_trans:
                    cur_trans.execute(query, params)
                    
        except Exception:
            logger.exception(f"Error registrando auditoría para {entidad} ID {entidad_id}")
