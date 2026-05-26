import sqlite3
import os
import logging
from contextlib import contextmanager
from typing import Optional, Iterator


class Database:
    def __init__(self, db_path: str, **sqlite_kwargs):
        """Wrapper de SQLite más robusto.

        Args:
            db_path: ruta al archivo .db o URI.
            sqlite_kwargs: argumentos pasados a sqlite3.connect (p. ej. timeout, check_same_thread).
        """
        self.db_path = db_path
        self.connection: Optional[sqlite3.Connection] = None
        # sane defaults for concurrency
        self._sqlite_kwargs = dict(check_same_thread=False, timeout=10)
        # allow overriding defaults
        self._sqlite_kwargs.update(sqlite_kwargs)

    def connect(self):
        """Establecer conexión con la base de datos SQLite y configurar row_factory."""
        if self.connection is None:
            try:
                # Ensure parent dir exists for file-based DBs
                if self.db_path not in (':memory:', '') and not self.db_path.startswith('file:'):
                    db_dir = os.path.dirname(self.db_path)
                    if db_dir and not os.path.exists(db_dir):
                        os.makedirs(db_dir, exist_ok=True)

                # Do not use PARSE_DECLTYPES/PARSE_COLNAMES to avoid automatic
                # conversion of date columns to datetime.date. Return dates as text.
                self.connection = sqlite3.connect(self.db_path, **self._sqlite_kwargs)
                # allow access by column name
                try:
                    self.connection.row_factory = sqlite3.Row
                except Exception:
                    pass
                # SQLite deshabilita FK por defecto — activar para que ON DELETE CASCADE funcione
                self.connection.execute('PRAGMA foreign_keys = ON')
                logging.info(f"Conectado a la base de datos: {self.db_path}")
            except sqlite3.Error as e:
                logging.error(f"Error al conectar con la base de datos: {e}")
                raise

    def execute_query(self, query: str, params: tuple | None = None):
        """Execute a modifying query and commit automatically."""
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
        """Execute SELECT and return all rows."""
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
        """Execute SELECT and return a single row."""
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
        """Close DB connection."""
        if self.connection:
            try:
                self.connection.close()
                logging.info("Conexión a la base de datos cerrada.")
            except sqlite3.Error as e:
                logging.error(f"Error al cerrar la conexión de la base de datos: {e}")
            finally:
                self.connection = None

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Cursor]:
        """Context manager for transactions.

        Usage:
            with db.transaction() as cur:
                cur.execute(...)
        Commits on success, rollbacks on exception.
        """
        if self.connection is None:
            raise RuntimeError("La conexión a la base de datos no está inicializada.")
        cur = self.connection.cursor()
        # Support nested transactions using SAVEPOINTs. If there's no active
        # transaction, start a normal one with BEGIN/COMMIT/ROLLBACK. If there
        # is already a transaction (connection.in_transaction), use a SAVEPOINT
        # so that we can rollback/commit locally without disturbing the outer
        # transaction.
        use_savepoint = getattr(self.connection, 'in_transaction', False)
        sp_name = None
        try:
            if use_savepoint:
                # create a unique savepoint name
                import uuid

                sp_name = f"sp_{uuid.uuid4().hex[:12]}"
                cur.execute(f"SAVEPOINT {sp_name}")
                yield cur
                # Release the savepoint to commit the nested work
                cur.execute(f"RELEASE SAVEPOINT {sp_name}")
            else:
                cur.execute('BEGIN')
                yield cur
                try:
                    self.connection.commit()
                except Exception:
                    self.connection.rollback()
                    raise
        except Exception:
            try:
                if use_savepoint and sp_name:
                    try:
                        cur.execute(f"ROLLBACK TO SAVEPOINT {sp_name}")
                        cur.execute(f"RELEASE SAVEPOINT {sp_name}")
                    except Exception:
                        # Best effort: if rollback to savepoint fails, try a full rollback
                        try:
                            self.connection.rollback()
                        except Exception:
                            pass
                else:
                    try:
                        self.connection.rollback()
                    except Exception:
                        pass
            except Exception:
                pass
            raise
