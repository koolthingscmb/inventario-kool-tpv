from dataclasses import dataclass, field
from typing import Optional

@dataclass
class ProduccionMetodo:
    id: Optional[int]
    nombre: str
    descripcion: Optional[str] = None
    icono: Optional[str] = None
    activo: int = 1
    orden: int = 0
