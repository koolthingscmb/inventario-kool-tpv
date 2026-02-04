import sqlite3
import os
import logging


class Database:
    def __init__(self, db_path: str):
        """Inicializar wrapper de base de datos SQLite.

        Args:
            db_path: Ruta al archivo .db (puede ser relativa o absoluta).
        """
        self.db_path = db_path
        self.connection = None

    def connect(self):
        """Establecer conexión con la base de datos SQLite."""
        if self.connection is None:
            try:
                # Asegurar que la carpeta existe si se proporciona ruta relativa
                db_dir = os.path.dirname(self.db_path)
                if db_dir and not os.path.exists(db_dir):
                    os.makedirs(db_dir, exist_ok=True)

                self.connection = sqlite3.connect(self.db_path)
                logging.info(f"Conectado a la base de datos: {self.db_path}")
            except sqlite3.Error as e:
                logging.error(f"Error al conectar con la base de datos: {e}")
                raise

    def execute_query(self, query: str, params: tuple | None = None):
        """Ejecutar una consulta que modifica datos (INSERT/UPDATE/DELETE).

        La función hace commit automáticamente.
        """
        if self.connection is None:
            raise RuntimeError("La conexión a la base de datos no está inicializada.")
        try:
            cursor = self.connection.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            self.connection.commit()
            return cursor
        except sqlite3.Error as e:
            logging.error(f"Error en la ejecución de la consulta: {e} -- Query: {query} -- Params: {params}")
            raise

    def fetch_all(self, query: str, params: tuple | None = None):
        """Ejecutar SELECT y devolver todos los registros."""
        if self.connection is None:
            raise RuntimeError("La conexión a la base de datos no está inicializada.")
        try:
            cursor = self.connection.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            rows = cursor.fetchall()
            return rows
        except sqlite3.Error as e:
            logging.error(f"Error al obtener registros: {e} -- Query: {query} -- Params: {params}")
            raise

    def fetch_one(self, query: str, params: tuple | None = None):
        """Ejecutar SELECT y devolver un único registro."""
        if self.connection is None:
            raise RuntimeError("La conexión a la base de datos no está inicializada.")
        try:
            cursor = self.connection.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            row = cursor.fetchone()
            return row
        except sqlite3.Error as e:
            logging.error(f"Error al obtener registro: {e} -- Query: {query} -- Params: {params}")
            raise

    def close_connection(self):
        """Cerrar la conexión a la base de datos si está abierta."""
        if self.connection:
            try:
                self.connection.close()
                logging.info("Conexión a la base de datos cerrada.")
            except sqlite3.Error as e:
                logging.error(f"Error al cerrar la conexión de la base de datos: {e}")
            finally:
                self.connection = None
# Wrapper común de conexión a la base de datos
# Placeholder: aquí se centralizarán las conexiones a SQLite.
