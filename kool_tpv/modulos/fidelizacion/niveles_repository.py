import logging
from typing import Dict, Any, Optional
from kool_tpv.base_datos.db_wrapper import Database

logger = logging.getLogger(__name__)


class NivelesRepository:
    def __init__(self, db: Database):
        self.db = db

    def insertar_nivel(self, data: Dict[str, Any]) -> int:
        """Inserta un nuevo nivel en niveles_fidelidad.

        Returns:
            ID del nivel insertado.
        Raises:
            Exception si falla la inserción.
        """
        try:
            in_tx = getattr(self.db.connection, 'in_transaction', False)
            cur = self.db.connection.cursor()
            if not in_tx:
                cur.execute('BEGIN')
            cur.execute(
                """
                INSERT INTO niveles_fidelidad
                (level, nombre_nivel, grafismo_nivel, tesoro_minimo, tipo_recompensa, detalle_recompensa)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    data['level'],
                    data['nombre_nivel'],
                    data['grafismo_nivel'],
                    data['tesoro_minimo'],
                    data.get('tipo_recompensa'),
                    data.get('detalle_recompensa'),
                )
            )
            nuevo_id = cur.lastrowid
            if not in_tx:
                self.db.connection.commit()
            logger.info('Nivel level=%s insertado con id=%s', data['level'], nuevo_id)
            return nuevo_id
        except Exception:
            try:
                in_tx = getattr(self.db.connection, 'in_transaction', False)
                if not in_tx:
                    self.db.connection.rollback()
            except Exception:
                pass
            logger.exception('Error insertando nivel level=%s', data.get('level'))
            raise

    def actualizar_nivel(self, nivel_id: int, data: Dict[str, Any]) -> None:
        """Actualiza un nivel existente.

        Raises:
            Exception si falla la actualización.
        """
        try:
            in_tx = getattr(self.db.connection, 'in_transaction', False)
            cur = self.db.connection.cursor()
            if not in_tx:
                cur.execute('BEGIN')
            cur.execute(
                """
                UPDATE niveles_fidelidad
                SET level = ?, nombre_nivel = ?, grafismo_nivel = ?,
                    tesoro_minimo = ?, tipo_recompensa = ?, detalle_recompensa = ?
                WHERE id = ?
                """,
                (
                    data['level'],
                    data['nombre_nivel'],
                    data['grafismo_nivel'],
                    data['tesoro_minimo'],
                    data.get('tipo_recompensa'),
                    data.get('detalle_recompensa'),
                    nivel_id,
                )
            )
            if not in_tx:
                self.db.connection.commit()
            logger.info('Nivel id=%s actualizado', nivel_id)
        except Exception:
            try:
                in_tx = getattr(self.db.connection, 'in_transaction', False)
                if not in_tx:
                    self.db.connection.rollback()
            except Exception:
                pass
            logger.exception('Error actualizando nivel id=%s', nivel_id)
            raise

    def eliminar_nivel(self, nivel_id: int) -> None:
        """Elimina un nivel por ID.

        Raises:
            Exception si falla la eliminación.
        """
        try:
            in_tx = getattr(self.db.connection, 'in_transaction', False)
            cur = self.db.connection.cursor()
            if not in_tx:
                cur.execute('BEGIN')
            cur.execute('DELETE FROM niveles_fidelidad WHERE id = ?', (nivel_id,))
            if not in_tx:
                self.db.connection.commit()
            logger.info('Nivel id=%s eliminado', nivel_id)
        except Exception:
            try:
                in_tx = getattr(self.db.connection, 'in_transaction', False)
                if not in_tx:
                    self.db.connection.rollback()
            except Exception:
                pass
            logger.exception('Error eliminando nivel id=%s', nivel_id)
            raise

    def obtener_nivel_base(self) -> Optional[int]:
        """Devuelve el ID del nivel con tesoro_minimo más bajo (nivel base).

        Returns:
            ID del nivel base, o None si la tabla está vacía.
        """
        row = self.db.fetch_one(
            "SELECT id FROM niveles_fidelidad ORDER BY tesoro_minimo ASC LIMIT 1"
        )
        return row[0] if row else None

    def get_nivel_por_id(self, nivel_id: int) -> Optional[Dict[str, Any]]:
        """Obtiene un nivel por su ID."""
        if nivel_id is None:
            return None
        query = "SELECT id, level, nombre_nivel, grafismo_nivel, tesoro_minimo FROM niveles_fidelidad WHERE id = ?"
        row = self.db.fetch_one(query, (nivel_id,))
        if row:
            return {
                'id': row[0],
                'level': row[1],
                'nombre_nivel': row[2],
                'grafismo_nivel': row[3],
                'tesoro_minimo': row[4]
            }
        return None
