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

    def guardar_coste_diseno(self, diseno_codigo: str, metodo_id: int, coste: int):
        """Guardar o actualizar el coste de un método para un diseño."""
        query = """
            INSERT INTO produccion_disenos_metodos (diseno_codigo, metodo_id, coste)
            VALUES (?, ?, ?)
            ON CONFLICT(diseno_codigo, metodo_id) DO UPDATE SET coste = excluded.coste
        """
        self.db.execute_query(query, (diseno_codigo, metodo_id, coste))
        
    def eliminar_costes_diseno(self, diseno_codigo: str):
        """Eliminar todos los costes de métodos para un diseño."""
        query = "DELETE FROM produccion_disenos_metodos WHERE diseno_codigo = ?"
        self.db.execute_query(query, (diseno_codigo,))
