"""Acceso a datos para la tabla `tipos_variantes`.

Contiene la clase `ProduccionTiposVariantesRepository` que expone métodos para consultar
y gestionar variantes de tipos de producto desde la base de datos.
"""
import logging
from typing import List, Optional
from datetime import datetime

from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.produccion.models.produccion_tipo_variante_model import ProduccionTipoVariante


class ProduccionTiposVariantesRepository:
    """Data access object (DAO) para `tipos_variantes`.

    Args:
        db: instancia de `Database` ya conectada.
    """

    def __init__(self, db: Database):
        self.db = db

    def _row_to_variante(self, row) -> ProduccionTipoVariante:
        """Mapear una fila de BD a objeto ProduccionTipoVariante."""
        (id_, tipo_id, nombre, coste_base, precio_recomendado, 
         activo, shopify_variant_id, created_at, updated_at,
         requiere_talla, requiere_color, grupo_talla_id) = row
        
        return ProduccionTipoVariante(
            id=id_,
            tipo_id=tipo_id,
            nombre=nombre,
            coste_base=coste_base or 0,
            precio_recomendado=precio_recomendado or 0,
            activo=activo if activo is not None else 1,
            requiere_talla=requiere_talla or 0,
            requiere_color=requiere_color or 0,
            grupo_talla_id=grupo_talla_id,
            shopify_variant_id=shopify_variant_id,
            created_at=datetime.fromisoformat(created_at) if created_at else None,
            updated_at=datetime.fromisoformat(updated_at) if updated_at else None
        )

    _QUERY_SELECT = """
        SELECT id, tipo_id, nombre, coste_base, precio_recomendado, 
               activo, shopify_variant_id, created_at, updated_at,
               requiere_talla, requiere_color, grupo_talla_id
        FROM tipos_variantes
    """

    def get_todos(self) -> List[ProduccionTipoVariante]:
        """Obtener todas las variantes."""
        query = self._QUERY_SELECT + " ORDER BY tipo_id, nombre"
        rows = self.db.fetch_all(query)
        return [self._row_to_variante(row) for row in rows]

    def get_por_tipo(self, tipo_id: int, solo_activos: bool = True) -> List[ProduccionTipoVariante]:
        """Obtener variantes de un tipo."""
        query = self._QUERY_SELECT + " WHERE tipo_id = ?"
        if solo_activos:
            query += " AND activo = 1"
        query += " ORDER BY nombre"

        rows = self.db.fetch_all(query, (tipo_id,))
        return [self._row_to_variante(row) for row in rows]

    def get_por_id(self, variante_id: int) -> Optional[ProduccionTipoVariante]:
        """Obtener una variante por su ID."""
        query = self._QUERY_SELECT + " WHERE id = ?"
        rows = self.db.fetch_all(query, (variante_id,))

        if not rows:
            return None
        return self._row_to_variante(rows[0])

    def crear(self, variante: ProduccionTipoVariante) -> Optional[int]:
        """Crear una nueva variante."""
        try:
            query = """
                INSERT INTO tipos_variantes
                (tipo_id, nombre, coste_base, precio_recomendado, activo, 
                 shopify_variant_id, requiere_talla, requiere_color, grupo_talla_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            self.db.execute_query(query, (
                variante.tipo_id, variante.nombre, variante.coste_base, 
                variante.precio_recomendado, variante.activo, 
                variante.shopify_variant_id, variante.requiere_talla, 
                variante.requiere_color, variante.grupo_talla_id
            ))
            result = self.db.fetch_all("SELECT last_insert_rowid()")
            if result:
                return result[0][0]
            return None
        except Exception:
            logging.exception("Error creando variante de tipo")
            return None

    def actualizar(self, variante: ProduccionTipoVariante) -> bool:
        """Actualizar una variante existente."""
        if variante.id is None:
            return False

        try:
            logging.info(f"REPO: Actualizando variante {variante.id} - Grupo ID: {variante.grupo_talla_id}")
            
            query = """
                UPDATE tipos_variantes
                SET tipo_id = ?, nombre = ?, coste_base = ?, 
                    precio_recomendado = ?, activo = ?, shopify_variant_id = ?,
                    requiere_talla = ?, requiere_color = ?, grupo_talla_id = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """
            self.db.execute_query(query, (
                variante.tipo_id, variante.nombre, variante.coste_base, 
                variante.precio_recomendado, variante.activo, 
                variante.shopify_variant_id, variante.requiere_talla, 
                variante.requiere_color, variante.grupo_talla_id, variante.id
            ))
            return True
        except Exception:
            logging.exception(f"Error actualizando variante {variante.id}")
            return False

    def get_variantes_con_coste(self, search_term: str = "") -> List[dict]:
        """Obtener variantes activas con su nombre de tipo y coste base para la UI."""
        query = """
            SELECT 
                t.nombre as tipo_nombre,
                v.nombre as variante_nombre,
                v.coste_base
            FROM tipos_variantes v
            JOIN tipos t ON v.tipo_id = t.id
            WHERE v.activo = 1
        """
        params = []
        if search_term:
            query += " AND (t.nombre LIKE ? OR v.nombre LIKE ?)"
            term = f"%{search_term}%"
            params.extend([term, term])
            
        query += " ORDER BY t.nombre, v.nombre"
        
        rows = self.db.fetch_all(query, tuple(params))
        
        resultados = []
        from kool_tpv.base_datos.money_adapter import read_from_db
        for r in rows:
            resultados.append({
                "tipo": r[0],
                "variante": r[1],
                "coste": float(read_from_db(r[2] or 0))
            })
        return resultados
