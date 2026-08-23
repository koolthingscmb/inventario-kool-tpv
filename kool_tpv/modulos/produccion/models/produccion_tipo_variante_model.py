from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class ProduccionTipoVariante:
    id: Optional[int] = None
    tipo_id: int = 0
    nombre: str = ""
    coste_base: int = 0
    precio_recomendado: int = 0
    activo: int = 1
    requiere_talla: int = 0
    requiere_color: int = 0
    grupo_talla_id: Optional[int] = None
    shopify_variant_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
