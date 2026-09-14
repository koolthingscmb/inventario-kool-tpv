import tkinter as tk
import customtkinter as ctk
import logging
import threading
from typing import Dict, Any, List, Optional

from kool_tpv.utils.factories.button_factory import ButtonFactory
from kool_tpv.utils.config_loader import load_colors
from kool_tpv.utils.widgets.notificaciones import show_success, show_error
from kool_tpv.modulos.shopify.services.shopify_sync_service import ShopifySyncService
from kool_tpv.modulos.produccion.services.produccion_stock_base_service import ProduccionStockBaseService
from kool_tpv.utils.widgets.searchable_combo import SearchableCombo

logger = logging.getLogger(__name__)

class ShopifySyncView(ctk.CTkFrame):
    """Vista principal para la sincronización manual de stock por categorías."""

    def __init__(self, parent, db):
        # Cargar colores del módulo Shopify para unificar diseño
        try:
            self.colors = load_colors('shopify')
            self._tab_bg_selected = self.colors.get('buttons', {}).get('primary', {}).get('bg', '#00A4DF')
            self._tab_bg_normal = self.colors.get('buttons', {}).get('secondary', {}).get('bg', '#3498db')
            self._tab_text_selected = self.colors.get('buttons', {}).get('primary', {}).get('text', '#FFFFFF')
            self._tab_text_normal = self.colors.get('buttons', {}).get('secondary', {}).get('text', '#FFFFFF')
        except Exception:
            self.colors = {}
            self._tab_bg_selected = '#00A4DF'
            self._tab_bg_normal = '#3498db'
            self._tab_text_selected = '#FFFFFF'
            self._tab_text_normal = '#FFFFFF'

        bg_color = self.colors.get('background', '#000000')
        super().__init__(parent, fg_color=bg_color, corner_radius=0)
        
        self.db = db
        self.sync_service = ShopifySyncService(db)
        self.stock_service = ProduccionStockBaseService(db)
        self.sync_thread = None
        self.is_syncing = False
        self._current_tab = None
        self._tab_labels = {}

        self._init_ui()

    def _init_ui(self):
        """Construye la interfaz de sincronización con pestañas."""
        # --- 1. HEADER ---
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=30, pady=(20, 10))
        
        primary_color = self.colors.get('primary', '#00A4DF')
        
        title_lbl = ctk.CTkLabel(
            header_frame, text="SINCRONIZACIÓN DE TIENDA ONLINE",
            font=("Roboto-Bold", 22), text_color=primary_color
        )
        title_lbl.pack(side="left")

        # --- 2. BARRA DE PESTAÑAS ---
        self.tab_bar = tk.Frame(self, bg=self.colors.get('background', '#000000'), height=40)
        self.tab_bar.pack(fill="x", padx=30, pady=(0, 10))
        self.tab_bar.pack_propagate(False)

        tabs = [("ACTUALIZAR", self._show_tab_actualizar), ("LOGS", self._show_tab_logs)]
        for name, callback in tabs:
            lbl = tk.Label(
                self.tab_bar, text=name, font=("Helvetica", 10, "bold"),
                fg=self._tab_text_normal, bg=self._tab_bg_normal,
                padx=20, pady=8, cursor="hand2"
            )
            lbl.pack(side="left", padx=(0, 5))
            lbl.bind("<Button-1>", lambda e, cb=callback, n=name: self._select_tab(n, cb))
            self._tab_labels[name] = lbl

        # --- 3. ÁREA DE CONTENIDO ---
        self.content_area = ctk.CTkFrame(self, fg_color="transparent")
        self.content_area.pack(fill="both", expand=True, padx=30)

        # Seleccionar primera pestaña
        self._select_tab("ACTUALIZAR", self._show_tab_actualizar)

    def _select_tab(self, tab_name: str, callback: callable):
        """Cambia entre pestañas de sincronización."""
        if self._current_tab == tab_name:
            return
        
        # Actualizar visual
        for name, lbl in self._tab_labels.items():
            if name == tab_name:
                lbl.configure(bg=self._tab_bg_selected, fg=self._tab_text_selected)
            else:
                lbl.configure(bg=self._tab_bg_normal, fg=self._tab_text_normal)
        
        self._current_tab = tab_name
        
        # Limpiar área
        for child in self.content_area.winfo_children():
            child.destroy()
        
        callback()

    def _show_tab_actualizar(self):
        """Muestra el panel de actualización manual."""
        primary_color = self.colors.get('primary', '#00A4DF')
        
        # --- FILTROS ---
        filters_frame = ctk.CTkFrame(self.content_area, fg_color=self.colors.get('bg_medium', '#1a1a1a'), corner_radius=10)
        filters_frame.pack(fill="x", pady=(0, 15), ipady=8)
        
        ctk.CTkLabel(filters_frame, text="FILTRAR POR:", font=("Roboto-Bold", 13), text_color=primary_color).pack(side="left", padx=15)
        
        try:
            from kool_tpv.modulos.produccion.services.produccion_colores_service import ProduccionColoresService
            from kool_tpv.modulos.produccion.services.produccion_tipos_variantes_service import ProduccionTiposVariantesService
            
            colores = ProduccionColoresService(self.db).obtener_como_dict(solo_activos=True)
            variantes_dict = ProduccionTiposVariantesService(self.db).obtener_activos_como_dict()
            
            options_colores = [(None, "TODOS LOS COLORES")] + [(c['id'], c['nombre'].upper()) for c in colores]
            options_variantes = [(None, "TODOS LOS GÉNEROS")] + [(vid, nom.upper()) for vid, nom in variantes_dict.items()]
        except Exception:
            options_colores = [(None, "TODOS LOS COLORES")]
            options_variantes = [(None, "TODOS LOS GÉNEROS")]

        self.cb_color = SearchableCombo(filters_frame, options=options_colores, placeholder="COLOR...", width=200, module_name="shopify")
        self.cb_color.pack(side="left", padx=8)
        
        self.cb_variante = SearchableCombo(filters_frame, options=options_variantes, placeholder="GÉNERO/VARIANTE...", width=200, module_name="shopify")
        self.cb_variante.pack(side="left", padx=8)

        # --- BOTONES CATEGORÍA ---
        categories = [
            {"id": 1, "name": "CAMISETAS", "active": True},
            {"id": 5, "name": "CALCETINES", "active": False},
            {"id": 37, "name": "SUDADERAS", "active": False},
            {"id": 29, "name": "PANTALONES", "active": False},
        ]

        self.category_buttons = {}
        for cat in categories:
            btn_frame = ctk.CTkFrame(self.content_area, fg_color=self.colors.get('bg_medium', '#1a1a1a'), corner_radius=10)
            btn_frame.pack(fill="x", pady=5, ipady=8)
            
            name_lbl = ctk.CTkLabel(btn_frame, text=cat["name"], font=("Roboto-Bold", 16), text_color="#FFFFFF")
            name_lbl.pack(side="left", padx=20)

            if cat["active"]:
                btn = ButtonFactory.create_button(
                    btn_frame, text="ACTUALIZAR EN TIENDA",
                    command=lambda c=cat: self._on_sync_category(c),
                    style_key="action_confirm", module="shopify", palette_key="primary",
                    width=200, height=35
                )
                self.category_buttons[cat["id"]] = btn
            else:
                btn = ctk.CTkButton(
                    btn_frame, text="PRÓXIMAMENTE",
                    state="disabled", fg_color="#333333", text_color="#666666",
                    width=200, height=35, corner_radius=10
                )
            btn.pack(side="right", padx=20)

        # Espacio debajo para el futuro
        spacer = ctk.CTkFrame(self.content_area, fg_color="transparent")
        spacer.pack(fill="both", expand=True)

    def _show_tab_logs(self):
        """Muestra el historial permanente de sincronización en formato terminal."""
        # --- CONSOLA DE LOGS GRANDE ---
        self.log_text = ctk.CTkTextbox(
            self.content_area, 
            fg_color="#0a0a0a", text_color="#00FF00", 
            font=("Consolas", 12), border_width=1, border_color="#333333"
        )
        self.log_text.pack(fill="both", expand=True, pady=(0, 10))
        
        # Botones de acción para logs
        footer_logs = ctk.CTkFrame(self.content_area, fg_color="transparent")
        footer_logs.pack(fill="x")
        
        ButtonFactory.create_button(
            footer_logs, text="REFRESCAR", 
            command=self._refresh_logs_data,
            style_key="mini_action", module="shopify", palette_key="secondary"
        ).pack(side="left")
        
        ButtonFactory.create_button(
            footer_logs, text="LIMPIAR HISTORIAL", 
            command=self._on_clear_logs_ui,
            style_key="mini_action", module="shopify", palette_key="accent"
        ).pack(side="right")

        self._refresh_logs_data()

    def _refresh_logs_data(self):
        """Carga los logs reales de la base de datos en la terminal."""
        if not hasattr(self, 'log_text') or not self.log_text.winfo_exists(): return
        
        logs = self.sync_service.config_service.get_logs(limit=200)
        
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        
        if not logs:
            self.log_text.insert("end", "> No hay historial de sincronización.\n")
        else:
            for l in reversed(logs): # De más antiguo a más nuevo para que el final sea lo último
                fecha = l["fecha"]
                accion = l["accion"]
                resultado = l["resultado"].upper()
                mensaje = l["mensaje"]
                
                prefix = "[OK]" if l["resultado"] == "success" else "[ERROR]"
                line = f"{fecha} {prefix} {accion}: {mensaje}\n"
                self.log_text.insert("end", line)
        
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _on_clear_logs_ui(self):
        if self.sync_service.config_service.clear_logs():
            show_success(self, "Historial de sincronización borrado.")
            self._refresh_logs_data()

    def _add_log(self, message):
        """Añade un mensaje a la consola visual."""
        if not hasattr(self, 'log_text'): return
        def _append():
            self.log_text.configure(state="normal")
            self.log_text.insert("end", f"> {message}\n")
            self.log_text.see("end")
            self.log_text.configure(state="disabled")
        self.after(0, _append)

    def _on_sync_category(self, category):
        if self.is_syncing: return
        self.is_syncing = True
        for btn in self.category_buttons.values(): btn.configure(state="disabled")
        
        color_id = self.cb_color.get_id()
        variante_id = self.cb_variante.get_id()
        
        threading.Thread(target=self._run_sync, args=(category, color_id, variante_id), daemon=True).start()

    def _run_sync(self, category, filter_color_id, filter_variante_id):
        try:
            tipo_id = category["id"]
            self._add_log(f"INICIANDO SINCRONIZACIÓN DE {category['name']}...")
            bases = self.stock_service.listar_todo()
            bases_filtradas = [
                b for b in bases if b.get('tipo_id') == tipo_id and
                (not filter_color_id or b.get('color_id') == filter_color_id) and
                (not filter_variante_id or b.get('variante_id') == filter_variante_id)
            ]
            
            if not bases_filtradas:
                self._add_log("Sin resultados para los filtros seleccionados.")
                self.after(0, lambda: show_error(self, "No hay productos para sincronizar."))
                return

            self._add_log(f"Detectadas {len(bases_filtradas)} variantes para subir.")
            total_actualizados = 0
            for base in bases_filtradas:
                sku = base.get('sku')
                cantidad = base.get('cantidad', 0)
                if not sku: continue
                self._add_log(f"Subiendo {sku} -> Stock: {cantidad}")
                res = self.sync_service.sync_stock_by_sku_prefix(sku, int(cantidad))
                if res["success"]:
                    updated = res.get("updated", 0)
                    total_actualizados += updated
                    self._add_log(f"   OK: {updated} variantes en web.")
                else:
                    self._add_log(f"   ERROR en {sku}: {res['message']}")

            self._add_log(f"--- PROCESO FINALIZADO ---")
            self.after(0, lambda: show_success(self, f"Sincronización completada."))
        except Exception as e:
            self._add_log(f"ERROR CRÍTICO: {str(e)}")
        finally:
            self.is_syncing = False
            self.after(0, self._reenable_buttons)

    def _reenable_buttons(self):
        for btn in self.category_buttons.values(): btn.configure(state="normal")

