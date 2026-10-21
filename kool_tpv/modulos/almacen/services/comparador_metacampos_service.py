"""Compara palabras candidatas de las fuentes con los metacampos de cómic.

Las fuentes editoriales no tienen un campo 'género' formal, pero traen
categorías, tags y materias donde a veces aparece ('Terror', 'Seinen'...).
Este servicio coteja esas palabras — solo campos estructurados, nunca la
sinopsis — contra las listas reales de los metacampos en Shopify.

Reglas:
- Comparación exacta tras normalizar (sin acentos, sin mayúsculas).
- Primero se consulta la tabla de equivalencias `metacampos_alias.json`
  para variantes editoriales ('misterio' -> 'Suspense').
- Demografía admite un solo valor (gana el primero); el resto son listas.
- Devuelve también las 'pruebas': qué palabra produjo cada asignación.
"""
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from kool_tpv.modulos.almacen.services.metacampos_comic_service import (
    MetacamposComicService,
)
from kool_tpv.paths import CONFIG_DIR

logger = logging.getLogger(__name__)

_SEPARADORES = (">", "/", "|", ";")


class ComparadorMetacamposService:
    """Mapea candidatos de las fuentes a valores oficiales de metacampos."""

    def __init__(self, db):
        self._svc = MetacamposComicService(db)
        self._listas: Optional[Dict[str, Dict[str, str]]] = None
        self._alias: Optional[Dict[str, str]] = None

    # ---------- listas oficiales ----------

    def _cargar_listas(self) -> Optional[str]:
        """{clave: {normalizado: nombre oficial}} una vez por sesión."""
        if self._listas is not None:
            return None
        opciones, err = self._svc.obtener_opciones()
        if err:
            logger.warning("Comparador sin listas de Shopify: %s", err)
            self._listas = {}
            return err
        self._listas = {
            clave: {
                MetacamposComicService.normalizar(e.get("nombre")): e.get("nombre")
                for e in datos.get("entradas") or []
            }
            for clave, datos in (opciones or {}).items()
        }
        return None

    def _cargar_alias(self) -> Dict[str, str]:
        """Variante editorial -> nombre oficial, desde la config."""
        if self._alias is not None:
            return self._alias
        self._alias = {}
        try:
            ruta = CONFIG_DIR / "metacampos_alias.json"
            if ruta.exists():
                datos = json.loads(ruta.read_text(encoding="utf-8"))
                self._alias = {
                    MetacamposComicService.normalizar(k): str(v)
                    for k, v in (datos or {}).items()
                }
        except Exception:
            logger.exception("No se pudo leer metacampos_alias.json")
        return self._alias

    # ---------- comparación ----------

    @staticmethod
    def _trocear(candidatos: List[str]) -> List[str]:
        """Un campo como 'MANGA > SMILEY' aporta dos candidatos."""
        trozos: List[str] = []
        for c in candidatos or []:
            texto = str(c or "").strip()
            if not texto:
                continue
            partes = [texto]
            for sep in _SEPARADORES:
                partes = [p for trozo in partes for p in trozo.split(sep)]
            trozos.extend(p.strip() for p in partes if p.strip())
        return trozos

    def comparar(self, candidatos: List[str],
                 listas: Optional[Dict[str, Dict[str, str]]] = None,
                 ) -> Dict[str, Any]:
        """Devuelve {'metacampos': {clave: valor}, 'pruebas': [...], 'error': ...}.

        `listas` ({clave: {normalizado: nombre}}) es inyectable para probar
        sin Shopify; si no se pasa, se piden una vez y se cachean.
        """
        error = None
        if listas is None:
            error = self._cargar_listas()
            listas = self._listas or {}
        if not listas:
            return {"metacampos": {}, "pruebas": [], "error": error}

        alias = self._cargar_alias()
        metacampos: Dict[str, Any] = {}
        pruebas: List[str] = []

        for trozo in self._trocear(candidatos):
            norm = MetacamposComicService.normalizar(trozo)
            if not norm:
                continue
            # la variante editorial apunta al nombre oficial antes de comparar
            buscar = alias.get(norm)
            if buscar:
                norm_buscado = MetacamposComicService.normalizar(buscar)
            else:
                norm_buscado = norm

            for clave, titulo, unico in MetacamposComicService.GRUPOS:
                oficial = (listas.get(clave) or {}).get(norm_buscado)
                if not oficial:
                    continue
                if unico:
                    if clave not in metacampos:
                        metacampos[clave] = oficial
                        pruebas.append(f"{titulo} ← '{oficial}' (de '{trozo}')")
                else:
                    lista = metacampos.setdefault(clave, [])
                    if oficial not in lista:
                        lista.append(oficial)
                        pruebas.append(f"{titulo} ← '{oficial}' (de '{trozo}')")

        return {"metacampos": metacampos, "pruebas": pruebas, "error": error}
