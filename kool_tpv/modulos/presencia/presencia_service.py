"""PresenciaService: Lógica de negocio para el control de presencia."""
import logging
from .presencia_repository import PresenciaRepository

class PresenciaService:
    def __init__(self, db):
        self.db = db
        self.repo = PresenciaRepository(db)

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

    def get_historial(self, usuario_id: int, limite: int = 5):
        """Historial reciente de fichajes."""
        return self.repo.get_ultimos_fichajes(usuario_id, limite)
