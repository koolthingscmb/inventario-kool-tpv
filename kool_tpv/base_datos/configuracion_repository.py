import logging
from kool_tpv.base_datos.db_wrapper import Database

logger = logging.getLogger(__name__)


class ConfiguracionRepository:
    def __init__(self, db: Database):
        self.db = db

    def obtener_multiples(self, claves: list) -> dict:
        """Obtiene múltiples claves de configuracion en UNA sola query."""
        if not claves:
            return {}
        placeholders = ','.join(['?' for _ in claves])
        rows = self.db.fetch_all(
            f"SELECT clave, valor FROM configuracion WHERE clave IN ({placeholders})",
            claves
        )
        return {row[0]: row[1] for row in rows}

    def guardar_multiples(self, campos: dict) -> None:
        """Guarda múltiples pares clave/valor en configuracion en UNA transacción atómica."""
        try:
            cur = self.db.connection.cursor()
            cur.execute('BEGIN')
            for clave, valor in campos.items():
                cur.execute(
                    "INSERT OR REPLACE INTO configuracion (clave, valor) VALUES (?, ?)",
                    (clave, valor)
                )
            self.db.connection.commit()
        except Exception:
            self.db.connection.rollback()
            logger.exception('Error guardando configuración múltiple')
            raise
