"""Service layer for clientes.

This module provides ClienteService which encapsulates all DB access related
to the `clientes` table so the UI does not execute SQL directly.

Design notes:
- Uses `database.connect()` as a context manager.
- Returns rows as dictionaries by setting `conn.row_factory = sqlite3.Row`.
- Methods handle exceptions and log errors; they return None/False on failure
  or appropriate empty collections.
"""
from typing import List, Dict, Optional, Any
import sqlite3
import logging
from datetime import datetime

import database

logger = logging.getLogger(__name__)


class ClienteService:
    """Encapsula operaciones CRUD y utilidades para clientes."""

    def __init__(self):
        # Nothing to initialize for now; kept for future dependency injection
        pass

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        if row is None:
            return None
        return {k: row[k] for k in row.keys()}

    def obtener_todos(self) -> List[Dict[str, Any]]:
        """Devuelve todos los clientes como lista de diccionarios."""
        try:
            with database.connect() as conn:
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                cur.execute("SELECT * FROM clientes ORDER BY nombre COLLATE NOCASE")
                rows = cur.fetchall()
                return [self._row_to_dict(r) for r in rows]
        except Exception as e:
            logger.exception("Error obteniendo todos los clientes: %s", e)
            return []

    def buscar_clientes(self, termino: str) -> List[Dict[str, Any]]:
        """Busca clientes por nombre, telefono o dni (LIKE, case-insensitive).

        `termino` se utiliza con comodines por ambas partes.
        """
        try:
            like = f"%{termino}%"
            with database.connect() as conn:
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT * FROM clientes
                    WHERE nombre LIKE ? OR telefono LIKE ? OR dni LIKE ?
                    ORDER BY nombre COLLATE NOCASE
                    """,
                    (like, like, like),
                )
                rows = cur.fetchall()
                return [self._row_to_dict(r) for r in rows]
        except Exception as e:
            logger.exception("Error buscando clientes con termino '%s': %s", termino, e)
            return []

    def obtener_por_id(self, cliente_id: int) -> Optional[Dict[str, Any]]:
        """Devuelve un cliente por su id o None si no existe."""
        try:
            with database.connect() as conn:
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                cur.execute("SELECT * FROM clientes WHERE id=?", (cliente_id,))
                row = cur.fetchone()
                return self._row_to_dict(row)
        except Exception as e:
            logger.exception("Error obteniendo cliente id=%s: %s", cliente_id, e)
            return None

    def crear_cliente(self, datos: Dict[str, Any]) -> Optional[int]:
        """Inserta un nuevo cliente. Devuelve el id creado o None en fallo.

        Campos aceptados en `datos`: nombre, telefono, email, dni, direccion,
        ciudad, cp, tags, notas_internas
        """
        try:
            nombre = datos.get("nombre")
            telefono = datos.get("telefono")
            email = datos.get("email")
            dni = datos.get("dni")
            direccion = datos.get("direccion")
            ciudad = datos.get("ciudad")
            cp = datos.get("cp")
            tags = datos.get("tags")
            notas = datos.get("notas_internas")

            fecha_alta = datetime.now().isoformat()
            puntos = 0
            total = 0.0

            with database.connect() as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO clientes
                    (nombre, telefono, email, dni, direccion, ciudad, cp, tags, notas_internas, puntos_fidelidad, total_gastado, fecha_alta)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (nombre, telefono, email, dni, direccion, ciudad, cp, tags, notas, puntos, total, fecha_alta),
                )
                conn.commit()
                return cur.lastrowid
        except Exception as e:
            logger.exception("Error creando cliente con datos %s: %s", datos, e)
            return None

    def actualizar_cliente(self, cliente_id: int, datos: Dict[str, Any]) -> bool:
        """Actualiza campos de un cliente existente. Devuelve True si se actualizó."""
        try:
            # Filtrar campos permitidos
            allowed = {
                "nombre",
                "telefono",
                "email",
                "dni",
                "direccion",
                "ciudad",
                "cp",
                "tags",
                "notas_internas",
                "puntos_fidelidad",
                "total_gastado",
            }
            items = [(k, datos[k]) for k in datos.keys() if k in allowed]
            if not items:
                return False
            set_clause = ", ".join([f"{k}=?" for k, _ in items])
            values = [v for _, v in items]
            values.append(cliente_id)
            sql = f"UPDATE clientes SET {set_clause} WHERE id=?"
            with database.connect() as conn:
                cur = conn.cursor()
                cur.execute(sql, values)
                conn.commit()
                return cur.rowcount > 0
        except Exception as e:
            logger.exception("Error actualizando cliente id=%s con %s: %s", cliente_id, datos, e)
            return False

    def eliminar_cliente(self, cliente_id: int) -> bool:
        """Elimina un cliente por id. Devuelve True si se eliminó algún registro."""
        try:
            with database.connect() as conn:
                cur = conn.cursor()
                cur.execute("DELETE FROM clientes WHERE id=?", (cliente_id,))
                conn.commit()
                return cur.rowcount > 0
        except Exception as e:
            logger.exception("Error eliminando cliente id=%s: %s", cliente_id, e)
            return False

    def sumar_puntos(self, cliente_id: int, puntos: float) -> bool:
        """Suma (o resta si negativo) puntos de fidelidad a un cliente.

        El argumento `puntos` se interpreta como número decimal (float).
        """
        try:
            with database.connect() as conn:
                cur = conn.cursor()
                try:
                    pts = float(puntos)
                except Exception:
                    pts = 0.0
                cur.execute(
                    "UPDATE clientes SET puntos_fidelidad = COALESCE(puntos_fidelidad,0) + ? WHERE id=?",
                    (pts, cliente_id),
                )
                conn.commit()
                return cur.rowcount > 0
        except Exception as e:
            logger.exception("Error sumando puntos (%s) al cliente id=%s: %s", puntos, cliente_id, e)
            return False

    def registrar_gasto(self, cliente_id: int, importe: float) -> bool:
        """Registra un gasto aumentando `total_gastado` en el importe indicado."""
        try:
            with database.connect() as conn:
                cur = conn.cursor()
                cur.execute(
                    "UPDATE clientes SET total_gastado = COALESCE(total_gastado,0) + ? WHERE id=?",
                    (importe, cliente_id),
                )
                conn.commit()
                return cur.rowcount > 0
        except Exception as e:
            logger.exception("Error registrando gasto (%s) para cliente id=%s: %s", importe, cliente_id, e)
            return False
