"""Repository de vales de devolución — operaciones SQL sobre vales y vales_usos.

Esta capa no realiza cálculos de negocio. Los importes se reciben ya en
céntimos enteros. Los métodos aceptan un cursor externo (``cur``) para
poder participar en transacciones gestionadas por la capa superior.
"""
import logging
from datetime import datetime
from typing import Optional

from kool_tpv.base_datos.db_wrapper import Database

logger = logging.getLogger(__name__)

_COLS = (
    'id, num_vale, nombre, fecha, importe_cents, importe_original_cents, '
    'importe_restante_cents, cliente_id, cliente_nombre, num_ticket_devolucion, '
    'usado, reservado, pedido_id, num_ticket_venta_uso, fecha_uso'
)


def _row_a_dict(row) -> dict:
    keys = _COLS.split(', ')
    return dict(zip(keys, row))


class ValeRepository:
    def __init__(self, db: Database):
        self.db = db

    def _cursor(self, cur=None):
        return cur if cur is not None else self.db.connection.cursor()

    # ------------------------------------------------------------------
    def crear(self, *, vale_id: str, num_vale: int, importe_cents: int,
              num_ticket_devolucion: str, cliente_id: Optional[int] = None,
              cliente_nombre: Optional[str] = None,
              nombre: Optional[str] = None, cur=None) -> None:
        """Inserta un vale nuevo con el saldo completo disponible."""
        self._cursor(cur).execute(
            f'INSERT INTO vales ({_COLS}) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, NULL, NULL, NULL)',
            (vale_id, int(num_vale), nombre or '', datetime.now().isoformat(),
             int(importe_cents), int(importe_cents), int(importe_cents),
             cliente_id, cliente_nombre or '', str(num_ticket_devolucion)),
        )

    def siguiente_num_vale(self) -> int:
        """Próximo número de vale (máximo + 1; nunca reutiliza números)."""
        row = self.db.connection.cursor().execute(
            'SELECT MAX(num_vale) FROM vales').fetchone()
        return int(row[0] or 0) + 1

    # ------------------------------------------------------------------
    def obtener_por_id(self, vale_id: str) -> Optional[dict]:
        """Devuelve el vale como dict o None si no existe."""
        row = self.db.connection.cursor().execute(
            f'SELECT {_COLS} FROM vales WHERE id = ?', (vale_id,)).fetchone()
        return _row_a_dict(row) if row else None

    # ------------------------------------------------------------------
    def listar_todos(self) -> list[dict]:
        """Todos los vales, del más reciente al más antiguo."""
        rows = self.db.connection.cursor().execute(
            f'SELECT {_COLS} FROM vales ORDER BY fecha DESC').fetchall()
        return [_row_a_dict(r) for r in rows]

    def listar_activos(self) -> list[dict]:
        """Vales no usados ni reservados, del más reciente al más antiguo."""
        rows = self.db.connection.cursor().execute(
            f'SELECT {_COLS} FROM vales WHERE usado = 0 AND reservado = 0 '
            'ORDER BY fecha DESC').fetchall()
        return [_row_a_dict(r) for r in rows]

    def hay_activos(self) -> bool:
        row = self.db.connection.cursor().execute(
            'SELECT 1 FROM vales WHERE usado = 0 AND reservado = 0 LIMIT 1'
        ).fetchone()
        return row is not None

    def contar(self) -> int:
        row = self.db.connection.cursor().execute(
            'SELECT COUNT(*) FROM vales').fetchone()
        return int(row[0]) if row else 0

    # ------------------------------------------------------------------
    def registrar_consumo(self, *, vale_id: str, importe_cents: int,
                          num_ticket_venta_uso: str, nuevo_restante: int,
                          agotado: bool, cur=None) -> None:
        """Actualiza el saldo del vale y registra el uso en vales_usos.

        Si ``agotado`` es True, el vale queda marcado como usado y se le
        quita la reserva. No valida el saldo: eso es responsabilidad del
        servicio, que ha leído el vale antes de llamar aquí.
        """
        c = self._cursor(cur)
        ahora = datetime.now().isoformat()
        if agotado:
            c.execute(
                'UPDATE vales SET importe_restante_cents = ?, usado = 1, '
                'reservado = 0, pedido_id = NULL, num_ticket_venta_uso = ?, '
                'fecha_uso = ? WHERE id = ?',
                (int(nuevo_restante), str(num_ticket_venta_uso), ahora, vale_id))
        else:
            c.execute(
                'UPDATE vales SET importe_restante_cents = ? WHERE id = ?',
                (int(nuevo_restante), vale_id))
        c.execute(
            'INSERT INTO vales_usos (vale_id, num_ticket_venta_uso, fecha, '
            'importe_cents) VALUES (?, ?, ?, ?)',
            (vale_id, str(num_ticket_venta_uso), ahora, int(importe_cents)))

    # ------------------------------------------------------------------
    def marcar_usado(self, *, vale_id: str, num_ticket_venta_uso: str,
                     cur=None) -> None:
        """Marca el vale como usado sin registrar consumo (saldo ya en 0)."""
        self._cursor(cur).execute(
            'UPDATE vales SET usado = 1, reservado = 0, pedido_id = NULL, '
            'num_ticket_venta_uso = ?, fecha_uso = ? WHERE id = ?',
            (str(num_ticket_venta_uso), datetime.now().isoformat(), vale_id))

    # ------------------------------------------------------------------
    def listar_usos(self, vale_id: str) -> list[dict]:
        """Historial de consumos de un vale, del más antiguo al más reciente."""
        rows = self.db.connection.cursor().execute(
            'SELECT id, vale_id, num_ticket_venta_uso, fecha, importe_cents '
            'FROM vales_usos WHERE vale_id = ? ORDER BY fecha, id',
            (vale_id,)).fetchall()
        return [
            {'id': r[0], 'vale_id': r[1], 'num_ticket_venta_uso': r[2],
             'fecha': r[3], 'importe_cents': r[4]}
            for r in rows
        ]

    # ------------------------------------------------------------------
    def marcar_reservado(self, vale_id: str, pedido_id: Optional[int] = None) -> bool:
        """Reserva un vale para un pedido. False si no existe."""
        c = self.db.connection.cursor()
        c.execute(
            'UPDATE vales SET reservado = 1, pedido_id = ? WHERE id = ?',
            (pedido_id, vale_id))
        self.db.connection.commit()
        ok = c.rowcount > 0
        if ok:
            logger.info(f'Vale {vale_id} reservado para pedido {pedido_id}')
        return ok

    # ------------------------------------------------------------------
    def eliminar(self, vale_id: str) -> bool:
        """Elimina el vale. Los usos registrados se conservan como historial."""
        c = self.db.connection.cursor()
        c.execute('DELETE FROM vales WHERE id = ?', (vale_id,))
        self.db.connection.commit()
        ok = c.rowcount > 0
        if ok:
            logger.info(f'Vale eliminado: {vale_id}')
        return ok
