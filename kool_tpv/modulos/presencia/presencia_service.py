"""PresenciaService: Lógica de negocio para el control de presencia."""
import logging
from .presencia_repository import PresenciaRepository
from kool_tpv.base_datos.audit_service import AuditService

class PresenciaService:
    def __init__(self, db):
        self.db = db
        self.repo = PresenciaRepository(db)
        self.audit = AuditService(db)

    def get_estado_usuario(self, usuario_id: int) -> dict:
        """Devuelve el estado actual de un usuario (TRABAJANDO/FUERA)."""
        sesion = self.repo.get_sesion_activa(usuario_id)
        if sesion:
            return {
                "trabajando": True,
                "sesion_id": sesion["id"],
                "desde": sesion["entrada"],
                "texto": "TRABAJANDO"
            }
        return {
            "trabajando": False,
            "sesion_id": None,
            "desde": None,
            "texto": "FUERA"
        }

    def fichar(self, usuario_id: int, notas: str = "") -> dict:
        """Realiza la acción de fichar (entrada o salida según estado)."""
        estado = self.get_estado_usuario(usuario_id)
        
        try:
            if estado["trabajando"]:
                # Si está trabajando, fichamos salida
                success = self.repo.registrar_salida(estado["sesion_id"])
                return {"success": success, "tipo": "salida"}
            else:
                # Si está fuera, fichamos entrada
                id_nuevo = self.repo.registrar_entrada(usuario_id, notas)
                return {"success": id_nuevo > 0, "tipo": "entrada"}
        except Exception as e:
            logging.exception(f"Error al fichar para usuario {usuario_id}")
            return {"success": False, "error": str(e)}

    def corregir_fichaje(self, sesion_id: int, fecha_salida: str, notas: str = "", responsable_id: int = None) -> dict:
        """Cierra manualmente una sesión antigua y registra auditoría."""
        try:
            # Obtener datos de la sesión para la auditoría antes de cambiarla
            query = "SELECT usuario_id, entrada FROM presencia WHERE id = ?"
            row = self.db.fetch_one(query, (sesion_id,))
            
            with self.db.transaction() as cur:
                success = self.repo.registrar_salida_manual(sesion_id, fecha_salida, notas)
                
                if success and row:
                    usuario_id = row[0]
                    entrada_raw = row[1]
                    
                    # Registrar en auditoría
                    self.audit.registrar(
                        entidad='presencia',
                        entidad_id=sesion_id,
                        accion='CORRECCION_PRESENCIA',
                        usuario_id=responsable_id or usuario_id,
                        datos_nuevos=f"Sesión ID {sesion_id} (Usuario {usuario_id}). Entrada: {entrada_raw} -> Salida manual: {fecha_salida}. Motivo: {notas}",
                        cur=cur
                    )
                
                return {"success": success}
        except Exception as e:
            logging.exception(f"Error al corregir fichaje {sesion_id}")
            return {"success": False, "error": str(e)}

    def get_historial(self, usuario_id: int, limite: int = 5):
        """Historial reciente de fichajes."""
        return self.repo.get_ultimos_fichajes(usuario_id, limite)
