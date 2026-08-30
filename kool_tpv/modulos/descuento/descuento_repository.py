from __future__ import annotations
import sqlite3
import os
from typing import Optional, List, Dict, Any
from kool_tpv.paths import DB_PATH


def _dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


# Delay-import Database for typing/instance checks
try:
    from kool_tpv.base_datos.db_wrapper import Database
except Exception:
    Database = None


class DescuentoRepository:
    """Repositorio para plantillas de descuento y persistencia de aplicación sobre tickets.

    Notas:
    - Usa la base de datos sqlite local por defecto (`kool_tpv/base_datos/kool_bd.db`).
    - Las operaciones sobre el ticket (snapshot) se realizan aquí como una simple UPDATE;
      la lógica de cálculo debe residir en `descuento_service`.
    """

    def __init__(self, db_path: Optional[str] = None):
        """Constructor: acepta una ruta a DB o una instancia `Database`.

        Args:
            db_path: ruta al fichero sqlite o instancia `Database`.
        """
        # Si le pasan un wrapper Database, úsalo directamente
        if Database is not None and isinstance(db_path, Database):
            self._db_wrapper = db_path
            self.db_path = None
        else:
            self._db_wrapper = None
            self.db_path = (db_path or DB_PATH)

    def _connect(self):
        """Context: devuelve una conexión usable en `with`.

        - Si se dispone de `self._db_wrapper`, asegura la conexión y devuelve
          `self._db_wrapper.connection`.
        - En caso contrario, abre una conexión nueva basada en `self.db_path`.
        """
        if self._db_wrapper is not None:
            # Asegurar conexión inicializada
            try:
                self._db_wrapper.connect()
            except Exception:
                pass
            # sqlite3.Connection soporta el protocolo context manager
            return self._db_wrapper.connection

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = _dict_factory
        return conn

    def listar_activos(self) -> List[Dict[str, Any]]:
        """Devuelve las plantillas de descuento activas (activo=1)."""
        # Si tenemos wrapper Database, usar su método fetch_all
        if self._db_wrapper is not None:
            rows = self._db_wrapper.fetch_all("SELECT * FROM descuentos WHERE activo=1 ORDER BY nombre")
            # convertir sqlite3.Row a dict
            return [dict(r) for r in (rows or [])]

        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM descuentos WHERE activo=1 ORDER BY nombre")
            return cur.fetchall()

    def get_by_id(self, descuento_id: int) -> Optional[Dict[str, Any]]:
        if self._db_wrapper is not None:
            row = self._db_wrapper.fetch_one("SELECT * FROM descuentos WHERE id = ?", (descuento_id,))
            return dict(row) if row is not None else None

        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM descuentos WHERE id = ?", (descuento_id,))
            row = cur.fetchone()
            return row

    def create_template(self, data: Dict[str, Any]) -> int:
        """Crea una plantilla de descuento y devuelve su id."""
        sql = ("""INSERT INTO descuentos (codigo, nombre, descripcion, tipo, valor_cents, valor_porcentaje, activo, vigencia_inicio, vigencia_fin, condiciones, aplicar_limite, created_by, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))""")
        params = (
            data.get('codigo'),
            data.get('nombre'),
            data.get('descripcion'),
            data.get('tipo'),
            data.get('valor_cents'),
            data.get('valor_porcentaje'),
            1 if data.get('activo', True) else 0,
            data.get('vigencia_inicio'),
            data.get('vigencia_fin'),
            data.get('condiciones'),
            1 if data.get('aplicar_limite') else 0,
            data.get('created_by'),
        )

        if self._db_wrapper is not None:
            cur = self._db_wrapper.execute_query(sql, params)
            return cur.lastrowid

        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(sql, params)
            conn.commit()
            return cur.lastrowid

    def apply_to_ticket(self, ticket_id: int, dto_aplicado_id: Optional[int], descuento_tipo: Optional[str], descuento_valor: Optional[int], descuento_euros_cents: Optional[int], cur: Optional[sqlite3.Cursor] = None) -> None:
        """Guarda en la fila `tickets` el `dto_aplicado_id` y campos snapshot del descuento.

        - `descuento_tipo`: por ejemplo 'directo' o 'porcentaje'
        - `descuento_valor`: porcentaje entero (ej. 10) o valor en céntimos según `descuento_tipo`
        - `descuento_euros_cents`: importe en céntimos aplicado al ticket
        """
        sql = """UPDATE tickets SET dto_aplicado_id = ?, descuento_tipo = ?, descuento_valor = ?, descuento_euros = ? WHERE id = ?"""
        params = (dto_aplicado_id, descuento_tipo, descuento_valor, descuento_euros_cents, ticket_id)

        if cur is not None:
            cur.execute(sql, params)
            return

        if self._db_wrapper is not None:
            self._db_wrapper.execute_query(sql, params)
            return

        with self._connect() as conn:
            cur2 = conn.cursor()
            cur2.execute(sql, params)
            conn.commit()
