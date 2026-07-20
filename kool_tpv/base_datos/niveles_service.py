import logging
from typing import List, Optional, Dict, Any
from decimal import Decimal
from kool_tpv.modulos.fidelizacion.niveles_repository import NivelesRepository


class NivelesService:
    """Servicio para gestión de niveles de fidelización."""

    def __init__(self, db):
        self.db = db
        self.repo = NivelesRepository(db)

    def get_all_niveles(self) -> List[Dict[str, Any]]:
        """Obtener todos los niveles ordenados por level.

        Returns:
            Lista de dicts con campos normalizados
        """
        try:
            query = """
                SELECT id, level, nombre_nivel, grafismo_nivel, tesoro_minimo,
                       tipo_recompensa, detalle_recompensa, producto_sku, lore_recompensa,
                       codigo_recompensa, descuento_tipo, descuento_valor
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
                SELECT id, level, nombre_nivel, grafismo_nivel, tesoro_minimo,
                       tipo_recompensa, detalle_recompensa, producto_sku, lore_recompensa,
                       codigo_recompensa, descuento_tipo, descuento_valor
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
            if not all(k in data for k in ['level', 'nombre_nivel', 'grafismo_nivel', 'tesoro_minimo']):
                logging.error('Faltan campos obligatorios en save_nivel')
                return False

            # Verificar que level no exista
            check = self.db.fetch_one("SELECT id FROM niveles_fidelidad WHERE level = ?", (data['level'],))
            if check:
                logging.warning('Ya existe un nivel con level %s', data['level'])
                return False

            self.repo.insertar_nivel(data)
            return True

        except Exception:
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
            self.repo.actualizar_nivel(nivel_id, data)
            return True
        except Exception:
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
            self.repo.eliminar_nivel(nivel_id)
            return True
        except Exception:
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
                'tesoro_minimo': row[4] or 0,
                'tipo_recompensa': row[5] or '',
                'detalle_recompensa': row[6] or '',
                'producto_sku': row[7] or '',
                'lore_recompensa': row[8] or '',
                'codigo_recompensa': row[9] or '',
                'descuento_tipo': row[10] or '',
                'descuento_valor': row[11] or 0.0
            }
        else:
            # sqlite3.Row - acceso por nombre de columna
            return {
                'id': row['id'],
                'level': row['level'],
                'nombre_nivel': row['nombre_nivel'] or '',
                'grafismo_nivel': row['grafismo_nivel'] or '',
                'tesoro_minimo': row['tesoro_minimo'] or 0,
                'tipo_recompensa': row['tipo_recompensa'] or '',
                'detalle_recompensa': row['detalle_recompensa'] or '',
                'producto_sku': row['producto_sku'] or '',
                'lore_recompensa': row['lore_recompensa'] or '',
                'codigo_recompensa': row['codigo_recompensa'] or '',
                'descuento_tipo': row['descuento_tipo'] or '',
                'descuento_valor': row['descuento_valor'] or 0.0
            }
