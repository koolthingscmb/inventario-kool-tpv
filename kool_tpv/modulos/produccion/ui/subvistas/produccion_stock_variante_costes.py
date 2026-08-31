"""Subvista para consultar los costes base configurados por cada variante de producto.
Muestra una tabla con el Tipo de producto, el nombre de la variante y su coste base.
"""
import logging
from typing import Callable, List, Dict, Any

import customtkinter as ctk

from kool_tpv.utils.factories.button_factory import ButtonFactory
from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.produccion.ui.subvistas.config_helper import cargar_config_produccion, get_font
from kool_tpv.utils.widgets.searchable_paginated_navlist import SearchablePaginatedNavList
from kool_tpv.modulos.produccion.services.produccion_tipos_variantes_service import ProduccionTiposVariantesService

logger = logging.getLogger(__name__)

class ProduccionStockVarianteCostesView:
    def __init__(self, parent, db: Database, on_cerrar: Callable[[], None]):
        self.parent = parent
        self.db = db
        self.on_cerrar = on_cerrar
        self.service = ProduccionTiposVariantesService(db)
        
        # Cargar configuración
        self.config = cargar_config_produccion()
        self._colors = self.config.get("colors", {})
        
        # Intentar cargar colores específicos del módulo producción
        from kool_tpv.utils.config_loader import load_colors
        self.mod_colors = load_colors("produccion")
        
        self._bg = self.mod_colors.get("background", self._colors.get("background", "#2c3e50"))
        self._text = self.mod_colors.get("text", self._colors.get("text", "#ecf0f1"))
        self._text_sec = self.mod_colors.get("text_secondary", self._colors.get("text_secondary", "#95a5a6"))
        self._accent = self.mod_colors.get("secondary", "#C77BFF")
        
        # Frame principal
        self.frame = ctk.CTkFrame(parent, fg_color=self._bg)
        self.frame.pack(fill="both", expand=True)
        
        self._crear_interfaz()
        
        # Vincular botón Power/Esc
        self.frame._volver = self.on_cerrar
        
    def _get_font(self, key: str) -> tuple:
        return get_font(self.config, key)
        
    def _crear_interfaz(self):
        # 1. CABECERA
        header = ctk.CTkFrame(self.frame, fg_color="transparent")
        header.pack(fill="x", padx=40, pady=(20, 10))
        
        btn_volver = ButtonFactory.create_button(
            header, text="VOLVER", 
            command=self.on_cerrar,
            module="produccion",
            palette_key="primary",
            style_key="action_secondary"
        )
        btn_volver.pack(side="left")
        
        lbl_title = ctk.CTkLabel(
            header, 
            text="CONSULTA DE COSTES POR VARIANTE",
            font=self._get_font("title_small"),
            text_color=self._accent
        )
        lbl_title.pack(side="left", padx=20)
        
        # 2. TABLA (SearchablePaginatedNavList)
        self.list_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        self.list_frame.pack(fill="both", expand=True, padx=40, pady=(10, 20))
        
        columns = [
            ("tipo", 200, "TIPO"),
            ("variante", 300, "VARIANTE"),
            ("coste", 150, "COSTE (€)")
        ]
        
        root = self.frame.winfo_toplevel()
        _km = getattr(root, 'keyboard_manager', None)
        
        self._paginated_list = SearchablePaginatedNavList(
            parent=self.list_frame,
            columns=columns,
            search_function=self._cargar_datos,
            map_function=self._map_datos,
            module_name="produccion",
            keyboard_manager=_km
        )
        self._paginated_list.pack(fill="both", expand=True)

    def _cargar_datos(self, search_term: str = "") -> List[Dict[str, Any]]:
        """Cargar datos usando el servicio."""
        return self.service.listar_variantes_con_coste(search_term)

    def _map_datos(self, r: Dict[str, Any]) -> Dict[str, Any]:
        """Mapear datos para la NavList."""
        return {
            "tipo": r["tipo"],
            "variante": r["variante"],
            "coste": f"{r['coste']:.2f}€"
        }

    def destruir(self):
        """Limpiar recursos."""
        if self.frame.winfo_exists():
            self.frame.destroy()
