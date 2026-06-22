"""Servicio para el menú de producción."""
from typing import List, Optional
from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.produccion.models.produccion_menu_model import ProduccionMenuItem
from kool_tpv.modulos.produccion.repositories.produccion_menu_repository import ProduccionMenuRepository
from kool_tpv.modulos.produccion.repositories.produccion_menu_tipos_repository import ProduccionMenuTiposRepository
from kool_tpv.modulos.produccion.repositories.produccion_tipos_repository import ProduccionTiposRepository
from kool_tpv.modulos.produccion.models.produccion_tipos_model import ProduccionTipo

class ProduccionMenuService:
    def __init__(self, db: Database):
        self.db = db
        self.repository = ProduccionMenuRepository(db)
        self.tipos_repo = ProduccionTiposRepository(db)
        self.menu_tipos_repo = ProduccionMenuTiposRepository(db)

    def obtener_menu_activos(self) -> List[ProduccionMenuItem]:
        """Obtener los elementos del menú activos."""
        return self.repository.get_activos()

    def obtener_tipo_asociado(self, item: ProduccionMenuItem) -> Optional[ProduccionTipo]:
        """Obtener el objeto ProduccionTipo asociado a un elemento del menú (compat 1:1)."""
        if item.tipo_id:
            return self.tipos_repo.get_por_id(item.tipo_id)
        return None

    def obtener_tipos_por_menu(self, menu_id: int) -> List[ProduccionTipo]:
        """Obtener los tipos asociados a un menú (relación N:M)."""
        return self.menu_tipos_repo.get_tipos_por_menu(menu_id)
