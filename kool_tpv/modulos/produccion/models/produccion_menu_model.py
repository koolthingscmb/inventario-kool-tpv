"""Modelo para los elementos del menú de producción."""
from dataclasses import dataclass
from typing import Optional

@dataclass
class ProduccionMenuItem:
    id: int
    nombre: str
    sistema_produccion: Optional[str] = None
    tipo_id: Optional[int] = None
    orden: int = 0
    activo: int = 1
