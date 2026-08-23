"""Modelo para grupos de tallas en producción."""
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class ProduccionTallaGrupo:
    """Grupo de tallas (ej: Adulto, Infantil, etc.)"""
    id: Optional[int] = None
    nombre: str = ""
    talla_ids: List[int] = None

    def __post_init__(self):
        if self.talla_ids is None:
            self.talla_ids = []
