from dataclasses import dataclass
from typing import Optional

@dataclass
class ProduccionLinea:
    id: Optional[int] = None
    orden_id: int = 0
    diseno_codigo: str = ""
    tipo_id: int = 0
    talla: Optional[str] = None
    color_id: Optional[int] = None
    cantidad: int = 1
    produccion_mixta: int = 0  # Legacy: 0=no, 1=si
    extra_id: Optional[int] = None
    extra_coste: int = 0       # en céntimos (snapshot)
    usuario_produccion_id: Optional[int] = None
    coste_unitario: int = 0    # en céntimos
    coste_total: int = 0       # en céntimos
    variante_id: Optional[int] = None
    metodo_id: Optional[int] = None
    origen: str = "KOOL"
