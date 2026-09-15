"""MangaData: modelo normalizado común para datos técnicos de manga.

Cada fuente traduce su respuesta cruda a este modelo mediante `normalize()`.
Los consumidores (UI, servicios de IA) trabajan siempre con este objeto,
sin depender del formato interno de cada API.
"""
from dataclasses import dataclass, field
from typing import List


@dataclass
class MangaData:
    titulo_romaji: str = ''
    titulo_nativo: str = ''      # kanji/kana japonés
    autor: str = ''
    anio: str = ''
    demografia: str = ''
    generos: List[str] = field(default_factory=list)
    editorial: str = ''
    sinopsis: str = ''
    estado: str = ''

    def merge(self, other: 'MangaData') -> 'MangaData':
        """Rellena los campos vacíos de self con los valores de other."""
        for f in ('titulo_romaji', 'titulo_nativo', 'autor', 'anio',
                  'demografia', 'editorial', 'sinopsis', 'estado'):
            if not getattr(self, f) and getattr(other, f):
                setattr(self, f, getattr(other, f))
        if not self.generos and other.generos:
            self.generos = list(other.generos)
        return self
