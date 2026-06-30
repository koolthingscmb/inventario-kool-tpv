"""Servicio para la gestión de extras de producción.
"""
from typing import List, Optional
from kool_tpv.modulos.produccion.repositories.produccion_extras_repository import ProduccionExtrasRepository, ProduccionExtra

class ProduccionExtrasService:
    def __init__(self, db):
        self.repository = ProduccionExtrasRepository(db)

    def get_todos(self, solo_activos: bool = False) -> List[ProduccionExtra]:
        return self.repository.get_todos(solo_activos)

    def get_por_id(self, extra_id: int) -> Optional[ProduccionExtra]:
        return self.repository.get_por_id(extra_id)

    def guardar_extra(self, extra: ProduccionExtra) -> bool:
        """Crea o actualiza un extra."""
        if not extra.nombre:
            return False
            
        if extra.id:
            return self.repository.actualizar(extra)
        else:
            nuevo_id = self.repository.crear(extra)
            if nuevo_id:
                extra.id = nuevo_id
                return True
            return False

    def eliminar_extra(self, extra_id: int) -> bool:
        return self.repository.eliminar(extra_id)
