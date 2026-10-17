"""Servicio de fuentes de datos de editoriales (manga/cómics).

Los datos viven en las tablas `editoriales_fuentes` y `editoriales` (creadas
por la migración 062). Una fuente = el sitio que responde (plataforma -> qué
clase
de `services/fuentes/` lo atiende) + URL + credenciales. Una editorial = un
nombre que puede llevar el campo Editorial del producto, enlazado a su
fuente y con su web para el botón IR.

Sin SQL aquí: eso es del `EditorialRepository`.
"""
import logging
from typing import Any, Dict, List, Optional

from kool_tpv.modulos.almacen.editorial_repository import EditorialRepository

logger = logging.getLogger(__name__)


class FuentesEditorialService:
    """Lógica de resolución editorial -> fuente + web del IR."""

    def __init__(self, db):
        self.db = db
        self.repo = EditorialRepository(db)

    # ---------- fuentes ----------

    def listar_fuentes(self) -> List[Dict[str, Any]]:
        """Fuentes con su lista de editoriales cubiertas."""
        fuentes = self.repo.listar_fuentes()
        for f in fuentes:
            f["editoriales"] = self.repo.editoriales_de_fuente(f["id"])
        return fuentes

    def fuente_por_id(self, fuente_id: int) -> Optional[Dict[str, Any]]:
        return self.repo.obtener_fuente(fuente_id)

    def guardar_fuente(self, datos: Dict[str, Any],
                       fuente_id: Optional[int] = None) -> int:
        """Crea o actualiza una fuente y enlaza sus editoriales.
        `editoriales` puede ser lista o texto separado por comas.
        Devuelve el id de la fuente."""
        nombre = (datos.get("nombre") or "").strip()
        plataforma = (datos.get("plataforma") or datos.get("tipo") or "").strip()
        if not nombre or not plataforma:
            raise ValueError("La fuente necesita nombre y plataforma")
        if fuente_id:
            self.repo.actualizar_fuente(
                fuente_id, nombre, plataforma, (datos.get("url") or "").strip(),
                datos.get("nif") or "", datos.get("usuario") or "",
                datos.get("password") or "")
        else:
            fuente_id = self.repo.insertar_fuente(
                nombre, plataforma, (datos.get("url") or "").strip(),
                datos.get("nif") or "", datos.get("usuario") or "",
                datos.get("password") or "")
        editoriales = datos.get("editoriales") or []
        if isinstance(editoriales, str):
            editoriales = [e.strip() for e in editoriales.split(",")]
        self.repo.enlazar_editoriales(fuente_id, editoriales)
        return fuente_id

    def borrar_fuente(self, fuente_id: int) -> None:
        """Elimina la fuente; sus editoriales quedan sin fuente (se conservan
        para el IR)."""
        self.repo.borrar_fuente(fuente_id)

    def editoriales_que_usan_portal(self, fuente_id: int) -> List[str]:
        """Nombres de las editoriales que cubre una fuente."""
        return self.repo.editoriales_de_fuente(fuente_id)

    # ---------- resolución ----------

    def fuente_para_editorial(self, texto_editorial: str) -> Optional[Dict[str, Any]]:
        """La fuente principal que cubre una editorial (para PROBAR)."""
        fuentes = self.fuentes_para_editorial(texto_editorial)
        return fuentes[0] if fuentes else None

    def fuentes_para_editorial(self, texto_editorial: str) -> List[Dict[str, Any]]:
        """Fuentes que cubren una editorial: [principal, reserva si la hay].
        Coincidencia exacta del nombre primero; si no, el nombre de
        editorial contenido en el texto."""
        texto = (texto_editorial or "").strip().lower()
        if not texto:
            return []
        editoriales = self.repo.listar_editoriales()
        elegida = None
        for ed in editoriales:
            if ed["nombre"].lower() == texto:
                elegida = ed
                break
            if elegida is None and ed["nombre"].lower() in texto:
                elegida = ed
        if not elegida:
            return []
        salida = []
        for fid in (elegida.get("fuente_id"), elegida.get("fuente_reserva_id")):
            if not fid or any(f["id"] == fid for f in salida):
                continue
            fuente = self.repo.obtener_fuente(fid)
            if fuente:
                salida.append(fuente)
        return salida

    def web_para_editorial(self, texto_editorial: str, consulta: str) -> str:
        """URL que abre el botón IR: 'web_buscar' de la editorial, o Google
        con site:su dominio, o Google a secas con 'editorial <nombre>'."""
        from urllib.parse import quote_plus
        q = quote_plus(consulta or "")
        texto = (texto_editorial or "").strip().lower()
        for ed in self.repo.listar_editoriales():
            if ed["nombre"].lower() == texto or ed["nombre"].lower() in texto:
                if ed.get("web_buscar"):
                    return ed["web_buscar"].replace("{q}", q)
                if ed.get("web_dominio"):
                    return f"https://www.google.com/search?q={q}+site%3A{ed['web_dominio']}"
        extra = f" editorial {texto_editorial.strip()}" if texto_editorial else ""
        return f"https://www.google.com/search?q={q}{quote_plus(extra)}"

    # ---------- fichas (vista de la UI: editorial + su fuente) ----------

    def listar_fichas(self) -> List[Dict[str, Any]]:
        """Cada editorial con los datos de su fuente embebidos, para la UI."""
        fichas = []
        for ed in self.repo.listar_editoriales():
            ficha = dict(ed)
            fuente = (self.repo.obtener_fuente(ed["fuente_id"])
                      if ed.get("fuente_id") else None) or {}
            ficha["fuente"] = fuente
            ficha["fuente_reserva"] = (
                self.repo.obtener_fuente(ed["fuente_reserva_id"])
                if ed.get("fuente_reserva_id") else {}) or {}
            fichas.append(ficha)
        return fichas

    def guardar_ficha(self, datos: Dict[str, Any],
                      editorial_id: Optional[int] = None) -> int:
        """Guarda la ficha de una editorial: nombre, web y su fuente.
        La fuente se reutiliza si ya existe una con la misma
        plataforma+url+usuario; si no, se crea — así editar el chip de una
        editorial nunca rompe a otra que comparta fuente."""
        nombre = (datos.get("nombre") or "").strip().lower()
        if not nombre:
            raise ValueError("La editorial necesita un nombre")
        plataforma = (datos.get("plataforma") or "").strip()
        fuente_id = None
        if plataforma and plataforma != "web":
            url = (datos.get("url") or "").strip()
            usuario = (datos.get("usuario") or "").strip()
            existente = self.repo.fuente_por_datos(
                plataforma, url, usuario, datos.get("password") or "")
            if existente:
                fuente_id = existente["id"]
                self.repo.actualizar_fuente(
                    fuente_id, datos.get("fuente_nombre") or existente["nombre"],
                    plataforma, url, datos.get("nif") or existente["nif"],
                    usuario, datos.get("password") or existente["password"])
            else:
                fuente_id = self.repo.insertar_fuente(
                    datos.get("fuente_nombre") or url or plataforma,
                    plataforma, url, datos.get("nif") or "",
                    usuario, datos.get("password") or "")
        reserva_id = datos.get("fuente_reserva_id") or None
        if editorial_id:
            actual = self.repo.obtener_editorial_por_id(editorial_id) or {}
            web_buscar = datos.get("web_buscar", actual.get("web_buscar", ""))
            web_dominio = datos.get("web_dominio", actual.get("web_dominio", ""))
            self.repo.actualizar_editorial(
                editorial_id, nombre, fuente_id, web_buscar, web_dominio,
                fuente_reserva_id=reserva_id)
        else:
            editorial_id = self.repo.insertar_editorial(
                nombre, fuente_id, datos.get("web_buscar") or "",
                datos.get("web_dominio") or "",
                fuente_reserva_id=reserva_id)
        self.repo.borrar_fuentes_huerfanas()
        return editorial_id

    # ---------- editoriales (filas sueltas, para el IR) ----------

    def listar_editoriales(self) -> List[Dict[str, Any]]:
        return self.repo.listar_editoriales()

    def guardar_editorial(self, nombre: str, fuente_id: Optional[int] = None,
                          web_buscar: str = "", web_dominio: str = "") -> int:
        nombre = (nombre or "").strip().lower()
        if not nombre:
            raise ValueError("La editorial necesita un nombre")
        existente = self.repo.obtener_editorial_por_nombre(nombre)
        if existente:
            self.repo.actualizar_editorial(
                existente["id"], nombre, fuente_id, web_buscar, web_dominio,
                fuente_reserva_id=existente.get("fuente_reserva_id"))
            return existente["id"]
        return self.repo.insertar_editorial(nombre, fuente_id, web_buscar,
                                            web_dominio)

    def borrar_editorial(self, editorial_id: int) -> None:
        self.repo.borrar_editorial(editorial_id)
        self.repo.borrar_fuentes_huerfanas()
