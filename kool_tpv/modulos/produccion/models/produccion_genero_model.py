from dataclasses import dataclass
from typing import Optional


@dataclass
class ProduccionGenero:
    id: Optional[int] = None
    nombre: str = ""
    orden: int = 0
    activo: int = 1
