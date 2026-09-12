from typing import List, Dict, Optional
from kool_tpv.base_datos.db_wrapper import Database
from .base_source import BaseSource
from .anilist_source import AniListSource
from .jikan_source import JikanSource
from .mangadex_source import MangaDexSource
from .google_books_source import GoogleBooksSource

class SourceManager:
    """Gestiona el registro y descubrimiento de fuentes de datos."""

    def __init__(self, db: Optional[Database] = None):
        self.db = db
        self._sources: Dict[str, BaseSource] = {}
        self._register_defaults()

    def _register_defaults(self):
        """Registra las fuentes disponibles por defecto."""
        self.register_source(AniListSource())
        self.register_source(JikanSource())
        self.register_source(MangaDexSource())
        self.register_source(GoogleBooksSource(self.db))
        # Aquí es donde añadirías MyAnimeListSource(), GoogleBooksSource(), etc.

    def register_source(self, source: BaseSource):
        self._sources[source.id] = source

    def get_all_sources(self) -> List[BaseSource]:
        return list(self._sources.values())

    def get_source(self, source_id: str) -> BaseSource:
        return self._sources.get(source_id)
