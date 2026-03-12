import logging
from typing import List, Optional, Dict, Any
from decimal import Decimal


class NivelesService:
    """Servicio para gestión de niveles de fidelización."""

    def __init__(self, db):
        self.db = db

    def get_all_niveles(self) -> List[Dict[str, Any]]:
        """Obtener todos los niveles ordenados por level.

        Returns:
            Lista de dicts con campos normalizados
        """
        try:
            query = """
                SELECT id, level, nombre_nivel, grafismo_nivel, gasto_minimo,
                       tipo_recompensa, detalle_recompensa
                FROM niveles_fidelidad
                ORDER BY level
            """
            rows = self.db.fetch_all(query)

            if not rows:
                return []

            niveles = []
            for row in rows:
                try:
                    niveles.append(self._row_to_dict(row))
                except Exception:
                    logging.exception('Error normalizando fila de nivel')
                    continue

            return niveles

        except Exception:
            logging.exception('Error obteniendo niveles')
            return []

    def get_nivel(self, nivel_id: int) -> Optional[Dict[str, Any]]:
        """Obtener un nivel por ID.

        Args:
            nivel_id: ID del nivel

        Returns:
            Dict con datos del nivel o None si no existe
        """
        try:
            query = """
                SELECT id, level, nombre_nivel, grafismo_nivel, gasto_minimo,
                       tipo_recompensa, detalle_recompensa
                FROM niveles_fidelidad
                WHERE id = ?
            """
            row = self.db.fetch_one(query, (nivel_id,))

            if not row:
                return None

            return self._row_to_dict(row)

        except Exception:
            logging.exception('Error obteniendo nivel %s', nivel_id)
            return None

    def save_nivel(self, data: Dict[str, Any]) -> bool:
        """Crear nuevo nivel.

        Args:
            data: Dict con level, nombre_nivel, grafismo_nivel, gasto_minimo,
                  tipo_recompensa (opcional), detalle_recompensa (opcional)

        Returns:
            True si se creó correctamente, False en caso de error
        """
        try:
            # Validar campos obligatorios
            if not all(k in data for k in ['level', 'nombre_nivel', 'grafismo_nivel', 'gasto_minimo']):
                logging.error('Faltan campos obligatorios en save_nivel')
                return False

            # Verificar que level no exista
            check = self.db.fetch_one("SELECT id FROM niveles_fidelidad WHERE level = ?", (data['level'],))
            if check:
                logging.warning('Ya existe un nivel con level %s', data['level'])
                return False

            conn = self.db.connection
            cur = conn.cursor()
            cur.execute('BEGIN')

            cur.execute("""
                INSERT INTO niveles_fidelidad
                (level, nombre_nivel, grafismo_nivel, gasto_minimo, tipo_recompensa, detalle_recompensa)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                data['level'],
                data['nombre_nivel'],
                data['grafismo_nivel'],
                data['gasto_minimo'],
                data.get('tipo_recompensa'),
                data.get('detalle_recompensa')
            ))

            conn.commit()
            logging.info('Nivel %s creado correctamente', data['level'])
            return True

        except Exception:
            try:
                self.db.connection.rollback()
            except Exception:
                pass
            logging.exception('Error guardando nivel')
            return False

    def update_nivel(self, nivel_id: int, data: Dict[str, Any]) -> bool:
        """Actualizar nivel existente.

        Args:
            nivel_id: ID del nivel a actualizar
            data: Dict con campos a actualizar

        Returns:
            True si se actualizó correctamente, False en caso de error
        """
        try:
            conn = self.db.connection
            cur = conn.cursor()
            cur.execute('BEGIN')

            cur.execute("""
                UPDATE niveles_fidelidad
                SET level = ?, nombre_nivel = ?, grafismo_nivel = ?,
                    gasto_minimo = ?, tipo_recompensa = ?, detalle_recompensa = ?
                WHERE id = ?
            """, (
                data['level'],
                data['nombre_nivel'],
                data['grafismo_nivel'],
                data['gasto_minimo'],
                data.get('tipo_recompensa'),
                data.get('detalle_recompensa'),
                nivel_id
            ))

            conn.commit()
            logging.info('Nivel %s actualizado correctamente', nivel_id)
            return True

        except Exception:
            try:
                self.db.connection.rollback()
            except Exception:
                pass
            logging.exception('Error actualizando nivel %s', nivel_id)
            return False

    def delete_nivel(self, nivel_id: int) -> bool:
        """Eliminar nivel.

        Args:
            nivel_id: ID del nivel a eliminar

        Returns:
            True si se eliminó correctamente, False en caso de error
        """
        try:
            conn = self.db.connection
            cur = conn.cursor()
            cur.execute('BEGIN')

            cur.execute("DELETE FROM niveles_fidelidad WHERE id = ?", (nivel_id,))

            conn.commit()
            logging.info('Nivel %s eliminado correctamente', nivel_id)
            return True

        except Exception:
            try:
                self.db.connection.rollback()
            except Exception:
                pass
            logging.exception('Error eliminando nivel %s', nivel_id)
            return False

    def get_next_level(self) -> int:
        """Calcular próximo número de level disponible.

        Returns:
            Siguiente level (MAX + 1, o 1 si no hay niveles)
        """
        try:
            query = "SELECT MAX(level) FROM niveles_fidelidad"
            row = self.db.fetch_one(query)
            max_level = row[0] if row and row[0] else 0
            return max_level + 1
        except Exception:
            logging.exception('Error calculando siguiente level')
            return 1

    def _row_to_dict(self, row) -> Dict[str, Any]:
        """Normalizar Row/tuple a dict.

        Args:
            row: sqlite3.Row o tuple

        Returns:
            Dict normalizado
        """
        if isinstance(row, tuple):
            return {
                'id': row[0],
                'level': row[1],
                'nombre_nivel': row[2] or '',
                'grafismo_nivel': row[3] or '',
                'gasto_minimo': row[4] or 0,
                'tipo_recompensa': row[5] or '',
                'detalle_recompensa': row[6] or ''
            }
        else:
            # sqlite3.Row - acceso por nombre de columna
            return {
                'id': row['id'],
                'level': row['level'],
                'nombre_nivel': row['nombre_nivel'] or '',
                'grafismo_nivel': row['grafismo_nivel'] or '',
                'gasto_minimo': row['gasto_minimo'] or 0,
                'tipo_recompensa': row['tipo_recompensa'] or '',
                'detalle_recompensa': row['detalle_recompensa'] or ''
            }
