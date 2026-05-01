from decimal import Decimal
import logging
from datetime import datetime

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

    def get_app_mode(self) -> str:
        """Devuelve el modo de la aplicación.

        Si la clave `app_mode` no existe en la tabla `configuracion`, se crea
        automáticamente con el valor `development` y se retorna éste.
        Valores válidos: 'development', 'production'.
        """
        try:
            row = self.db.fetch_one("SELECT valor FROM configuracion WHERE clave = ? LIMIT 1", ("app_mode",))
            if not row or row[0] is None:
                # Crear valor por defecto en modo development
                try:
                    self.db.execute_query("INSERT OR REPLACE INTO configuracion (clave, valor) VALUES (?, ?)", ("app_mode", "development"))
                except Exception:
                    logging.exception('No se pudo crear app_mode por defecto')
                return "development"
            return str(row[0])
        except Exception:
            logging.exception('Error leyendo app_mode desde configuracion')
            return "development"

    def set_app_mode(self, mode: str) -> None:
        """Establece el modo de la aplicación a 'development' o 'production'."""
        if mode not in ("development", "production"):
            raise ValueError("app_mode must be 'development' or 'production'")
        try:
            self.db.execute_query("INSERT OR REPLACE INTO configuracion (clave, valor) VALUES (?, ?)", ("app_mode", mode))
        except Exception:
            logging.exception('Error guardando app_mode en configuracion')

    def reset_ticket_counter(self) -> None:
        """Reset del contador de tickets.

        IMPORTANTE:
        En `production` no se permite resetear el contador. Esta operación
        solo puede realizarse en `development` y en caso de error lanzará
        una excepción.
        """
        mode = self.get_app_mode()
        if mode != "development":
            # Protección explícita: evitar resets en producción
            raise RuntimeError("reset_ticket_counter is allowed only in development mode")
        try:
            # En modo development permitir reset seguro: poner contador a 0
            # y alinear el año al actual.
            year = datetime.now().year
            with self.db.transaction() as cur:
                cur.execute("INSERT OR REPLACE INTO configuracion (clave, valor) VALUES (?, ?)", ("ticket_counter_value", "0"))
                cur.execute("INSERT OR REPLACE INTO configuracion (clave, valor) VALUES (?, ?)", ("ticket_counter_year", str(year)))
        except Exception:
            logging.exception('Error reseteando ticket_counter en configuracion')

    def get_next_ticket_number(self, cur=None) -> str:
        """Devuelve el siguiente número de ticket con formato YYYY-XXXX.

        Reglas:
        - Reinicia automáticamente al cambiar de año.
        - Operación transaccional para evitar condiciones de carrera.
        """
        try:
            now_year = datetime.now().year
            # Si se recibe un cursor externo, reutilizarlo para integrarse en
            # la transacción del llamador. En caso contrario, abrir una
            # transacción propia.
            external_cursor = cur is not None
            if external_cursor:
                cursor = cur
                # Leer valores actuales
                cursor.execute("SELECT valor FROM configuracion WHERE clave = ? LIMIT 1", ("ticket_counter_year",))
                row_year = cursor.fetchone()
                cursor.execute("SELECT valor FROM configuracion WHERE clave = ? LIMIT 1", ("ticket_counter_value",))
                row_value = cursor.fetchone()

                stored_year = None
                stored_value = None
                if row_year and row_year[0] is not None:
                    try:
                        stored_year = int(row_year[0])
                    except Exception:
                        stored_year = None
                if row_value and row_value[0] is not None:
                    try:
                        stored_value = int(row_value[0])
                    except Exception:
                        stored_value = None

                if stored_year != now_year:
                    new_value = 1
                    cursor.execute("INSERT OR REPLACE INTO configuracion (clave, valor) VALUES (?, ?)", ("ticket_counter_year", str(now_year)))
                    cursor.execute("INSERT OR REPLACE INTO configuracion (clave, valor) VALUES (?, ?)", ("ticket_counter_value", str(new_value)))
                else:
                    if stored_value is None:
                        new_value = 1
                    else:
                        new_value = stored_value + 1
                    cursor.execute("INSERT OR REPLACE INTO configuracion (clave, valor) VALUES (?, ?)", ("ticket_counter_value", str(new_value)))
            else:
                with self.db.transaction() as cursor:
                    cursor.execute("SELECT valor FROM configuracion WHERE clave = ? LIMIT 1", ("ticket_counter_year",))
                    row_year = cursor.fetchone()
                    cursor.execute("SELECT valor FROM configuracion WHERE clave = ? LIMIT 1", ("ticket_counter_value",))
                    row_value = cursor.fetchone()

                    stored_year = None
                    stored_value = None
                    if row_year and row_year[0] is not None:
                        try:
                            stored_year = int(row_year[0])
                        except Exception:
                            stored_year = None
                    if row_value and row_value[0] is not None:
                        try:
                            stored_value = int(row_value[0])
                        except Exception:
                            stored_value = None

                    if stored_year != now_year:
                        new_value = 1
                        cursor.execute("INSERT OR REPLACE INTO configuracion (clave, valor) VALUES (?, ?)", ("ticket_counter_year", str(now_year)))
                        cursor.execute("INSERT OR REPLACE INTO configuracion (clave, valor) VALUES (?, ?)", ("ticket_counter_value", str(new_value)))
                    else:
                        if stored_value is None:
                            new_value = 1
                        else:
                            new_value = stored_value + 1
                        cursor.execute("INSERT OR REPLACE INTO configuracion (clave, valor) VALUES (?, ?)", ("ticket_counter_value", str(new_value)))

            return f"{now_year}-{new_value:04d}"
        except Exception:
            logging.exception('Error generando siguiente número de ticket')
            raise
