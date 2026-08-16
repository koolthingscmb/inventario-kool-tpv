from typing import List, Optional
from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.produccion.models.produccion_metodo_model import ProduccionMetodo

class ProduccionMetodosRepository:
    """Acceso a datos para la tabla `produccion_metodos`."""

    def __init__(self, db: Database):
        self.db = db

    def get_activos(self) -> List[ProduccionMetodo]:
        """Obtener métodos de producción activos."""
        query = "SELECT id, nombre, descripcion, icono, activo, orden FROM produccion_metodos WHERE activo = 1 ORDER BY orden, nombre"
        rows = self.db.fetch_all(query)
        return [ProduccionMetodo(*row) for row in rows]

    def get_por_id(self, metodo_id: int) -> Optional[ProduccionMetodo]:
        query = "SELECT id, nombre, descripcion, icono, activo, orden FROM produccion_metodos WHERE id = ?"
        row = self.db.fetch_one(query, (metodo_id,))
        return ProduccionMetodo(*row) if row else None

    def crear(self, nombre: str) -> Optional[int]:
        """Crear un nuevo método de producción."""
        try:
            query = "INSERT INTO produccion_metodos (nombre) VALUES (?)"
            return self.db.execute_query(query, (nombre,))
        except Exception:
            return None

    def get_costes_por_diseno(self, diseno_codigo: str) -> dict:
        """Obtener un mapeo {metodo_id: coste} para un diseño."""
        query = "SELECT metodo_id, coste FROM produccion_disenos_metodos WHERE diseno_codigo = ?"
        rows = self.db.fetch_all(query, (diseno_codigo,))
        return {row[0]: row[1] for row in rows}

    def guardar_coste_diseno(self, diseno_codigo: str, metodo_id: int, coste: int, 
                             tipo_id: Optional[int] = None, variante_id: Optional[int] = None):
        """Guardar o actualizar el coste de un método para un diseño, opcionalmente por tipo/variante."""
        try:
            with self.db.transaction() as cur:
                # 1. Borrar coincidencia exacta
                if tipo_id is None and variante_id is None:
                    cur.execute(
                        "DELETE FROM produccion_disenos_metodos WHERE diseno_codigo = ? AND metodo_id = ? AND tipo_id IS NULL AND variante_id IS NULL",
                        (diseno_codigo, metodo_id)
                    )
                elif tipo_id is not None and variante_id is None:
                    cur.execute(
                        "DELETE FROM produccion_disenos_metodos WHERE diseno_codigo = ? AND metodo_id = ? AND tipo_id = ? AND variante_id IS NULL",
                        (diseno_codigo, metodo_id, tipo_id)
                    )
                else:
                    cur.execute(
                        "DELETE FROM produccion_disenos_metodos WHERE diseno_codigo = ? AND metodo_id = ? AND tipo_id = ? AND variante_id = ?",
                        (diseno_codigo, metodo_id, tipo_id, variante_id)
                    )

                # 2. Insertar nuevo
                cur.execute(
                    """
                    INSERT INTO produccion_disenos_metodos (diseno_codigo, metodo_id, tipo_id, variante_id, coste)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (diseno_codigo, metodo_id, tipo_id, variante_id, coste)
                )
        except Exception:
            import logging
            logging.exception(f"Error guardando coste diseño {diseno_codigo}")
            raise
        
    def eliminar_costes_diseno(self, diseno_codigo: str):
        """Eliminar todos los costes de métodos para un diseño."""
        query = "DELETE FROM produccion_disenos_metodos WHERE diseno_codigo = ?"
        self.db.execute_query(query, (diseno_codigo,))
