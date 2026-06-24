from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class ProduccionOrden:
    id: Optional[int] = None
    fecha_hora: datetime = datetime.now()
    usuario_id: Optional[int] = None
    notas: Optional[str] = None
    tiempo_estimado_minutos: Optional[int] = None
    estado: str = "PENDIENTE"
    origen: str = "KOOL"
