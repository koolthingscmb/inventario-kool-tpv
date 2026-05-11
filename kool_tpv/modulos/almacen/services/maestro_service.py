"""MaestroService: servicio CRUD genérico para el módulo ALMACÉN.

Hace uso de `ProductoService` existente para operaciones relacionadas con productos
(sin duplicar lógica). Provee métodos genéricos para entidades maestras como
categorías, tipos y precios delegando a los servicios existentes cuando aplique.
"""
from typing import Any, Dict, List, Optional
import logging

# Reutilizar producto_service existente
from kool_tpv.base_datos.producto_service import ProductoService


class MaestroService:
    """Servicio maestro que agrega una capa simple sobre ProductoService.

    - No duplica lógica de `ProductoService`.
    - Expone métodos CRUD simples para usar desde la UI de almacen.
    """

    def __init__(self, db: Any):
        self.db = db
        try:
            self.producto_svc = ProductoService(db)
        except Exception:
            logging.exception('Error instanciando ProductoService en MaestroService')
            self.producto_svc = None

    # Productos (delegado)
    def listar_productos(self, termino: str = '') -> List[Dict[str, Any]]:
        try:
            if self.producto_svc is None:
                return []
            return self.producto_svc.listar_productos(termino)
        except Exception:
            logging.exception('Error en listar_productos MaestroService')
            return []

    def obtener_producto_por_id(self, pid: int) -> Optional[Dict[str, Any]]:
        try:
            if self.producto_svc is None:
                return None
            return self.producto_svc.obtener_producto_por_id(pid)
        except Exception:
            logging.exception('Error en obtener_producto_por_id MaestroService')
            return None

    def listar_precios(self) -> List[Dict[str, Any]]:
        try:
            sql = "SELECT id, producto_id, pvp, activo, created_at FROM precios ORDER BY created_at DESC"
            rows = self.producto_svc.db.fetch_all(sql, ()) if getattr(self, 'producto_svc', None) is not None else []
            items = []
            for r in rows or []:
                try:
                    items.append({
                        'id': r[0],
                        'producto_id': r[1],
                        'pvp': r[2],
                        'activo': bool(r[3]),
                        'created_at': r[4],
                    })
                except Exception:
                    logging.exception('Error normalizando fila precio')
            return items
        except Exception:
            logging.exception('Error listando precios')
            return []
    # Generic helpers requested by the feature: get_all/save/update
    _ALLOWED_TABLES = {"categorias", "tipos", "proveedores", "precios", "productos"}

    def _validate_table(self, tabla: str) -> bool:
        try:
            return str(tabla) in self._ALLOWED_TABLES
        except Exception:
            return False

    def get_all(self, tabla: str) -> List[Dict[str, Any]]:
        """Return all rows from `tabla` ordered by `nombre` when possible.

        Only tables in `_ALLOWED_TABLES` are accepted to avoid SQL injection.
        """
        try:
            if not self._validate_table(tabla):
                logging.warning('get_all: tabla no permitida %s', tabla)
                return []
            # Order by nombre when column exists; safe because tabla was validated
            try:
                # Check if column 'nombre' exists
                info = self.producto_svc.db.fetch_all(f"PRAGMA table_info({tabla})", ())
                cols = [r[1] for r in (info or [])]
                order_clause = 'ORDER BY nombre' if 'nombre' in cols else ''
            except Exception:
                order_clause = ''
            sql = f"SELECT * FROM {tabla} {order_clause}"
            rows = self.producto_svc.db.fetch_all(sql, ()) if getattr(self, 'producto_svc', None) is not None else []
            items: List[Dict[str, Any]] = []
            for r in rows or []:
                try:
                    # map columns via PRAGMA
                    if 'cols' in locals() and cols:
                        item = {cols[i]: r[i] for i in range(min(len(cols), len(r)))}
                    else:
                        # fallback: index-based
                        item = {'row': r}
                    items.append(item)
                except Exception:
                    logging.exception('Error normalizando fila get_all %s', tabla)
            return items
        except Exception:
            logging.exception('Error en get_all MaestroService')
            return []

    def save(self, tabla: str, datos: Dict[str, Any]) -> Optional[int]:
        """Insert a new row into `tabla` using keys from `datos`.

        Returns the new row id or None on error.
        """
        try:
            if not self._validate_table(tabla):
                logging.warning('save: tabla no permitida %s', tabla)
                return None
            cols = []
            vals = []
            for k, v in (datos or {}).items():
                cols.append(k)
                vals.append(v)
            # add timestamps if available and not provided
            if 'created_at' not in cols and 'created_at' in (c for c in cols) is False:
                # do not force created_at; let DB defaults handle it or caller provide
                pass
            placeholders = ','.join(['?'] * len(cols)) if cols else ''
            cols_clause = ','.join(cols)
            sql = f"INSERT INTO {tabla} ({cols_clause}) VALUES ({placeholders})" if cols else None
            if not sql:
                logging.warning('save: no hay columnas para insertar en %s', tabla)
                return None
            cur = self.producto_svc.db.execute(sql, tuple(vals)) if getattr(self, 'producto_svc', None) is not None else None
            return cur.lastrowid if cur is not None else None
        except Exception:
            logging.exception('Error en save MaestroService')
            return None

    def update(self, tabla: str, id_val: int, datos: Dict[str, Any]) -> bool:
        """Update row `id_val` in `tabla` with values from `datos`.

        Returns True on success.
        """
        try:
            if not self._validate_table(tabla):
                logging.warning('update: tabla no permitida %s', tabla)
                return False
            if not datos:
                return False
            sets = []
            params = []
            for k, v in datos.items():
                sets.append(f"{k} = ?")
                params.append(v)
            params.append(int(id_val))
            set_clause = ', '.join(sets)
            sql = f"UPDATE {tabla} SET {set_clause} WHERE id = ?"
            if getattr(self, 'producto_svc', None) is not None:
                self.producto_svc.db.execute(sql, tuple(params))
                return True
            return False
        except Exception:
            logging.exception('Error en update MaestroService')
            return False
