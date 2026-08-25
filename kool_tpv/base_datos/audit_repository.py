import logging
from typing import List, Dict, Any, Optional
from kool_tpv.base_datos.db_wrapper import Database

logger = logging.getLogger(__name__)

class AuditRepository:
    def __init__(self, db: Database):
        self.db = db

    def fetch_logs(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Obtiene los logs de auditoría aplicando filtros opcionales.
        
        Filters keys:
            entidad (str): Nombre de la entidad
            usuario_id (int): ID del usuario
            accion (str): Tipo de acción
            fecha_inicio (str): Fecha inicio (YYYY-MM-DD)
            fecha_fin (str): Fecha fin (YYYY-MM-DD)
        """
        query = """
            SELECT 
                a.id, 
                a.entidad, 
                a.entidad_id, 
                a.accion, 
                a.usuario_id, 
                u.nombre as usuario_nombre,
                a.datos_previos, 
                a.datos_nuevos, 
                a.created_at
            FROM audit_logs a
            LEFT JOIN usuarios u ON a.usuario_id = u.id
            WHERE 1=1
        """
        params = []

        if filters:
            if filters.get('entidad'):
                query += " AND a.entidad = ?"
                params.append(filters['entidad'])
            
            if filters.get('usuario_id'):
                query += " AND a.usuario_id = ?"
                params.append(filters['usuario_id'])
            
            if filters.get('accion'):
                query += " AND a.accion = ?"
                params.append(filters['accion'])
            
            if filters.get('fecha_inicio'):
                query += " AND a.created_at >= ?"
                params.append(f"{filters['fecha_inicio']} 00:00:00")
            
            if filters.get('fecha_fin'):
                query += " AND a.created_at <= ?"
                params.append(f"{filters['fecha_fin']} 23:59:59")

        query += " ORDER BY a.created_at DESC LIMIT 1000"

        try:
            rows = self.db.fetch_all(query, tuple(params))
            
            result = []
            for row in rows:
                result.append({
                    'id': row[0],
                    'entidad': row[1],
                    'entidad_id': row[2],
                    'accion': row[3],
                    'usuario_id': row[4],
                    'usuario_nombre': row[5] or 'Sistema',
                    'datos_previos': row[6],
                    'datos_nuevos': row[7],
                    'created_at': row[8]
                })
            return result
        except Exception:
            logger.exception("Error al consultar audit_logs")
            return []
    def obtener_entidades(self) -> List[str]:
        """Obtiene la lista de todas las entidades que tienen registros de auditoría."""
        try:
            rows = self.db.fetch_all("SELECT DISTINCT entidad FROM audit_logs ORDER BY entidad ASC")
            return [row[0] for row in rows if row[0]]
        except Exception:
            logger.exception("Error al obtener entidades de audit_logs")
            return []

    def obtener_acciones(self) -> List[str]:
        """Obtiene la lista de todas las acciones registradas en auditoría."""
        try:
            rows = self.db.fetch_all("SELECT DISTINCT accion FROM audit_logs ORDER BY accion ASC")
            return [row[0] for row in rows if row[0]]
        except Exception:
            logger.exception("Error al obtener acciones de audit_logs")
            return []
