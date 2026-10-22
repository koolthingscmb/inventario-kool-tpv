"""Servicio de vales de devolución — lógica de negocio sobre la BD.

Los vales viven en las tablas `vales` y `vales_usos` (migración 065).
Mantiene la misma interfaz pública que la versión basada en JSON para no
tocar las pantallas que lo usan.
"""
import logging
import uuid
from pathlib import Path

from kool_tpv.paths import DB_PATH, BORRADORES_DIR
from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.tpv.vale_repository import ValeRepository

logger = logging.getLogger(__name__)


class ValeDevolucionService:
    """Gestiona vales de devolución persistidos en la base de datos."""

    def __init__(self, db: Database | None = None):
        self._db = db
        self._repo: ValeRepository | None = None

    @property
    def repo(self) -> ValeRepository:
        """Conexión perezosa: abre la BD solo cuando se usa de verdad."""
        if self._repo is None:
            if self._db is None:
                self._db = Database(str(DB_PATH))
                self._db.connect()
            self._repo = ValeRepository(self._db)
        return self._repo

    # ------------------------------------------------------------------
    def guardar(
        self,
        importe_cents: int,
        num_ticket_devolucion: str,
        cliente_id: int | None = None,
        cliente_nombre: str | None = None,
        productos_nombres: str | None = None,
    ) -> str:
        """Crea un vale nuevo con el saldo completo y devuelve su id."""
        vale_id = str(uuid.uuid4())
        self.repo.crear(
            vale_id=vale_id,
            num_vale=self.repo.siguiente_num_vale(),
            nombre=productos_nombres or '',
            importe_cents=int(importe_cents),
            num_ticket_devolucion=str(num_ticket_devolucion),
            cliente_id=cliente_id,
            cliente_nombre=cliente_nombre,
        )
        self._db.connection.commit()
        logger.info(f'Vale guardado en BD: {vale_id} ({importe_cents} céntimos)')
        return vale_id

    # ------------------------------------------------------------------
    def listar(self) -> list[dict]:
        """Vales no usados (activos y reservados), del más reciente al más antiguo."""
        return [v for v in self.repo.listar_todos() if not v.get('usado')]

    def listar_activos(self) -> list[dict]:
        """Devuelve solo los vales NO usados y NO reservados."""
        return self.repo.listar_activos()

    def listar_todos(self) -> list[dict]:
        """Devuelve todos los vales (activos + usados), del más reciente al más antiguo."""
        return self.repo.listar_todos()

    # ------------------------------------------------------------------
    def obtener_por_id(self, vale_id: str) -> dict | None:
        """Carga un vale por su UUID, con su historial de consumos."""
        try:
            vale = self.repo.obtener_por_id(vale_id)
            if not vale:
                return None
            vale['consumos'] = self.repo.listar_usos(vale_id)
            return vale
        except Exception:
            logger.warning(f'Error cargando vale {vale_id}')
            return None

    # ------------------------------------------------------------------
    def consumir_parcial(self, vale_id: str, importe_cents: int,
                         num_ticket_venta_uso: str, cur=None) -> bool:
        """Resta el importe consumido del saldo restante del vale.

        Si el saldo llega a cero, el vale queda marcado como usado y el
        consumo queda registrado en vales_usos en la misma operación.

        Con ``cur`` se ejecuta dentro de una transacción externa (sin
        commit propio): cualquier error se propaga para que el llamante
        revierta la operación completa.
        """
        try:
            vale = self.repo.obtener_por_id(vale_id)
            if not vale:
                logger.warning(f'Vale no encontrado: {vale_id}')
                return False
            if vale.get('usado'):
                logger.warning(f'Vale {vale_id} ya está usado')
                return False

            saldo_actual = vale.get('importe_restante_cents', vale.get('importe_cents', 0))
            if int(importe_cents) > int(saldo_actual):
                logger.warning(f'Importe a consumir ({importe_cents}) mayor que saldo ({saldo_actual})')
                return False

            nuevo_restante = int(saldo_actual) - int(importe_cents)
            self.repo.registrar_consumo(
                vale_id=vale_id,
                importe_cents=int(importe_cents),
                num_ticket_venta_uso=str(num_ticket_venta_uso),
                nuevo_restante=nuevo_restante,
                agotado=nuevo_restante <= 0,
                cur=cur,
            )
            if cur is None:
                self._db.connection.commit()
            logger.info(f'Vale {vale_id} consumido: -{importe_cents} céntimos, restante: {nuevo_restante}')
            return True
        except Exception:
            if cur is not None:
                raise
            logger.exception(f'Error consumiendo vale {vale_id} parcialmente')
            try:
                self._db.connection.rollback()
            except Exception:
                pass
            return False

    # ------------------------------------------------------------------
    def marcar_usado(self, vale_id: str, num_ticket_venta_uso: str,
                     cur=None) -> bool:
        """Marca un vale como usado consumiendo todo su saldo restante.

        Para vales anónimos el vale se gasta entero: si quedaba saldo, se
        registra como consumo final y el vale queda a 0.

        Con ``cur`` se ejecuta dentro de una transacción externa (sin
        commit propio): cualquier error se propaga para que el llamante
        revierta la operación completa.
        """
        try:
            vale = self.repo.obtener_por_id(vale_id)
            if not vale:
                logger.warning(f'Vale no encontrado: {vale_id}')
                return False
            if vale.get('usado'):
                return True

            restante = int(vale.get('importe_restante_cents', vale.get('importe_cents', 0)) or 0)
            if restante > 0:
                self.repo.registrar_consumo(
                    vale_id=vale_id,
                    importe_cents=restante,
                    num_ticket_venta_uso=str(num_ticket_venta_uso),
                    nuevo_restante=0,
                    agotado=True,
                    cur=cur,
                )
            else:
                self.repo.marcar_usado(
                    vale_id=vale_id,
                    num_ticket_venta_uso=str(num_ticket_venta_uso),
                    cur=cur,
                )
            if cur is None:
                self._db.connection.commit()
            logger.info(f'Vale {vale_id} marcado como usado en venta {num_ticket_venta_uso}')
            return True
        except Exception:
            if cur is not None:
                raise
            logger.exception(f'Error marcando vale {vale_id} como usado')
            try:
                self._db.connection.rollback()
            except Exception:
                pass
            return False

    # ------------------------------------------------------------------
    def marcar_reservado(self, vale_id: str, pedido_id: int | None = None) -> bool:
        """Marca un vale como reservado para un pedido."""
        try:
            return self.repo.marcar_reservado(vale_id, pedido_id)
        except Exception:
            logger.exception(f"Error marcando vale {vale_id} como reservado")
            return False

    # ------------------------------------------------------------------
    def eliminar(self, vale_id: str) -> bool:
        """Elimina el vale de la BD (su historial de usos se conserva)."""
        try:
            return self.repo.eliminar(vale_id)
        except Exception:
            logger.warning(f'No se pudo eliminar vale: {vale_id}')
            return False

    def eliminar_por_path(self, path_str: str) -> bool:
        """Elimina un vale antiguo guardado como JSON (limpieza heredada)."""
        try:
            p = Path(path_str)
            if p.exists():
                p.unlink()
                logger.info(f'Vale JSON eliminado: {path_str}')
                return True
            return False
        except Exception:
            logger.warning(f'No se pudo eliminar vale por path: {path_str}')
            return False

    # ------------------------------------------------------------------
    def hay_vales_activos(self) -> bool:
        """Devuelve True si existe al menos un vale no usado y NO reservado."""
        try:
            return self.repo.hay_activos()
        except Exception:
            return False
