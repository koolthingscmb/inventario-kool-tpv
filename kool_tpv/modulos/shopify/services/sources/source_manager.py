from typing import List, Dict
from .base_source import BaseSource
from .anilist_source import AniListSource

class SourceManager:
    """Gestiona el registro y descubrimiento de fuentes de datos."""

    def __init__(self):
        self._sources: Dict[str, BaseSource] = {}
        self._register_defaults()

    def _register_defaults(self):
        """Registra las fuentes disponibles por defecto."""
        self.register_source(AniListSource())
        # Aquí es donde añadirías MyAnimeListSource(), GoogleBooksSource(), etc.

    def register_source(self, source: BaseSource):
        self._sources[source.id] = source

    def get_all_sources(self) -> List[BaseSource]:
        return list(self._sources.values())

    def get_source(self, source_id: str) -> BaseSource:
        return self._sources.get(source_id)
