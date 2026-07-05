from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class VarianteProductoLink:
    """Modelo para el mapeo entre una variante de producción y un producto del TPV."""
    id: Optional[int] = None
    variante_id: int = 0
    producto_id: int = 0
    extra_id: Optional[int] = None
    coleccion_id: Optional[int] = None
    ratio: int = 1
    activo: int = 1
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # Campos auxiliares para UI (join con otras tablas)
    variante_nombre: Optional[str] = None
    producto_nombre: Optional[str] = None
    extra_nombre: Optional[str] = None
    coleccion_nombre: Optional[str] = None
