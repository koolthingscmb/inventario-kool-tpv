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
    coleccion: str
    nombre: str
    sufijo: Optional[str] = None
    tipos: List[int] = field(default_factory=list)  # IDs de produccion_tipos
    costes: List[DisenoCoste] = field(default_factory=list)  # costes dinámicos
    # Campos viejos mantenidos para compatibilidad durante la migración
    coste_camiseta: int = 0  # en céntimos
    coste_taza: int = 0      # en céntimos
    coste_gorra: int = 0     # en céntimos
    coste_calcetin: int = 0  # en céntimos
    coste_libreta: int = 0   # en céntimos
    coste_poster: int = 0    # en céntimos
    coste_cartera: int = 0   # en céntimos
    activo: int = 1
