"""Repositorio de fuentes y editoriales (tablas `editoriales_fuentes` y
`editoriales`).

`editoriales_fuentes`: el sitio que responde a las búsquedas (plataforma =
qué código lo atiende: zonalibros/planeta/shopify) con sus credenciales.
`editoriales`: cada nombre que puede llevar el campo Editorial de un
producto, a qué fuente apunta (`fuente_id`) y su web para el botón IR.

Solo SQL; la lógica vive en `services/fuentes_editorial_service.py`.
"""
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_COLS_FUENTE = "id, nombre, plataforma, url, nif, usuario, password"
_COLS_EDITORIAL = "id, nombre, fuente_id, fuente_reserva_id, web_buscar, web_dominio"


def _fuente(row) -> Dict[str, Any]:
    return {
        "id": row[0], "nombre": row[1] or "", "plataforma": row[2] or "",
        "url": row[3] or "", "nif": row[4] or "", "usuario": row[5] or "",
        "password": row[6] or "",
    }


def _editorial(row) -> Dict[str, Any]:
    return {
        "id": row[0], "nombre": row[1] or "", "fuente_id": row[2],
        "fuente_reserva_id": row[3],
        "web_buscar": row[4] or "", "web_dominio": row[5] or "",
    }


class EditorialRepository:
    def __init__(self, db):
        self.db = db

    # ---------- fuentes ----------

    def listar_fuentes(self) -> List[Dict[str, Any]]:
        rows = self.db.fetch_all(
            f"SELECT {_COLS_FUENTE} FROM editoriales_fuentes"
            " ORDER BY nombre") or []
        return [_fuente(r) for r in rows]

    def obtener_fuente(self, fuente_id: int) -> Optional[Dict[str, Any]]:
        row = self.db.fetch_one(
            f"SELECT {_COLS_FUENTE} FROM editoriales_fuentes WHERE id = ?",
            (fuente_id,))
        return _fuente(row) if row else None

    def insertar_fuente(self, nombre: str, plataforma: str, url: str,
                        nif: str = "", usuario: str = "",
                        password: str = "") -> int:
        cur = self.db.execute_query(
            "INSERT INTO editoriales_fuentes"
            " (nombre, plataforma, url, nif, usuario, password)"
            " VALUES (?,?,?,?,?,?)",
            (nombre, plataforma, url, nif, usuario, password))
        return cur.lastrowid if cur else 0

    def actualizar_fuente(self, fuente_id: int, nombre: str, plataforma: str,
                          url: str, nif: str, usuario: str,
                          password: str) -> None:
        self.db.execute_query(
            "UPDATE editoriales_fuentes SET nombre=?, plataforma=?, url=?,"
            " nif=?, usuario=?, password=? WHERE id=?",
            (nombre, plataforma, url, nif, usuario, password, fuente_id))

    def borrar_fuente(self, fuente_id: int) -> None:
        cur = self.db.execute_query(
            "DELETE FROM editoriales_fuentes WHERE id = ? AND NOT EXISTS"
            " (SELECT 1 FROM editoriales WHERE fuente_id = ? OR fuente_reserva_id = ?)",
            (fuente_id, fuente_id, fuente_id))
        if not cur.rowcount:
            raise ValueError("La fuente no existe o está en uso; actualiza la selección")

    def fuente_por_datos(self, plataforma: str, url: str,
                         usuario: str, password: str = "") -> Optional[Dict[str, Any]]:
        """La fuente que coincide en plataforma+url+usuario (para no
        duplicar el mismo portal al guardar fichas de editoriales)."""
        row = self.db.fetch_one(
            f"SELECT {_COLS_FUENTE} FROM editoriales_fuentes"
            " WHERE plataforma = ? AND url = ? AND COALESCE(usuario,'') = ?",
            (plataforma, url, usuario or ""))
        return _fuente(row) if row else None

    def borrar_fuentes_huerfanas(self) -> int:
        """Elimina fuentes que ya no usa ninguna editorial. Devuelve cuántas."""
        cur = self.db.execute_query(
            "DELETE FROM editoriales_fuentes WHERE id NOT IN"
            " (SELECT fuente_id FROM editoriales WHERE fuente_id IS NOT NULL"
            "  UNION SELECT fuente_reserva_id FROM editoriales"
            "  WHERE fuente_reserva_id IS NOT NULL)")
        return cur.rowcount if cur else 0

    # ---------- editoriales ----------

    def listar_editoriales(self) -> List[Dict[str, Any]]:
        rows = self.db.fetch_all(
            f"SELECT {_COLS_EDITORIAL} FROM editoriales ORDER BY nombre") or []
        return [_editorial(r) for r in rows]

    def obtener_editorial_por_nombre(self, nombre: str) -> Optional[Dict[str, Any]]:
        row = self.db.fetch_one(
            f"SELECT {_COLS_EDITORIAL} FROM editoriales"
            " WHERE nombre = ? COLLATE NOCASE",
            (nombre,))
        return _editorial(row) if row else None

    def obtener_editorial_por_id(self, editorial_id: int) -> Optional[Dict[str, Any]]:
        row = self.db.fetch_one(
            f"SELECT {_COLS_EDITORIAL} FROM editoriales WHERE id = ?",
            (editorial_id,))
        return _editorial(row) if row else None

    def editoriales_de_fuente(self, fuente_id: int) -> List[str]:
        rows = self.db.fetch_all(
            "SELECT nombre FROM editoriales WHERE fuente_id = ? ORDER BY nombre",
            (fuente_id,)) or []
        return [r[0] for r in rows]

    def usos_de_fuente(self, fuente_id: int) -> List[Dict[str, Any]]:
        rows = self.db.fetch_all(
            "SELECT id, nombre, fuente_id, fuente_reserva_id FROM editoriales"
            " WHERE fuente_id = ? OR fuente_reserva_id = ? ORDER BY nombre",
            (fuente_id, fuente_id)) or []
        return [{"id": r[0], "nombre": r[1], "principal": r[2] == fuente_id,
                 "reserva": r[3] == fuente_id} for r in rows]

    def insertar_editorial(self, nombre: str, fuente_id: Optional[int] = None,
                           web_buscar: str = "", web_dominio: str = "",
                           fuente_reserva_id: Optional[int] = None) -> int:
        cur = self.db.execute_query(
            "INSERT OR IGNORE INTO editoriales"
            " (nombre, fuente_id, fuente_reserva_id, web_buscar, web_dominio)"
            " VALUES (?,?,?,?,?)",
            (nombre, fuente_id, fuente_reserva_id, web_buscar, web_dominio))
        return cur.lastrowid if cur else 0

    def actualizar_editorial(self, editorial_id: int, nombre: str,
                             fuente_id: Optional[int], web_buscar: str,
                             web_dominio: str,
                             fuente_reserva_id: Optional[int] = None) -> None:
        self.db.execute_query(
            "UPDATE editoriales SET nombre=?, fuente_id=?,"
            " fuente_reserva_id=?, web_buscar=?, web_dominio=? WHERE id=?",
            (nombre, fuente_id, fuente_reserva_id, web_buscar, web_dominio,
             editorial_id))

    def enlazar_editoriales(self, fuente_id: int, nombres: List[str]) -> None:
        """Asigna `fuente_id` a los nombres dados (creándolos si faltan) y
        desvincula los que tenía la fuente y ya no están en la lista."""
        actuales = {n.lower() for n in self.editoriales_de_fuente(fuente_id)}
        nuevos = {n.strip().lower() for n in nombres if n and n.strip()}
        for nombre in nuevos:
            row = self.obtener_editorial_por_nombre(nombre)
            if row:
                self.db.execute_query(
                    "UPDATE editoriales SET fuente_id = ? WHERE id = ?",
                    (fuente_id, row["id"]))
            else:
                self.insertar_editorial(nombre, fuente_id)
        for viejo in actuales - nuevos:
            self.db.execute_query(
                "UPDATE editoriales SET fuente_id = NULL"
                " WHERE nombre = ? COLLATE NOCASE",
                (viejo,))

    def borrar_editorial(self, editorial_id: int) -> None:
        self.db.execute_query(
            "DELETE FROM editoriales WHERE id = ?", (editorial_id,))
