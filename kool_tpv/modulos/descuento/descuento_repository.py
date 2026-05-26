from __future__ import annotations
import sqlite3
import os
from typing import Optional, List, Dict, Any

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'base_datos', 'kool_bd.db')


def _dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


class DescuentoRepository:
    """Repositorio para plantillas de descuento y persistencia de aplicación sobre tickets.

    Notas:
    - Usa la base de datos sqlite local por defecto (`kool_tpv/base_datos/kool_bd.db`).
    - Las operaciones sobre el ticket (snapshot) se realizan aquí como una simple UPDATE;
      la lógica de cálculo debe residir en `descuento_service`.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or DB_PATH

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = _dict_factory
        return conn

    def listar_activos(self) -> List[Dict[str, Any]]:
        """Devuelve las plantillas de descuento activas (activo=1)."""
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM descuentos WHERE activo=1 ORDER BY nombre")
            return cur.fetchall()

    def get_by_id(self, descuento_id: int) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM descuentos WHERE id = ?", (descuento_id,))
            row = cur.fetchone()
            return row

    def create_template(self, data: Dict[str, Any]) -> int:
        """Crea una plantilla de descuento y devuelve su id."""
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO descuentos (codigo, nombre, descripcion, tipo, valor_cents, valor_porcentaje, activo, vigencia_inicio, vigencia_fin, condiciones, aplicar_limite, created_by, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))""",
                (
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
                ),
            )
            conn.commit()
            return cur.lastrowid

    def apply_to_ticket(self, ticket_id: int, dto_aplicado_id: Optional[int], descuento_tipo: Optional[str], descuento_valor: Optional[int], descuento_euros_cents: Optional[int]) -> None:
        """Guarda en la fila `tickets` el `dto_aplicado_id` y campos snapshot del descuento.

        - `descuento_tipo`: por ejemplo 'directo' o 'porcentaje'
        - `descuento_valor`: porcentaje entero (ej. 10) o valor en céntimos según `descuento_tipo`
        - `descuento_euros_cents`: importe en céntimos aplicado al ticket
        """
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """UPDATE tickets SET dto_aplicado_id = ?, descuento_tipo = ?, descuento_valor = ?, descuento_euros = ? WHERE id = ?""",
                (dto_aplicado_id, descuento_tipo, descuento_valor, descuento_euros_cents, ticket_id),
            )
            conn.commit()
