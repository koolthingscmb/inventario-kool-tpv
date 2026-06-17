"""PresenciaRepository: Acceso a BD para el control de fichajes."""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

class PresenciaRepository:
    def __init__(self, db):
        self.db = db

    def get_sesion_activa(self, usuario_id: int) -> Optional[Dict[str, Any]]:
        """Busca una sesión abierta ('activa') para un usuario."""
        query = "SELECT * FROM presencia WHERE usuario_id = ? AND estado = 'activa' LIMIT 1"
        row = self.db.fetch_one(query, (usuario_id,))
        return dict(row) if row else None

    def registrar_entrada(self, usuario_id: int, notas: str = "") -> int:
        """Crea un nuevo registro de entrada."""
        query = "INSERT INTO presencia (usuario_id, entrada, estado, notas) VALUES (?, CURRENT_TIMESTAMP, 'activa', ?)"
        # Usamos execute_query y last_insert_rowid si el wrapper lo permite, 
        # o accedemos directamente al cursor.
        cur = self.db.connection.cursor()
        cur.execute(query, (usuario_id, notas))
        self.db.connection.commit()
        return cur.lastrowid

    def registrar_salida(self, sesion_id: int) -> bool:
        """Cierra una sesión activa calculando la duración."""
        # Primero obtenemos la fecha de entrada para calcular minutos
        query_data = "SELECT entrada FROM presencia WHERE id = ?"
        row = self.db.fetch_one(query_data, (sesion_id,))
        if not row:
            return False
        
        # En SQLite podemos usar strftime para calcular minutos entre timestamps
        query_update = """
            UPDATE presencia 
            SET salida = CURRENT_TIMESTAMP, 
                estado = 'completada',
                duracion_minutos = (strftime('%s', 'now') - strftime('%s', entrada)) / 60
            WHERE id = ?
        """
        self.db.execute_query(query_update, (sesion_id,))
        return True

    def get_ultimos_fichajes(self, usuario_id: int, limite: int = 5) -> List[Dict[str, Any]]:
        """Obtiene los últimos N fichajes de un usuario."""
        query = "SELECT * FROM presencia WHERE usuario_id = ? ORDER BY entrada DESC LIMIT ?"
        rows = self.db.fetch_all(query, (usuario_id, limite))
        return [dict(r) for r in rows] if rows else []
