from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple

class BaseSource(ABC):
    """Clase base abstracta para todas las fuentes de datos externas."""

    @property
    @abstractmethod
    def id(self) -> str:
        """Identificador único de la fuente (usado en la BD, ej: 'anilist')."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Nombre amigable para la UI."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Descripción corta de qué datos ofrece."""
        pass

    @abstractmethod
    def test_connection(self) -> Tuple[bool, str]:
        """Prueba la conexión con el servicio.
        
        Returns:
            Tuple[bool, str]: (Éxito, Mensaje de respuesta o error)
        """
        pass

    @abstractmethod
    def search(self, query: str) -> List[Dict[str, Any]]:
        """Busca información general."""
        pass

    @abstractmethod
    def get_details(self, identifier: Any) -> Optional[Dict[str, Any]]:
        """Obtiene el detalle completo de un ítem."""
        pass
