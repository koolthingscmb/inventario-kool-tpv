"""Repositorio para operaciones SQL específicas de devoluciones.

Este módulo centraliza las consultas relacionadas con devoluciones,
movimientos de puntos y actualizaciones en clientes para permitir
operaciones transaccionales y pruebas más sencillas.
"""
from __future__ import annotations
from typing import Optional
from datetime import datetime, timezone
import logging

from kool_tpv.base_datos.db_wrapper import Database

logger = logging.getLogger(__name__)


class DevolucionRepository:
    def __init__(self, db: Database):
        self.db = db

    def insert_devolucion(self, ticket_id: int, cliente_id: Optional[int], cajero: Optional[str], total_cents: int, created_at: Optional[str] = None, cur=None) -> int:
        """Inserta una fila en la tabla `devoluciones`.

        Devuelve el id del registro insertado o lanza excepción si falla.
        """
        use_external_cursor = cur is not None
        if not use_external_cursor:
            cur = self.db.connection.cursor()

        try:
            if created_at is None:
                created_at = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

            insert_q = (
                "INSERT INTO devoluciones (ticket_id, cliente_id, cajero, total_cents, created_at) "
                "VALUES (?, ?, ?, ?, COALESCE(?, CURRENT_TIMESTAMP))"
            )
            cur.execute(insert_q, (ticket_id, cliente_id, cajero, int(total_cents), created_at))
            if not use_external_cursor:
                self.db.connection.commit()
            return cur.lastrowid
        except Exception:
            logger.exception('Error insertando devolucion (ticket_id=%s)', ticket_id)
            raise

    def update_cliente_total_devoluciones(self, cliente_id: int, delta_cents: int, cur=None) -> None:
        use_external_cursor = cur is not None
        if not use_external_cursor:
            cur = self.db.connection.cursor()
        try:
            cur.execute('UPDATE clientes SET total_devoluciones = COALESCE(total_devoluciones,0) + ? WHERE id = ?', (int(delta_cents), cliente_id))
            if not use_external_cursor:
                self.db.connection.commit()
        except Exception:
            logger.exception('Error actualizando total_devoluciones para cliente_id=%s', cliente_id)
            raise

    def insert_points_movement(self, cliente_id: int, puntos: int, motivo: str, ticket_id: Optional[int] = None, usuario_id: Optional[int] = None, created_at: Optional[str] = None, cur=None) -> None:
        """Inserta un movimiento en `points_movements`.

        No eleva si la tabla no existe (comportamiento tolerante similar al resto del repo).
        """
        try:
            if created_at is None:
                try:
                    created_at = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
                except Exception:
                    created_at = None

            use_external_cursor = cur is not None
            if not use_external_cursor:
                cur = self.db.connection.cursor()
            cur.execute(
                'INSERT INTO points_movements (cliente_id, puntos, motivo, ticket_id, usuario_id, created_at) VALUES (?, ?, ?, ?, ?, ?)',
                (cliente_id, int(puntos), motivo, ticket_id, usuario_id, created_at),
            )
            if not use_external_cursor:
                self.db.connection.commit()
        except Exception:
            logger.warning('points_movements insert ignored or failed')
            # No raise: mantener tolerancia para entornos antiguos
