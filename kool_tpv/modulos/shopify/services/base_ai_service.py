from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple

class BaseAIService(ABC):
    """Clase base abstracta para todos los servicios de Inteligencia Artificial."""

    @abstractmethod
    def test_connection(self) -> Tuple[bool, str]:
        """Prueba la conexión con el servicio de IA.
        
        Returns:
            Tuple[bool, str]: (Éxito, Mensaje de respuesta o error)
        """
        pass

    @abstractmethod
    def generate_seo(self, source_data: Dict[str, Any], product_name: str, prompt_template: str) -> Optional[Dict[str, str]]:
        """Genera campos SEO optimizados para Shopify a partir de datos de una fuente externa.
        
        Args:
            source_data: Datos crudos de la fuente (ej: AniList) con title, description, genres, etc.
            product_name: Nombre del producto en el TPV.
            prompt_template: Plantilla del prompt con marcadores {product_name} y {source_data}.
            
        Returns:
            Dict con claves: seo_title, seo_short, seo_description, description, tags, tipo_shop
            o None si falla la generación.
        """
        pass
