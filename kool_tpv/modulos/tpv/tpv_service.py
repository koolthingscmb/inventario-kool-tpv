"""kool_tpv.modulos.tpv.tpv_service

Módulo de servicio (placeholder) para lógica de negocio del TPV.
Contendrá funciones para guardar tickets, gestionar líneas, calcular totales, etc.
"""

from __future__ import annotations
from typing import Any, Optional

class TpvService:
    """Servicio para operaciones de TPV (placeholder).

    Implementar métodos reales en próximas iteraciones.
    """

    def __init__(self, db: Optional[Any] = None):
        self.db = db

    def save_ticket(self, ticket_data: dict) -> int:
        raise NotImplementedError

    def add_ticket_line(self, ticket_id: int, line: dict) -> None:
        raise NotImplementedError

    def calculate_totals(self, ticket: dict) -> dict:
        raise NotImplementedError


__all__ = ["TpvService"]
