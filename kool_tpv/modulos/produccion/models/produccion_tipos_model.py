from dataclasses import dataclass
from typing import Optional


@dataclass
class ProduccionTipo:
    id: Optional[int] = None
    nombre: str = ""
    descripcion: Optional[str] = None
    color: Optional[str] = None
    icono: Optional[str] = None
    coste_base: float = 0.0
    requiere_talla: int = 0
    requiere_color: int = 0
    requiere_genero: int = 0
    activo: int = 1
    orden: int = 0
