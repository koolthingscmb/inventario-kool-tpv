"""Acceso a datos para la tabla `produccion_variantes_productos`.

Gestiona la relación entre variantes de producción y productos del TPV.
"""
import logging
from typing import List, Optional
from datetime import datetime

from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.produccion.models.variante_producto_link import VarianteProductoLink

logger = logging.getLogger(__name__)

class VarianteProductoRepository:
    """DAO para la tabla `produccion_variantes_productos`."""

    def __init__(self, db: Database):
        self.db = db

    def _row_to_link(self, row) -> VarianteProductoLink:
        """Convierte una fila de la BD a un objeto VarianteProductoLink."""
        # sqlite3.Row soporta .keys() y indexación por nombre, pero NO .get()
        def _get(key, default=None):
            try:
                return row[key]
            except (KeyError, IndexError):
                return default

        try:
            # Intentar acceso por nombre si el cursor es de tipo Row, o índices si no.
            if hasattr(row, 'keys'):
                return VarianteProductoLink(
                    id=row['id'],
                    variante_id=row['variante_id'],
                    producto_id=row['producto_id'],
                    extra_id=_get('extra_id'),
                    coleccion_id=_get('coleccion_id'),
                    ratio=_get('ratio', 1),
                    activo=_get('activo', 1),
                    created_at=datetime.fromisoformat(_get('created_at')) if _get('created_at') else None,
                    updated_at=datetime.fromisoformat(_get('updated_at')) if _get('updated_at') else None,
                    variante_nombre=_get('variante_nombre'),
                    producto_nombre=_get('producto_nombre'),
                    extra_nombre=_get('extra_nombre'),
                    coleccion_nombre=_get('coleccion_nombre')
                )
            
            # Fallback a índices (orden estándar de SELECT *)
            # id, v_id, p_id, extra_id, coleccion_id, ratio, activo, created_at, updated_at
            id_, v_id, p_id, extra_id, coleccion_id, ratio, activo, created_at, updated_at = row[:9]
            v_nombre = row[9] if len(row) > 9 else None
            p_nombre = row[10] if len(row) > 10 else None
            e_nombre = row[11] if len(row) > 11 else None
            c_nombre = row[12] if len(row) > 12 else None
            
            return VarianteProductoLink(
                id=id_,
                variante_id=v_id,
                producto_id=p_id,
                extra_id=extra_id,
                coleccion_id=coleccion_id,
                ratio=ratio,
                activo=activo,
                created_at=datetime.fromisoformat(created_at) if created_at else None,
                updated_at=datetime.fromisoformat(updated_at) if updated_at else None,
                variante_nombre=v_nombre,
                producto_nombre=p_nombre,
                extra_nombre=e_nombre,
                coleccion_nombre=c_nombre
            )
        except Exception:
            logger.exception("Error mapeando row a VarianteProductoLink")
            raise

    def get_todos(self) -> List[VarianteProductoLink]:
        """Obtener todos los mapeos con nombres de variante, producto, extra y colección."""
        query = """
            SELECT l.id, l.variante_id, l.producto_id, l.extra_id, l.coleccion_id, l.ratio, l.activo, l.created_at, l.updated_at,
                   v.nombre as variante_nombre, p.nombre as producto_nombre,
                   e.nombre as extra_nombre, c.nombre as coleccion_nombre
            FROM produccion_variantes_productos l
            JOIN tipos_variantes v ON l.variante_id = v.id
            JOIN productos p ON l.producto_id = p.id
            LEFT JOIN produccion_extras e ON l.extra_id = e.id
            LEFT JOIN produccion_colecciones c ON l.coleccion_id = c.id
            ORDER BY v.nombre ASC
        """
        rows = self.db.fetch_all(query)
        return [self._row_to_link(row) for row in rows]

    def get_por_combinacion(self, variante_id: int, extra_id: Optional[int] = None, 
                           coleccion_id: Optional[int] = None) -> Optional[VarianteProductoLink]:
        """Obtener el mapeo para una combinación de variante, extra y colección.
        
        Sigue un orden de prioridad:
        1. Combinación exacta (variante + extra + colección)
        2. Variante + Extra (colección global)
        3. Variante + Colección (extra global)
        4. Variante global (extra y colección NULL)
        """
        query = """
            SELECT l.id, l.variante_id, l.producto_id, l.extra_id, l.coleccion_id, l.ratio, l.activo, l.created_at, l.updated_at,
                   v.nombre as variante_nombre, p.nombre as producto_nombre,
                   e.nombre as extra_nombre, c.nombre as coleccion_nombre
            FROM produccion_variantes_productos l
            JOIN tipos_variantes v ON l.variante_id = v.id
            JOIN productos p ON l.producto_id = p.id
            LEFT JOIN produccion_extras e ON l.extra_id = e.id
            LEFT JOIN produccion_colecciones c ON l.coleccion_id = c.id
            WHERE l.variante_id = ? 
              AND (l.extra_id IS ? OR l.extra_id IS NULL)
              AND (l.coleccion_id IS ? OR l.coleccion_id IS NULL)
              AND l.activo = 1
            ORDER BY 
                (l.extra_id IS ?) DESC, 
                (l.coleccion_id IS ?) DESC,
                l.id DESC
            LIMIT 1
        """
        # Repetimos extra_id y coleccion_id para los parámetros de ordenación
        params = (variante_id, extra_id, coleccion_id, extra_id, coleccion_id)
        rows = self.db.fetch_all(query, params)
        if not rows:
            return None
        return self._row_to_link(rows[0])

    def get_filtrados(self, tipo_id: Optional[int] = None, variante_id: Optional[int] = None) -> List[VarianteProductoLink]:
        """Obtener vinculaciones filtradas por tipo o variante."""
        query = """
            SELECT l.id, l.variante_id, l.producto_id, l.extra_id, l.coleccion_id, l.ratio, l.activo, l.created_at, l.updated_at,
                   v.nombre as variante_nombre, p.nombre as producto_nombre,
                   e.nombre as extra_nombre, c.nombre as coleccion_nombre
            FROM produccion_variantes_productos l
            JOIN tipos_variantes v ON l.variante_id = v.id
            JOIN productos p ON l.producto_id = p.id
            LEFT JOIN produccion_extras e ON l.extra_id = e.id
            LEFT JOIN produccion_colecciones c ON l.coleccion_id = c.id
            WHERE 1=1
        """
        params = []
        if variante_id:
            query += " AND l.variante_id = ?"
            params.append(variante_id)
        elif tipo_id:
            query += " AND v.tipo_id = ?"
            params.append(tipo_id)
            
        query += " ORDER BY p.nombre ASC"
        rows = self.db.fetch_all(query, tuple(params))
        return [self._row_to_link(row) for row in rows]


    def existe_combinacion_exacta(self, variante_id: int, extra_id: Optional[int] = None,
                                  coleccion_id: Optional[int] = None) -> bool:
        """Comprobar si existe una vinculación con coincidencia exacta (sin fallback)."""
        query = """
            SELECT 1 FROM produccion_variantes_productos
            WHERE variante_id = ? AND extra_id IS ? AND coleccion_id IS ? AND activo = 1
            LIMIT 1
        """
        rows = self.db.fetch_all(query, (variante_id, extra_id, coleccion_id))
        return len(rows) > 0

    def crear(self, link: VarianteProductoLink) -> Optional[int]:
        """Crear un nuevo mapeo."""
        try:
            query = """
                INSERT INTO produccion_variantes_productos (variante_id, producto_id, extra_id, coleccion_id, ratio, activo)
                VALUES (?, ?, ?, ?, ?, ?)
            """
            self.db.execute_query(query, (link.variante_id, link.producto_id, link.extra_id, link.coleccion_id, link.ratio, link.activo))
            res = self.db.fetch_all("SELECT last_insert_rowid()")
            return res[0][0] if res else None
        except Exception:
            logger.exception("Error al crear mapeo variante-producto")
            return None

    def actualizar(self, link: VarianteProductoLink) -> bool:
        """Actualizar un mapeo existente."""
        if not link.id: return False
        try:
            query = """
                UPDATE produccion_variantes_productos
                SET variante_id = ?, producto_id = ?, extra_id = ?, coleccion_id = ?, ratio = ?, activo = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """
            self.db.execute_query(query, (link.variante_id, link.producto_id, link.extra_id, link.coleccion_id, link.ratio, link.activo, link.id))
            return True
        except Exception:
            logger.exception(f"Error al actualizar mapeo {link.id}")
            return False

    def eliminar(self, link_id: int) -> bool:
        """Eliminar un mapeo (físicamente de la BD)."""
        try:
            self.db.execute_query("DELETE FROM produccion_variantes_productos WHERE id = ?", (link_id,))
            return True
        except Exception:
            logger.exception(f"Error al eliminar mapeo {link_id}")
            return False
