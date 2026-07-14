"""Lógica de negocio para el mapeo entre variantes de producción y productos del TPV.
"""
import logging
from typing import List, Optional, Set, Tuple

from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.produccion.models.variante_producto_link import VarianteProductoLink
from kool_tpv.modulos.produccion.repositories.variante_producto_repository import VarianteProductoRepository

logger = logging.getLogger(__name__)

class VarianteProductoService:
    """Servicio para gestionar la relación entre variantes y productos TPV."""

    def __init__(self, db: Database):
        self.db = db
        self.repo = VarianteProductoRepository(db)

    def get_todos(self) -> List[VarianteProductoLink]:
        """Obtener todos los mapeos configurados."""
        return self.repo.get_todos()

    def get_por_combinacion(self, variante_id: int, extra_id: Optional[int] = None, 
                           coleccion_id: Optional[int] = None) -> Optional[VarianteProductoLink]:
        """Obtener el mapeo activo para una combinación de producción."""
        return self.repo.get_por_combinacion(variante_id, extra_id, coleccion_id)

    def get_filtrados(self, tipo_id: Optional[int] = None, variante_id: Optional[int] = None) -> List[VarianteProductoLink]:
        """Obtener vinculaciones filtradas."""
        return self.repo.get_filtrados(tipo_id, variante_id)

    def get_por_producto_combinacion(self, producto_id: int, extra_id: Optional[int] = None, 
                                     coleccion_id: Optional[int] = None) -> List[VarianteProductoLink]:
        """Obtener todas las variantes vinculadas a un producto TPV para una combinación."""
        return self.repo.get_por_producto_combinacion(producto_id, extra_id, coleccion_id)

    def sincronizar_vinculaciones(self, producto_id: int, variante_ids: Set[int], 
                                  extra_id: Optional[int] = None, 
                                  coleccion_id: Optional[int] = None) -> Tuple[int, int]:
        """Sincroniza vinculaciones: elimina las que no están en el set e inserta las nuevas.
        
        Devuelve (insertadas, eliminadas).
        """
        try:
            # 1. Obtener vinculaciones actuales para esta combinación
            actuales = self.get_por_producto_combinacion(producto_id, extra_id, coleccion_id)
            actuales_ids = {a.variante_id for a in actuales}
            
            # 2. Calcular diferencias
            a_eliminar = actuales_ids - variante_ids
            a_insertar = variante_ids - actuales_ids
            
            if not a_eliminar and not a_insertar:
                return 0, 0
                
            with self.db.transaction() as cur:
                # 3. Eliminar las que ya no están
                if a_eliminar:
                    # En SQLite no podemos hacer DELETE WHERE v_id IN (...) AND extra IS ?
                    # de forma eficiente para el batch, así que lo hacemos uno a uno 
                    # o borramos todo y re-insertamos. Por robustez, borramos todo y re-insertamos
                    # lo que queremos mantener + lo nuevo.
                    self.repo.eliminar_por_producto_combinacion(producto_id, extra_id, coleccion_id, cur=cur)
                    # Al borrar todo, ahora todas las variante_ids son "a insertar"
                    final_insertar = variante_ids
                else:
                    final_insertar = a_insertar
                
                # 4. Insertar las necesarias
                if final_insertar:
                    links = [
                        VarianteProductoLink(
                            variante_id=vid,
                            producto_id=producto_id,
                            extra_id=extra_id,
                            coleccion_id=coleccion_id,
                            ratio=1,
                            activo=1
                        ) for vid in final_insertar
                    ]
                    self.repo.crear_batch(links, cur=cur)
            
            return len(final_insertar), len(a_eliminar)
            
        except Exception:
            logger.exception(f"Error sincronizando vinculaciones para producto {producto_id}")
            return 0, 0

    def guardar_mapeo(self, variante_id: int, producto_id: int, ratio: int = 1, 
                     extra_id: Optional[int] = None, coleccion_id: Optional[int] = None) -> bool:
        """Crea o actualiza un mapeo para una combinación exacta.
        
        Si ya existe una vinculación para esta combinación (variante+extra+colección), la actualiza.
        """
        try:
            existe = self.existe_combinacion_exacta(variante_id, extra_id, coleccion_id)
            
            if existe:
                existente = self.get_por_combinacion(variante_id, extra_id, coleccion_id)
            else:
                existente = None
            
            link = VarianteProductoLink(
                id=existente.id if existente else None,
                variante_id=variante_id,
                producto_id=producto_id,
                extra_id=extra_id,
                coleccion_id=coleccion_id,
                ratio=ratio,
                activo=1
            )

            if existente:
                return self.repo.actualizar(link)
            else:
                return self.repo.crear(link) is not None
        except Exception:
            logger.exception("Error en VarianteProductoService.guardar_mapeo")
            return False


    def eliminar_mapeo(self, link_id: int) -> bool:
        """Elimina un mapeo por su ID."""
        return self.repo.eliminar(link_id)

    def existe_combinacion_exacta(self, variante_id: int, extra_id: Optional[int] = None,
                                  coleccion_id: Optional[int] = None) -> bool:
        """Comprobar si existe una vinculación con coincidencia exacta (sin fallback)."""
        return self.repo.existe_combinacion_exacta(variante_id, extra_id, coleccion_id)

    def vincular_variante_con_producto(self, variante_id: int, producto_id: int, ratio: int = 1) -> bool:
        """Método de conveniencia para vinculación rápida."""
        return self.guardar_mapeo(variante_id, producto_id, ratio)
