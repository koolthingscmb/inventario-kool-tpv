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
    shopify_variant_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
