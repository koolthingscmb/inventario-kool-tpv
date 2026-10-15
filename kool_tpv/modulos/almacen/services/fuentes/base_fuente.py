"""Contrato común de las fuentes de datos de producto (manga/cómics/juegos).

Cada fuente devuelve SOLO información del producto (sinopsis, autor, editorial,
título original, géneros, portada...). Nunca precios, costes ni PVP: esos datos
entran al TPV por otro lado.

Todos los métodos son de solo lectura sobre el portal: búsquedas y fichas.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

# Campos normalizados que intenta devolver cada fuente (los que no sepan, vacíos)
CAMPOS_PRODUCTO = (
    "titulo", "titulo_original", "autor", "editorial", "isbn", "ean",
    "coleccion", "generos", "sinopsis", "imagen_url", "url_ficha",
)


class BaseFuente(ABC):
    """Fuente de datos de producto (portal de distribuidor o web pública)."""

    @property
    @abstractmethod
    def id(self) -> str:
        """Identificador del tipo de fuente (ej: 'zonalibros', 'planeta')."""

    @abstractmethod
    def buscar(self, consulta: str) -> List[Dict[str, Any]]:
        """Busca por EAN/ISBN (o texto) y devuelve resultados normalizados."""

    @abstractmethod
    def detalle(self, identificador: Any) -> Optional[Dict[str, Any]]:
        """Devuelve la ficha completa de un resultado de `buscar()`."""

    def probar(self) -> tuple:
        """Comprueba login + acceso. Devuelve (ok, mensaje)."""
        return (True, "Fuente sin prueba específica")
