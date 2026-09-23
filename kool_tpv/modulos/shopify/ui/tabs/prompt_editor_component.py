import tkinter as tk
import customtkinter as ctk
import logging
from typing import Dict, Any, List, Optional
from kool_tpv.utils.factories.button_factory import ButtonFactory
from kool_tpv.utils.widgets.notificaciones import show_success, show_error

logger = logging.getLogger(__name__)

class PromptEditorComponent:
    """Componente reutilizable para editar prompts con chips y editor."""

    # Marcadores disponibles por prompt
    _MARCADORES = {
        "tags": "{titulo_base} {tipo_producto}",
        "body": "{variante} {tipo_producto} {titulo_base} {tono} {instrucciones_variante} {tags} {beneficio} {tags_top3}",
        "seo": "{tipo_producto} {titulo_base} {tags} {beneficio}",
        "seo_title": "{titulo} {variante} {marca}",
        "html": "{titulo_introductorio} {parrafo_introductorio} {titulo_seccion_calidad} {bloque_calidad_impresion} {bloque_calidad_material} {bloque_calidad_durabilidad} {bloque_porque_elegirnos} {botones_html}",
        "manga_seo": "{product_name} {source_data}",
    }

    def __init__(self, parent, db, prompts_repo, primary_color, secondary_color, bg_color, bg_medium, tab_bg_selected, tab_bg_normal, tab_text_selected, tab_text_normal):
        self.parent = parent
        self.db = db
        self.prompts_repo = prompts_repo
        self._primary_color = primary_color
        self._secondary_color = secondary_color
        self._bg_color = bg_color
        self._bg_medium = bg_medium
        self._tab_bg_selected = tab_bg_selected
        self._tab_bg_normal = tab_bg_normal
        self._tab_text_selected = tab_text_selected
        self._tab_text_normal = tab_text_normal

        # Estado local (memoria temporal antes de guardar)
        self._prompt_edits = {}         # { (clave, tipo_id): texto }
        self._prompt_nombre_edits = {}  # { clave: nombre }
        
        # Widgets actuales
        self._active_prompt: Optional[str] = None
        self._current_tipo_id: Optional[int] = None
        
        self._chips = {}
        self._area = None
        self._editor = None
        self._nombre_entry = None

    def render(self, container: tk.Frame, tipo_id: Optional[int] = None):
        """Dibuja el panel del editor."""
        self.parent = container
        self._current_tipo_id = tipo_id
        
        frame = tk.Frame(container, bg=self._bg_medium if tipo_id else self._bg_color)
        frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        # Determinar qué prompts mostrar
        if tipo_id is None:
            prompts = self.prompts_repo.get_genericos()
        else:
            prompts = []
            for clave in ["tags", "body", "seo", "seo_title", "html"]:
                p = self.prompts_repo.get_prompt(clave)
                if p: prompts.append(p)

        if not prompts: return

        # Chips
        chips_frame = tk.Frame(frame, bg=frame["bg"])
        chips_frame.pack(fill="x", pady=(0, 10))
        
        self._chips = {}
        self._area = tk.Frame(frame, bg=frame["bg"])
        self._area.pack(fill="both", expand=True)

        for p in prompts:
            clave = p['clave']
            chip = tk.Label(
                chips_frame, text=p['nombre'].upper(), font=("Helvetica", 10, "bold"),
                fg=self._tab_text_normal, bg=self._tab_bg_normal,
                padx=16, pady=8, cursor="hand2"
            )
            chip.pack(side="left", padx=(0, 6))
            chip.bind("<Button-1>", lambda e, c=clave: self.select_prompt(c))
            self._chips[clave] = chip

        # Seleccionar el primero
        self.select_prompt(prompts[0]['clave'])

    def select_prompt(self, clave: str):
        """Cambia el prompt activo en el editor."""
        # Flush actual a memoria
        if self._active_prompt and self._editor and self._editor.winfo_exists():
            self._prompt_edits[(self._active_prompt, self._current_tipo_id)] = self._editor.get("1.0", "end-1c")
            if self._nombre_entry and self._nombre_entry.winfo_exists():
                self._prompt_nombre_edits[self._active_prompt] = self._nombre_entry.get().strip()

        self._active_prompt = clave
        
        # Visual chips
        for c, lbl in self._chips.items():
            if c == clave: lbl.configure(bg=self._tab_bg_selected, fg=self._tab_text_selected)
            else: lbl.configure(bg=self._tab_bg_normal, fg=self._tab_text_normal)

        for child in self._area.winfo_children(): child.destroy()

        # Datos
        data = self.prompts_repo.get_prompt(clave, self._current_tipo_id) or self.prompts_repo.get_prompt(clave)
        texto = self._prompt_edits.get((clave, self._current_tipo_id)) or self.prompts_repo.get_texto(clave, self._current_tipo_id)

        # Header
        head = tk.Frame(self._area, bg=self._area["bg"])
        head.pack(fill="x", pady=(0, 5))
        
        if self._current_tipo_id is None:
            tk.Label(head, text="NOMBRE:", font=("Helvetica", 10, "bold"), fg="#888", bg=head["bg"]).pack(side="left", padx=(0, 8))
            self._nombre_entry = ctk.CTkEntry(head, width=220, height=28, font=("Helvetica", 11))
            self._nombre_entry.insert(0, self._prompt_nombre_edits.get(clave) or data.get('nombre') or clave)
            self._nombre_entry.pack(side="left", padx=(0, 20))
            self._setup_select_all(self._nombre_entry)
        
        marcadores = self._MARCADORES.get(clave, "")
        tk.Label(head, text=f"Marcadores: {marcadores}", font=("Helvetica", 9, "italic"), fg="#888", bg=head["bg"]).pack(side="left")

        # Editor
        h = 180 if self._current_tipo_id else 540
        self._editor = ctk.CTkTextbox(self._area, height=h, font=("Consolas" if not self._current_tipo_id else "Helvetica", 12 if not self._current_tipo_id else 11), wrap="word")
        self._editor.pack(fill="both", expand=True, pady=(0, 8))
        self._editor.insert("1.0", texto)
        self._setup_select_all(self._editor)
        
        if self._current_tipo_id:
            self._editor.after(100, self.ajustar_altura)

        # Footer
        foot = tk.Frame(self._area, bg=self._area["bg"])
        foot.pack(fill="x")
        
        if self._current_tipo_id is not None:
            es_perso = bool(self.prompts_repo.get_prompt(clave, self._current_tipo_id))
            lbl_est = tk.Label(foot, text="PERSONALIZADO" if es_perso else "GENÉRICO", font=("Helvetica", 9, "bold"),
                               fg="#00FF00" if es_perso else "#888888", bg=foot["bg"])
            lbl_est.pack(side="left")
            
            ButtonFactory.create_button(foot, text="GUARDAR", color=self._primary_color, text_color="#000000",
                                        command=lambda: self._guardar_individual(clave, self._current_tipo_id, lbl_est),
                                        width=110, height=30).pack(side="right")
            ButtonFactory.create_button(foot, text="RESTAURAR GENÉRICO", color=self._secondary_color, text_color="#FFFFFF",
                                        command=lambda: self._restaurar(clave, self._current_tipo_id, lbl_est),
                                        width=150, height=30).pack(side="right", padx=(0, 8))
        else:
            ButtonFactory.create_button(head, text="RESTAURAR ORIGINAL", color=self._secondary_color, text_color="#FFFFFF",
                                        command=lambda: self._restaurar(clave, None, None),
                                        width=170, height=26).pack(side="right")

    def _setup_select_all(self, widget):
        def select_all(e):
            if isinstance(e.widget, ctk.CTkTextbox):
                e.widget.tag_add("sel", "1.0", "end")
                e.widget.mark_set("insert", "1.0")
            else:
                e.widget.select_range(0, 'end')
                e.widget.icursor('end')
            return "break"
        widget.bind("<Command-a>", select_all)
        widget.bind("<Control-a>", select_all)

    def ajustar_altura(self):
        """Ajusta el alto del editor al espacio disponible."""
        if not self._editor or not self._editor.winfo_exists(): return
        try:
            top = self._editor.winfo_toplevel()
            editor_y = self._editor.winfo_rooty() - top.winfo_rooty()
            disponible = top.winfo_height() - editor_y - 160
            self._editor.configure(height=max(200, disponible))
        except: pass

    def _guardar_individual(self, clave, tipo_id, lbl_est):
        texto = self._editor.get("1.0", "end-1c")
        if self.prompts_repo.save_texto(clave, texto, tipo_id):
            self._prompt_edits.pop((clave, tipo_id), None)
            if lbl_est: lbl_est.configure(text="PERSONALIZADO", fg="#00FF00")
            show_success(self.parent, f"Guardado correctamente.")
        else: show_error(self.parent, "Error al guardar.")

    def _restaurar(self, clave, tipo_id, lbl_est):
        texto = self.prompts_repo.reset_to_default(clave, tipo_id)
        if texto is None and tipo_id is not None:
            texto = self.prompts_repo.get_texto(clave, None)
        if texto is not None:
            self._prompt_edits.pop((clave, tipo_id), None)
            self._editor.delete("1.0", "end")
            self._editor.insert("1.0", texto)
            if lbl_est: lbl_est.configure(text="GENÉRICO", fg="#888888")
            show_success(self.parent, "Prompt restaurado.")

    def clear_local_edits(self):
        """Limpia la memoria temporal de ediciones."""
        self._prompt_edits = {}
        self._prompt_nombre_edits = {}

    def harvest_all(self, target_edits, target_nombre_edits):
        """Vuelca los cambios en memoria a los diccionarios globales."""
        if self._active_prompt and self._editor and self._editor.winfo_exists():
            self._prompt_edits[(self._active_prompt, self._current_tipo_id)] = self._editor.get("1.0", "end-1c")
            if self._nombre_entry and self._nombre_entry.winfo_exists():
                self._prompt_nombre_edits[self._active_prompt] = self._nombre_entry.get().strip()
                
        target_edits.update(self._prompt_edits)
        target_nombre_edits.update(self._prompt_nombre_edits)
