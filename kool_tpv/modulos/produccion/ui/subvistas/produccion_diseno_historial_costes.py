"""Subvista para mostrar el historial de costes y beneficios de un diseño específico.
Muestra una tabla con los costes de prenda, técnica, PVP y margen de beneficio.
"""
import logging
import tkinter as tk
from typing import Callable, Optional, List
from datetime import datetime

import customtkinter as ctk

from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.produccion.models.produccion_diseno_model import ProduccionDiseno
from kool_tpv.modulos.produccion.services.produccion_ordenes_service import ProduccionOrdenesService
from kool_tpv.modulos.produccion.services.variante_producto_service import VarianteProductoService
from kool_tpv.base_datos.producto_service import ProductoService
from kool_tpv.modulos.produccion.ui.subvistas.config_helper import cargar_config_produccion, get_font
from kool_tpv.utils.widgets.searchable_paginated_navlist import SearchablePaginatedNavList
from kool_tpv.base_datos.money_adapter import read_from_db
from kool_tpv.utils.factories.button_factory import ButtonFactory

class DisenoHistorialCostesView:
    def __init__(self, parent, db: Database, diseno: ProduccionDiseno, on_cerrar: Callable[[], None]):
        self.parent = parent
        self.db = db
        self.diseno = diseno
        self.on_cerrar = on_cerrar
        
        self.produccion_service = ProduccionOrdenesService(db)
        self.link_service = VarianteProductoService(db)
        self.producto_service = ProductoService(db)
        
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
        
    def _get_font(self, key: str) -> tuple:
        return get_font(self.config, key)
        
    def _crear_interfaz(self):
        # 1. CABECERA
        header = ctk.CTkFrame(self.frame, fg_color="transparent")
        header.pack(fill="x", padx=40, pady=(20, 10))
        
        btn_volver = ButtonFactory.create_button(
            header, text="VOLVER", width=100,
            command=self.on_cerrar,
            module="produccion",
            palette_key="primary",
            style_key="action_secondary"
        )
        btn_volver.pack(side="left")
        
        lbl_title = ctk.CTkLabel(
            header, 
            text=f"HISTORIAL DE COSTES: {self.diseno.codigo} - {self.diseno.nombre}",
            font=self._get_font("title_small"),
            text_color=self._accent
        )
        lbl_title.pack(side="left", padx=20)
        
        # 2. TABLA (NavList) - 85% del espacio vertical aproximado
        self.list_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        self.list_frame.pack(fill="both", expand=True, padx=40, pady=(10, 5))
        
        # Definición de columnas con iconos
        # 👕 € = Coste Prenda (variante)
        # 🎨 € = Coste Técnica (metodo)
        # €€ = Coste Total
        columns = [
            ("fecha", 80, "FECHA"),
            ("tipo", 100, "TIPO"),
            ("variante", 135, "VARIANTE"),
            ("coste_prenda", 65, "👕 €"),
            ("metodo", 100, "MÉTODO"),
            ("coste_tecnica", 65, "🎨 €"),
            ("extra_nombre", 110, "EXTRA"),
            ("extra_coste", 65, "➕ €"),
            ("coste_total", 80, "€€"),
            ("pvp", 80, "PVP"),
            ("margen", 80, "%%")
        ]
        
        from kool_tpv.utils.config_loader import load_layout_config
        root = self.frame.winfo_toplevel()
        _km = getattr(root, 'keyboard_manager', None)
        
        self._paginated_list = SearchablePaginatedNavList(
            parent=self.list_frame,
            columns=columns,
            search_function=self._cargar_datos,
            map_function=self._map_datos,
            module_name="produccion",
            page_limit=50,
            on_double_click=self._on_item_double_click,
            keyboard_manager=_km,
            layout_config=load_layout_config()
        )
        self._paginated_list.pack(fill="both", expand=True)

        # 3. ZONA DE EDICIÓN (15% del espacio)
        edit_bg = self.mod_colors.get("bg_dark", "#1a1a2e")
        self.edit_frame = ctk.CTkFrame(self.frame, height=120, fg_color=edit_bg)
        self.edit_frame.pack(fill="x", padx=40, pady=(5, 20))
        self.edit_frame.pack_propagate(False) # Mantener altura fija para el 15%
        
        self._crear_zona_edicion()

    def _crear_zona_edicion(self):
        """Crear los widgets para la edición rápida del coste del método."""
        for w in self.edit_frame.winfo_children():
            w.destroy()
            
        title_edit = ctk.CTkLabel(
            self.edit_frame, 
            text="EDICIÓN RÁPIDA DE COSTE DE MÉTODO",
            font=self._get_font("label"),
            text_color=self._text_sec
        )
        title_edit.pack(anchor="w", padx=20, pady=(5, 0))
        
        inputs_row = ctk.CTkFrame(self.edit_frame, fg_color="transparent")
        inputs_row.pack(fill="x", padx=20, pady=10)
        
        # Datos informativos
        self._lbl_info_edit = ctk.CTkLabel(
            inputs_row, text="Doble clic en una línea para editar el coste del método...",
            font=self._get_font("label"),
            text_color=self._accent
        )
        self._lbl_info_edit.pack(side="left", padx=(0, 20))
        
        # Entry para el nuevo coste
        self._entry_nuevo_coste = ctk.CTkEntry(
            inputs_row, width=120,
            placeholder_text="0.00",
            font=self._get_font("entry"),
            justify="right"
        )
        self._entry_nuevo_coste.pack(side="left", padx=10)
        self._entry_nuevo_coste.bind("<Return>", lambda e: self._guardar_nuevo_coste())
        
        self._btn_guardar_edit = ButtonFactory.create_button(
            inputs_row, text="ACTUALIZAR COSTE",
            width=150,
            command=self._guardar_nuevo_coste,
            module="produccion",
            palette_key="primary",
            style_key="action_confirm"
        )
        self._btn_guardar_edit.configure(state="disabled")
        self._btn_guardar_edit.pack(side="left", padx=10)
        
        # Estado de edición actual
        self._item_en_edicion = None

    def _on_item_double_click(self, item_data: dict):
        """Al hacer doble clic, cargar el ítem en la zona de edición."""
        self._item_en_edicion = item_data
        
        # Actualizar info
        metodo = item_data.get("metodo", "-")
        tipo = item_data.get("tipo", "")
        variante = item_data.get("variante", "")
        self._lbl_info_edit.configure(
            text=f"EDITANDO: {metodo} ({tipo} - {variante})",
            text_color="#ecf0f1"
        )
        
        # Cargar coste actual
        coste_str = item_data.get("coste_tecnica", "0.00€").replace("€", "")
        self._entry_nuevo_coste.delete(0, tk.END)
        self._entry_nuevo_coste.insert(0, coste_str)
        
        # Habilitar botón
        self._btn_guardar_edit.configure(state="normal")
        self._entry_nuevo_coste.focus_set()

    def _guardar_nuevo_coste(self):
        """Guardar el nuevo coste del método para el diseño."""
        if not self._item_en_edicion:
            return
            
        try:
            nuevo_coste = float(self._entry_nuevo_coste.get().replace(",", "."))
            metodo_id = self._item_en_edicion.get("_metodo_id")
            tipo_id = self._item_en_edicion.get("_tipo_id")
            variante_id = self._item_en_edicion.get("_variante_id")
            
            if not metodo_id:
                from kool_tpv.utils.widgets.notificaciones.toast_widget import ToastWidget
                ToastWidget.show(self.frame, "Este ítem no tiene un método válido", tipo="error")
                return
            
            from kool_tpv.modulos.produccion.repositories.produccion_metodos_repository import ProduccionMetodosRepository
            from kool_tpv.base_datos.money_adapter import prepare_for_db
            
            repo = ProduccionMetodosRepository(self.db)
            repo.guardar_coste_diseno(
                self.diseno.codigo,
                metodo_id,
                prepare_for_db(nuevo_coste),
                tipo_id=tipo_id,
                variante_id=variante_id
            )
            
            from kool_tpv.utils.widgets.notificaciones.toast_widget import ToastWidget
            ToastWidget.show(self.frame, "Coste actualizado correctamente", tipo="success")
            
            # Limpiar edición
            self._crear_zona_edicion()
            
            # Refrescar lista
            self._paginated_list.search("")
            
        except ValueError:
            from kool_tpv.utils.widgets.notificaciones.toast_widget import ToastWidget
            ToastWidget.show(self.frame, "Introduce un número válido", tipo="warning")
        
    def _cargar_datos(self, filtro: str) -> List[dict]:
        """Obtener líneas de producción del diseño y cruzar con costes actuales y PVP."""
        try:
            # 1. Obtener líneas de producción filtradas por el código del diseño
            query = """
                SELECT 
                    o.fecha_hora,
                    t.nombre as tipo,
                    v.nombre as variante,
                    l.coste_unitario,
                    l.metodo_id,
                    m.nombre as metodo_nombre,
                    l.variante_id,
                    l.tipo_id,
                    l.extra_coste,
                    e.nombre as extra_nombre
                FROM produccion_lineas l
                JOIN produccion_ordenes o ON l.orden_id = o.id
                JOIN tipos t ON l.tipo_id = t.id
                LEFT JOIN tipos_variantes v ON l.variante_id = v.id
                LEFT JOIN produccion_metodos m ON l.metodo_id = m.id
                LEFT JOIN produccion_extras e ON l.extra_id = e.id
                WHERE l.diseno_codigo = ?
                ORDER BY o.fecha_hora DESC
            """
            rows = self.db.fetch_all(query, (self.diseno.codigo,))
            
            # Repositorio para consultar costes de base reales
            from kool_tpv.modulos.produccion.repositories.produccion_stock_base_repository import ProduccionStockBaseRepository
            repo_base = ProduccionStockBaseRepository(self.db)
            
            resultados = []
            for row in rows:
                fecha, tipo, variante, c_unitario, m_id, m_nombre, v_id, t_id, extra_c, extra_nombre = row
                
                # A. PVP ACTUAL
                pvp_actual = 0.0
                if v_id:
                    link = self.link_service.get_por_combinacion(v_id)
                    if link and link.producto_id:
                        prod = self.producto_service.get_producto_completo(link.producto_id)
                        if prod:
                            pvp_actual = float(prod.get('pvp', 0))
                
                # B. COSTE PRENDA ACTUAL (BASE)
                # Consultamos lo que nos cuesta la prenda blanca hoy en stock
                coste_prenda = 0.0
                stock_base = repo_base.get_by_params(t_id, None, None, v_id)
                if stock_base:
                    coste_prenda = float(read_from_db(stock_base.get('coste_medio', 0)))
                else:
                    # Si no hay stock base configurado, intentamos estimar del unitario
                    coste_prenda = float(read_from_db(c_unitario)) * 0.7 # fallback 70%
                
                # C. COSTE TÉCNICA ACTUAL (MÉTODO)
                coste_tecnica = 0.0
                if self.diseno.codigo and m_id:
                    # Buscar coincidencia más específica en la configuración del diseño
                    q_met = """
                        SELECT coste FROM produccion_disenos_metodos 
                        WHERE diseno_codigo = ? AND metodo_id = ?
                        AND (
                            (variante_id = ? AND tipo_id = ?) OR
                            (variante_id IS NULL AND tipo_id = ?) OR
                            (variante_id IS NULL AND tipo_id IS NULL)
                        )
                        ORDER BY variante_id DESC, tipo_id DESC
                        LIMIT 1
                    """
                    r_met = self.db.fetch_one(q_met, (self.diseno.codigo, m_id, v_id, t_id, t_id))
                    if r_met:
                        coste_tecnica = float(read_from_db(r_met[0]))
                
                # D. COSTE TOTAL PROYECTADO
                # Sumamos los costes actuales + los extras que tuvo esa línea en su día
                extra_c_val = float(read_from_db(extra_c))
                coste_total = coste_prenda + coste_tecnica + extra_c_val
                
                # E. MARGEN PROYECTADO
                margen = 0.0
                if pvp_actual > 0:
                    margen = ((pvp_actual - coste_total) / pvp_actual) * 100
                
                resultados.append({
                    "fecha": fecha,
                    "tipo": tipo,
                    "variante": variante or "-",
                    "coste_prenda": coste_prenda,
                    "metodo": m_nombre or "-",
                    "_metodo_id": m_id,
                    "_tipo_id": t_id,
                    "_variante_id": v_id,
                    "coste_tecnica": coste_tecnica,
                    "extra_nombre": extra_nombre or "-",
                    "extra_coste": extra_c_val,
                    "coste_total": coste_total,
                    "pvp": pvp_actual,
                    "margen": margen
                })
            
            return resultados
        except Exception:
            logging.exception("Error cargando historial de costes")
            return []
            
    def _map_datos(self, r: dict) -> dict:
        """Formatear datos para la NavList."""
        try:
            dt = datetime.fromisoformat(str(r["fecha"]))
            fecha_str = dt.strftime("%d-%m-%y")
        except:
            fecha_str = str(r["fecha"])
            
        return {
            "_metodo_id": r.get("_metodo_id"),
            "_tipo_id": r.get("_tipo_id"),
            "_variante_id": r.get("_variante_id"),
            "fecha": fecha_str,
            "tipo": r["tipo"],
            "variante": r["variante"],
            "coste_prenda": f"{r['coste_prenda']:.2f}€",
            "metodo": r["metodo"],
            "coste_tecnica": f"{r['coste_tecnica']:.2f}€",
            "extra_nombre": r["extra_nombre"],
            "extra_coste": f"{r['extra_coste']:.2f}€" if r['extra_coste'] > 0 else "-",
            "coste_total": f"{r['coste_total']:.2f}€",
            "pvp": f"{r['pvp']:.2f}€" if r['pvp'] > 0 else "-",
            "margen": f"{r['margen']:.1f}%" if r['pvp'] > 0 else "-"
        }
