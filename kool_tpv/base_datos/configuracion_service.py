from decimal import Decimal
import logging

from .db_wrapper import Database


class ConfiguracionService:
    """Servicio simple para leer parámetros de la tabla `configuracion`."""

    def __init__(self, db: Database):
        self.db = db

    def get_fide_porcentaje_global(self) -> Decimal:
        """Devuelve el porcentaje global de fidelización.

        Busca la clave `fide_porcentaje_general` en la tabla `configuracion`.
        Si no existe o hay un error, devuelve Decimal('0').
        """
        try:
            row = self.db.fetch_one("SELECT valor FROM configuracion WHERE clave = ? LIMIT 1", ("fide_porcentaje_general",))
            if not row:
                return Decimal('0')
            val = row[0]
            try:
                # Normalizar a Decimal desde string/number
                return Decimal(str(val))
            except Exception:
                return Decimal('0')
        except Exception:
            logging.exception('Error leyendo porcentaje global de fidelización')
            return Decimal('0')
