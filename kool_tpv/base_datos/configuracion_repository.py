import logging
from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.base_datos.audit_service import AuditService

logger = logging.getLogger(__name__)


class ConfiguracionRepository:
    def __init__(self, db: Database):
        self.db = db
        self.audit = AuditService(db)

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

    def guardar_multiples(self, campos: dict, usuario_id: int = None) -> None:
        """Guarda múltiples pares clave/valor en configuracion en UNA transacción atómica, auditando solo los cambios reales."""
        try:
            # 1. Obtener valores actuales para comparar
            claves = list(campos.keys())
            valores_anteriores = self.obtener_multiples(claves)
            
            detalles_cambios = []
            
            cur = self.db.connection.cursor()
            cur.execute('BEGIN')
            
            for clave, valor_nuevo in campos.items():
                valor_antiguo = valores_anteriores.get(clave)
                
                # Solo procesar si el valor ha cambiado realmente
                if str(valor_nuevo) != str(valor_antiguo):
                    cur.execute(
                        "INSERT OR REPLACE INTO configuracion (clave, valor) VALUES (?, ?)",
                        (clave, valor_nuevo)
                    )
                    detalles_cambios.append(f"{clave}: {valor_antiguo} -> {valor_nuevo}")
            
            # 2. Si hay cambios reales, auditar
            if detalles_cambios:
                resumen_audit = "Actualización configuración: " + " | ".join(detalles_cambios)
                
                self.audit.registrar(
                    entidad='configuracion',
                    entidad_id=0,
                    accion='ACTUALIZACION_CONFIG',
                    usuario_id=usuario_id,
                    datos_nuevos=resumen_audit,
                    cur=cur
                )
            
            self.db.connection.commit()
        except Exception:
            self.db.connection.rollback()
            logger.exception('Error guardando configuración múltiple')
            raise
