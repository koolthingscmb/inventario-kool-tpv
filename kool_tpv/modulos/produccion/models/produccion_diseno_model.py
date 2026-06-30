from dataclasses import dataclass, field
from typing import Optional, List

@dataclass
class DisenoCoste:
    diseno_codigo: str
    tipo_id: int
    variante_id: Optional[int] = None
    talla_id: Optional[int] = None
    coste: int = 0  # en céntimos

@dataclass
class ProduccionDiseno:
    codigo: str  # PK
    coleccion_id: int
    nombre: str
    sufijo_id: Optional[int] = None
    tipos: List[int] = field(default_factory=list)  # IDs de produccion_tipos
    activo: int = 1
