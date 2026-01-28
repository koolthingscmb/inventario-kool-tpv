from typing import Optional, List, Dict, Any
import sqlite3
import logging

import database

logger = logging.getLogger(__name__)


class ConfigService:
    """Servicio para configuración global, categorías y promociones de fidelización."""

    def __init__(self):
        pass

    def _row_to_dict(self, row: sqlite3.Row) -> Optional[Dict[str, Any]]:
        if row is None:
            return None
        return {k: row[k] for k in row.keys()}

    # ---------- Configuración global (clave/valor) ----------
    def get_valor(self, clave: str, default: Optional[str] = None) -> Optional[str]:
        try:
            conn = database.connect()
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute('SELECT valor FROM configuracion WHERE clave=? LIMIT 1', (clave,))
            row = cur.fetchone()
            try:
                cur.close()
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass
            if row:
                return row['valor']
            return default
        except Exception as e:
            logger.exception('Error leyendo configuración %s: %s', clave, e)
            return default

    def set_valor(self, clave: str, valor: str) -> bool:
        try:
            conn = database.connect()
            cur = conn.cursor()
            try:
                cur.execute('INSERT OR REPLACE INTO configuracion (clave, valor) VALUES (?, ?)', (clave, valor))
                conn.commit()
                return True
            finally:
                try:
                    cur.close()
                except Exception:
                    pass
                try:
                    conn.close()
                except Exception:
                    pass
        except Exception as e:
            logger.exception('Error guardando configuración %s=%s: %s', clave, valor, e)
            return False

    @staticmethod
    def validar_pass_config(password_intento: str) -> bool:
        """Valida el valor de 'config_pass_global' contra `password_intento`.

        Devuelve True si coinciden, False en caso contrario o en error.
        """
        try:
            conn = database.connect()
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            try:
                cur.execute('SELECT valor FROM configuracion WHERE clave=? LIMIT 1', ('config_pass_global',))
                row = cur.fetchone()
            finally:
                try:
                    cur.close()
                except Exception:
                    pass
                try:
                    conn.close()
                except Exception:
                    pass

            if row and row['valor'] is not None:
                return str(row['valor']) == str(password_intento)
            return False
        except Exception:
            logger.exception('Error validando password de configuración')
            return False

    @staticmethod
    def cambiar_pass_config(nueva_password: str) -> bool:
        """Actualiza la clave 'config_pass_global' con `nueva_password`.

        Devuelve True si la operación se completó correctamente.
        """
        try:
            conn = database.connect()
            cur = conn.cursor()
            try:
                cur.execute('INSERT OR REPLACE INTO configuracion (clave, valor) VALUES (?, ?)', ('config_pass_global', nueva_password))
                conn.commit()
                return True
            finally:
                try:
                    cur.close()
                except Exception:
                    pass
                try:
                    conn.close()
                except Exception:
                    pass
        except Exception:
            logger.exception('Error cambiando password de configuración')
            return False

    # ---------- Categorías (fide_porcentaje) ----------
    def listar_categorias_fide(self) -> List[Dict[str, Any]]:
        try:
            conn = database.connect()
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute('SELECT id, nombre, fide_porcentaje FROM categorias ORDER BY nombre COLLATE NOCASE')
            rows = cur.fetchall()
            result = [self._row_to_dict(r) for r in rows]
            try:
                cur.close()
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass
            return result
        except Exception as e:
            logger.exception('Error listando categorías para fidelización: %s', e)
            return []

    def actualizar_porcentaje_categoria(self, id_cat: int, porcentaje: Optional[float]) -> bool:
        try:
            conn = database.connect()
            cur = conn.cursor()
            try:
                cur.execute('UPDATE categorias SET fide_porcentaje=? WHERE id=?', (porcentaje, id_cat))
                conn.commit()
                return cur.rowcount > 0
            finally:
                try:
                    cur.close()
                except Exception:
                    pass
                try:
                    conn.close()
                except Exception:
                    pass
        except Exception as e:
            logger.exception('Error actualizando porcentaje de categoría id=%s: %s', id_cat, e)
            return False

    # ---------- Tipos (fide_porcentaje) ----------
    def listar_tipos_fide(self) -> List[Dict[str, Any]]:
        try:
            conn = database.connect()
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute('SELECT id, nombre, fide_porcentaje FROM tipos ORDER BY nombre COLLATE NOCASE')
            rows = cur.fetchall()
            result = [self._row_to_dict(r) for r in rows]
            try:
                cur.close()
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass
            return result
        except Exception as e:
            logger.exception('Error listando tipos para fidelización: %s', e)
            return []

    def actualizar_porcentaje_tipo(self, id_tipo: int, porcentaje: Optional[float]) -> bool:
        try:
            conn = database.connect()
            cur = conn.cursor()
            try:
                cur.execute('UPDATE tipos SET fide_porcentaje=? WHERE id=?', (porcentaje, id_tipo))
                conn.commit()
                return cur.rowcount > 0
            finally:
                try:
                    cur.close()
                except Exception:
                    pass
                try:
                    conn.close()
                except Exception:
                    pass
        except Exception as e:
            logger.exception('Error actualizando porcentaje de tipo id=%s: %s', id_tipo, e)
            return False

    # ---------- Obtener todo (config + listas) ----------
    def obtener_todo_fide(self) -> Dict[str, Any]:
        """Devuelve un dict con la configuración global y listas necesarias para cargar la UI.

        Estructura devuelta:
        {
            'config': {clave: valor, ...},
            'categorias': [ {id,nombre,fide_porcentaje}, ... ],
            'tipos': [ {id,nombre,fide_porcentaje}, ... ],
            'promociones': [ {id,nombre,fecha_inicio,fecha_fin,multiplicador,activa}, ... ]
        }
        """
        try:
            out: Dict[str, Any] = {}
            # config
            try:
                conn = database.connect()
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                cur.execute('SELECT clave, valor FROM configuracion')
                rows = cur.fetchall()
                cfg = {r['clave']: r['valor'] for r in rows} if rows else {}
            except Exception:
                cfg = {}
            finally:
                try:
                    cur.close()
                except Exception:
                    pass
                try:
                    conn.close()
                except Exception:
                    pass

            out['config'] = cfg
            out['categorias'] = self.listar_categorias_fide()
            out['tipos'] = self.listar_tipos_fide()
            out['promociones'] = self.listar_promociones()
            return out
        except Exception as e:
            logger.exception('Error obteniendo todo para fidelización: %s', e)
            return {'config': {}, 'categorias': [], 'tipos': [], 'promociones': []}

    # ---------- Promociones temporales ----------
    def listar_promociones(self) -> List[Dict[str, Any]]:
        try:
            conn = database.connect()
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute('SELECT id, nombre, fecha_inicio, fecha_fin, multiplicador, activa FROM fide_promociones ORDER BY fecha_inicio DESC')
            rows = cur.fetchall()
            result = [self._row_to_dict(r) for r in rows]
            try:
                cur.close()
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass
            return result
        except Exception as e:
            logger.exception('Error listando promociones de fidelización: %s', e)
            return []

    def guardar_promocion(self, datos: Dict[str, Any]) -> Optional[int]:
        """Crea o actualiza una promoción.

        Si `datos` contiene `id`, intenta actualizar; si no existe, crea nueva.
        Devuelve el id de la promoción creada/actualizada o None en fallo.
        """
        try:
            conn = database.connect()
            cur = conn.cursor()

            pid = datos.get('id')
            nombre = datos.get('nombre')
            fecha_inicio = datos.get('fecha_inicio')
            fecha_fin = datos.get('fecha_fin')
            multiplicador = datos.get('multiplicador', 1.0)
            activa = 1 if datos.get('activa', True) else 0

            if pid:
                # update
                cur.execute('''
                    UPDATE fide_promociones
                    SET nombre=?, fecha_inicio=?, fecha_fin=?, multiplicador=?, activa=?
                    WHERE id=?
                ''', (nombre, fecha_inicio, fecha_fin, multiplicador, activa, pid))
                conn.commit()
                try:
                    cur.close()
                except Exception:
                    pass
                try:
                    conn.close()
                except Exception:
                    pass
                return pid
            else:
                cur.execute('''
                    INSERT INTO fide_promociones (nombre, fecha_inicio, fecha_fin, multiplicador, activa)
                    VALUES (?, ?, ?, ?, ?)
                ''', (nombre, fecha_inicio, fecha_fin, multiplicador, activa))
                new_id = cur.lastrowid
                conn.commit()
                try:
                    cur.close()
                except Exception:
                    pass
                try:
                    conn.close()
                except Exception:
                    pass
                return new_id
        except Exception as e:
            logger.exception('Error guardando promoción: %s', e)
            return None

    def eliminar_promocion(self, promo_id: int) -> bool:
        try:
            conn = database.connect()
            cur = conn.cursor()
            try:
                cur.execute('DELETE FROM fide_promociones WHERE id=?', (promo_id,))
                conn.commit()
                return cur.rowcount > 0
            finally:
                try:
                    cur.close()
                except Exception:
                    pass
                try:
                    conn.close()
                except Exception:
                    pass
        except Exception as e:
            logger.exception('Error eliminando promoción id=%s: %s', promo_id, e)
            return False
