from dataclasses import dataclass
from typing import Optional

@dataclass
class ProduccionColor:
    id: Optional[int] = None
    nombre: str = ""
    codigo_hex: Optional[str] = None
