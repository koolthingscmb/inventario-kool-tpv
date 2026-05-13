import logging
from typing import Dict, Any
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
            cur = self.db.connection.cursor()
            cur.execute('BEGIN')
            cur.execute(
                """
                INSERT INTO niveles_fidelidad
                (level, nombre_nivel, grafismo_nivel, gasto_minimo, tipo_recompensa, detalle_recompensa)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    data['level'],
                    data['nombre_nivel'],
                    data['grafismo_nivel'],
                    data['gasto_minimo'],
                    data.get('tipo_recompensa'),
                    data.get('detalle_recompensa'),
                )
            )
            nuevo_id = cur.lastrowid
            self.db.connection.commit()
            logger.info('Nivel level=%s insertado con id=%s', data['level'], nuevo_id)
            return nuevo_id
        except Exception:
            self.db.connection.rollback()
            logger.exception('Error insertando nivel level=%s', data.get('level'))
            raise

    def actualizar_nivel(self, nivel_id: int, data: Dict[str, Any]) -> None:
        """Actualiza un nivel existente.

        Raises:
            Exception si falla la actualización.
        """
        try:
            cur = self.db.connection.cursor()
            cur.execute('BEGIN')
            cur.execute(
                """
                UPDATE niveles_fidelidad
                SET level = ?, nombre_nivel = ?, grafismo_nivel = ?,
                    gasto_minimo = ?, tipo_recompensa = ?, detalle_recompensa = ?
                WHERE id = ?
                """,
                (
                    data['level'],
                    data['nombre_nivel'],
                    data['grafismo_nivel'],
                    data['gasto_minimo'],
                    data.get('tipo_recompensa'),
                    data.get('detalle_recompensa'),
                    nivel_id,
                )
            )
            self.db.connection.commit()
            logger.info('Nivel id=%s actualizado', nivel_id)
        except Exception:
            self.db.connection.rollback()
            logger.exception('Error actualizando nivel id=%s', nivel_id)
            raise

    def eliminar_nivel(self, nivel_id: int) -> None:
        """Elimina un nivel por ID.

        Raises:
            Exception si falla la eliminación.
        """
        try:
            cur = self.db.connection.cursor()
            cur.execute('BEGIN')
            cur.execute('DELETE FROM niveles_fidelidad WHERE id = ?', (nivel_id,))
            self.db.connection.commit()
            logger.info('Nivel id=%s eliminado', nivel_id)
        except Exception:
            self.db.connection.rollback()
            logger.exception('Error eliminando nivel id=%s', nivel_id)
            raise
