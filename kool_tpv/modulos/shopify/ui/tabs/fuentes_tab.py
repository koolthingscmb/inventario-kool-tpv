import tkinter as tk
import customtkinter as ctk
import logging
from typing import List, Dict, Any, Optional
from kool_tpv.utils.widgets.searchable_combo import SearchableCombo
from kool_tpv.utils.widgets.notificaciones import show_error

logger = logging.getLogger(__name__)

class FuentesTab:
    """Gestiona la vinculación de fuentes de datos externas a tipos de producto."""

    def __init__(self, parent, db, config, source_manager, service, primary_color, secondary_color, bg_color, bg_medium):
        self.parent = parent
        self.db = db
        self._config = config
        self.source_manager = source_manager
        self.service = service
        self._primary_color = primary_color
        self._secondary_color = secondary_color
        self._bg_color = bg_color
        self._bg_medium = bg_medium
        
        self.type_combo = None
        self.widgets = {}

    def render(self):
        """Dibuja la interfaz de la pestaña FUENTES."""
        # --- ZONA GLOBAL DE SELECCIÓN DE TIPO ---
        selection_zone = tk.Frame(self.parent, bg=self._bg_color)
        selection_zone.pack(fill="x", padx=10, pady=(0, 20))
        
        tk.Label(
            selection_zone, text="TIPO DE PRODUCTO A VINCULAR:", 
            font=("Helvetica", 10, "bold"), fg="#888", bg=self._bg_color
        ).pack(side="left", padx=(0, 10))
        
        # Cargar tipos para el combo
        try:
            rows = self.db.fetch_all("SELECT id, nombre FROM tipos ORDER BY nombre ASC")
            all_types = [(r[0], r[1]) for r in (rows or [])]
        except Exception:
            all_types = []
            
        self.type_combo = SearchableCombo(
            selection_zone, 
            options=all_types,
            placeholder="Selecciona un tipo...",
            width=300,
            module_name='shopify'
        )
        self.type_combo.pack(side="left")
        
        # --- LISTADO DE CONECTORES ---
        sources = self.source_manager.get_all_sources()

        for source in sources:
            f_frame = tk.Frame(self.parent, bg=self._bg_medium, bd=1, relief="flat")
            f_frame.pack(fill="x", pady=5, ipady=10)
            
            # Contenedor izquierdo (Nombre + Tags)
            left_container = tk.Frame(f_frame, bg=self._bg_medium)
            left_container.pack(side="left", fill="both", expand=True, padx=20)
            
            top_line = tk.Frame(left_container, bg=self._bg_medium)
            top_line.pack(fill="x")
            
            tk.Label(top_line, text=source.name, font=("Helvetica", 12, "bold"), fg=self._primary_color, bg=self._bg_medium).pack(side="left")
            tk.Label(top_line, text=f"- {source.description}", font=("Helvetica", 10), fg="#888", bg=self._bg_medium).pack(side="left", padx=10)
            
            # Zona de Tags (Vínculos actuales)
            tags_frame = tk.Frame(left_container, bg=self._bg_medium)
            tags_frame.pack(fill="x", pady=(5, 0))
            self._render_source_tags(source, tags_frame)
            
            # Botones derecha
            cb = ctk.CTkCheckBox(f_frame, text="ACTIVAR", font=("Helvetica", 10, "bold"), fg_color=self._primary_color, hover_color=self._secondary_color, text_color="#FFFFFF")
            if self._config.get(source.id): cb.select()
            else: cb.deselect()
            cb.pack(side="right", padx=10)
            self.widgets[source.id] = cb

            btn_test = ctk.CTkButton(f_frame, text="Test", width=60, height=24, fg_color=self._secondary_color, command=lambda s=source: self._on_test_source(s))
            btn_test.pack(side="right", padx=10)

            # Botón "+" para añadir el tipo seleccionado en el combo
            btn_add = ctk.CTkButton(
                f_frame, text="+", width=30, height=24, 
                fg_color=self._primary_color, font=("Helvetica", 14, "bold"),
                command=lambda s=source, tf=tags_frame: self._on_add_type_to_source(s, tf)
            )
            btn_add.pack(side="right", padx=10)

    def _render_source_tags(self, source, parent):
        """Dibuja los tipos vinculados como etiquetas."""
        for child in parent.winfo_children():
            child.destroy()
            
        try:
            # Obtener nombres de tipos mapeados
            query = """
                SELECT t.id, t.nombre 
                FROM tipos t
                JOIN shopify_source_type_mapping m ON t.id = m.tipo_id
                WHERE m.source_id = ?
                ORDER BY t.nombre ASC
            """
            rows = self.db.fetch_all(query, (source.id,))
            
            if not rows:
                tk.Label(parent, text="Sin tipos vinculados", font=("Helvetica", 8, "italic"), fg="#555", bg=self._bg_medium).pack(side="left")
                return

            for t_id, t_nombre in rows:
                tag = tk.Frame(parent, bg="#333", padx=5, pady=2)
                tag.pack(side="left", padx=(0, 5))
                
                tk.Label(tag, text=t_nombre.upper(), font=("Helvetica", 8, "bold"), fg=self._primary_color, bg="#333").pack(side="left")
                
                btn_del = tk.Label(tag, text="✕", font=("Helvetica", 8), fg="#666", bg="#333", cursor="hand2")
                btn_del.pack(side="left", padx=(5, 0))
                btn_del.bind("<Button-1>", lambda e, sid=source.id, tid=t_id, tf=parent: self._on_remove_type_from_source(sid, tid, tf))

        except Exception:
            logger.exception("Error renderizando tags")

    def _on_add_type_to_source(self, source, tags_frame):
        """Añade el tipo seleccionado en el combo al conector."""
        if not self.type_combo: return
        tipo_id = self.type_combo.get_id()
        if not tipo_id:
            show_error(self.parent, "Selecciona primero un tipo en el buscador superior.")
            return
            
        # Obtener mapeos actuales para añadir el nuevo
        current_ids = self.service.get_source_type_mappings(source.id)
        if tipo_id in current_ids:
            show_error(self.parent, "Este tipo ya está vinculado a esta fuente.")
            return
            
        current_ids.append(tipo_id)
        if self.service.update_source_type_mappings(source.id, current_ids):
            self._render_source_tags(source, tags_frame)
        else:
            show_error(self.parent, "Error al guardar el vínculo.")

    def _on_remove_type_from_source(self, source_id, tipo_id, tags_frame):
        """Elimina un vínculo de tipo."""
        current_ids = self.service.get_source_type_mappings(source_id)
        if tipo_id in current_ids:
            current_ids.remove(tipo_id)
            if self.service.update_source_type_mappings(source_id, current_ids):
                self._render_source_tags(None, tags_frame) # Trigger re-render by passing source logic or re-fetching
                # Re-render properly:
                try:
                    # Find the source object again if possible, or just trigger refresh
                    # For simplicity, we just reload the tags if we had the source ref.
                    # Since we don't have it easily here without passing it, let's just trigger a re-render of the whole tab or use a better way.
                    # Actually we can just re-read the tags from DB.
                    class DummySource: pass
                    s = DummySource()
                    s.id = source_id
                    self._render_source_tags(s, tags_frame)
                except:
                    pass

    def _on_test_source(self, source):
        success, message = source.test_connection()
        if success:
            self.service.add_log("TEST_SOURCE", "success", f"Conector {source.name} OK")
            from kool_tpv.utils.widgets.notificaciones import show_success
            show_success(self.parent, f"Conexión con {source.name} correcta.")
        else:
            self.service.add_log("TEST_SOURCE", "error", f"Fallo conector {source.name}: {message}")
            show_error(self.parent, f"Error: {message}")

    def harvest(self, config_dict: Dict[str, Any]):
        """Recoge los estados de activación de los conectores."""
        for key, widget in self.widgets.items():
            if widget.winfo_exists():
                config_dict[key] = bool(widget.get())
