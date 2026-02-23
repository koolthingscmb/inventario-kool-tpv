"""Servicios para obtener 'tops' de clientes (backend).

Este módulo expone `ClientesTopsService` con consultas limpias hacia la
tabla `clientes` para calcular rankings/posiciones en Python.
"""
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


class ClientesTopsService:
    """Servicio que provee rankings/Top de clientes."""

    @staticmethod
    def get_top_clientes_general(db, limit: int = 50) -> List[Dict]:
        """
        Obtiene el Top general de clientes ordenado por `total_compras_euros`.

        Args:
            db: instancia del wrapper Database (debe exponer .connection)
            limit: número máximo de filas a devolver

        Returns:
            Lista de diccionarios con claves: posicion, cliente_id, nombre,
            total_tickets, total_unidades, total_euros
        """
        if db is None:
            return []

        try:
            conn = getattr(db, 'connection', None)
            if conn is None:
                return []
            cur = conn.cursor()

            q = (
                "SELECT id, nombre, COALESCE(total_compras,0) AS total_compras, "
                "COALESCE(total_unidades,0) AS total_unidades, "
                "COALESCE(total_compras_euros,0) AS total_compras_euros "
                "FROM clientes "
                "WHERE COALESCE(total_compras_euros,0) > 0 "
                "ORDER BY total_compras_euros DESC "
                "LIMIT ?"
            )
            cur.execute(q, (limit,))
            rows = cur.fetchall() or []

            result: List[Dict] = []
            for idx, row in enumerate(rows, start=1):
                try:
                    cliente_id = int(row[0]) if row[0] is not None else None
                except Exception:
                    cliente_id = None
                try:
                    nombre = str(row[1]) if row[1] is not None else ''
                except Exception:
                    nombre = ''
                try:
                    total_tickets = int(row[2]) if row[2] is not None else 0
                except Exception:
                    total_tickets = 0
                try:
                    total_unidades = int(row[3]) if row[3] is not None else 0
                except Exception:
                    total_unidades = 0
                try:
                    total_euros = float(row[4]) if row[4] is not None else 0.0
                except Exception:
                    # fallback: try converting from decimal/string
                    try:
                        total_euros = float(str(row[4]))
                    except Exception:
                        total_euros = 0.0

                result.append({
                    'posicion': idx,
                    'cliente_id': cliente_id,
                    'nombre': nombre,
                    'total_tickets': total_tickets,
                    'total_unidades': total_unidades,
                    'total_euros': total_euros,
                })

            return result
        except Exception:
            logger.exception('Error obteniendo top general de clientes')
            return []
