import tkinter as tk
import customtkinter as ctk
import logging
from typing import Dict, Any
from kool_tpv.modulos.shopify.services.openai_service import OpenAIService
from kool_tpv.utils.factories.button_factory import ButtonFactory
from kool_tpv.utils.widgets.notificaciones import show_success, show_error

logger = logging.getLogger(__name__)

class IATab:
    """Configura la IA con chips (mismo patrón que IA PROMPTS).

    Un chip por proveedor: CHATGPT, GEMINI y GOOGLE BOOKS. Lo escrito se
    guarda en memoria al cambiar de chip (como el editor de prompts) y
    se persiste al GUARDAR. El botón 'USAR ESTA IA' marca el proveedor
    activo. Gemini admite varias API keys (una por línea): si una se
    queda sin cuota, se prueba la siguiente automáticamente."""

    def __init__(self, parent, db, config, primary_color, secondary_color,
                 bg_color, bg_medium, tab_bg_selected, tab_bg_normal,
                 tab_text_selected, tab_text_normal):
        self.parent = parent
        self.db = db
        self._config = config
        self._primary_color = primary_color
        self._secondary_color = secondary_color
        self._bg_color = bg_color
        self._bg_medium = bg_medium
        self._tab_bg_selected = tab_bg_selected
        self._tab_bg_normal = tab_bg_normal
        self._tab_text_selected = tab_text_selected
        self._tab_text_normal = tab_text_normal

        # Widgets del chip visible (se recrean al cambiar); valores en _config
        self.widgets = {}
        self._chips = {}
        self._area = None
        self._chip_visible = "openai"
        self._proveedor_activo = str(config.get("ia_proveedor") or "openai").strip().lower()
        if self._proveedor_activo not in OpenAIService.MODELOS:
            self._proveedor_activo = "openai"

    # ---------- render ----------

    def render(self):
        """Dibuja chips + área del proveedor (patrón IA PROMPTS)."""
        frame = tk.Frame(self.parent, bg=self._bg_color)
        frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        chips_frame = tk.Frame(frame, bg=frame["bg"])
        chips_frame.pack(fill="x", pady=(0, 10))
        self._area = tk.Frame(frame, bg=frame["bg"])
        self._area.pack(fill="both", expand=True)

        for nombre, clave in (("CHATGPT", "openai"), ("GEMINI", "gemini"),
                              ("GOOGLE BOOKS", "google_books")):
            chip = tk.Label(
                chips_frame, text=nombre, font=("Helvetica", 10, "bold"),
                fg=self._tab_text_normal, bg=self._tab_bg_normal,
                padx=16, pady=8, cursor="hand2")
            chip.pack(side="left", padx=(0, 6))
            chip.bind("<Button-1>", lambda e, c=clave: self.select(c))
            self._chips[clave] = chip

        self.select(self._proveedor_activo)

    def select(self, clave: str):
        """Cambia el proveedor visible; antes vuelca lo escrito a memoria."""
        self._flush()
        self._chip_visible = clave
        for c, lbl in self._chips.items():
            if c == clave:
                lbl.configure(bg=self._tab_bg_selected, fg=self._tab_text_selected)
            else:
                lbl.configure(bg=self._tab_bg_normal, fg=self._tab_text_normal)

        for child in self._area.winfo_children():
            child.destroy()
        self.widgets = {}

        if clave == "openai":
            self._render_chatgpt()
        elif clave == "gemini":
            self._render_gemini()
        else:
            self._render_google_books()

    # ---------- sub-paneles ----------

    def _fila(self, texto: str, fila: int) -> tk.Frame:
        """Fila etiqueta + hueco para widget, estilo de la pestaña IA original."""
        fila_frame = tk.Frame(self._area, bg=self._area["bg"])
        fila_frame.grid(row=fila, column=0, sticky="ew", pady=10)
        tk.Label(fila_frame, text=texto, font=("Helvetica", 12),
                 fg="#FFFFFF", bg=fila_frame["bg"], anchor="e", width=22).pack(side="left")
        return fila_frame

    def _combo_modelo(self, marco, proveedor: str) -> ctk.CTkOptionMenu:
        """Desplegable de modelos del proveedor con el último valor guardado."""
        valores = OpenAIService.MODELOS[proveedor]
        guardado = (self._config.get(f"ia_model_{proveedor}") or "").strip()
        if guardado not in valores:
            guardado = OpenAIService.MODELO_DEFECTO[proveedor]
        combo = ctk.CTkOptionMenu(marco, values=valores, height=36, width=250)
        combo.set(guardado)
        return combo

    def _pie_usar(self, proveedor: str, texto_boton: str, fila: int = 3):
        """Pie con 'USAR ESTA IA' + indicador del que está en uso."""
        foot = tk.Frame(self._area, bg=self._area["bg"])
        foot.grid(row=fila, column=0, sticky="w", pady=(14, 4))
        en_uso = self._proveedor_activo == proveedor
        ButtonFactory.create_button(
            foot, text=texto_boton, color=self._secondary_color, text_color="#FFFFFF",
            command=lambda: self._usar(proveedor), width=160, height=32).pack(side="left")
        tk.Label(foot, text="IA EN USO" if en_uso else "",
                 font=("Helvetica", 10, "bold"),
                 fg=self._primary_color, bg=foot["bg"]).pack(side="left", padx=(15, 0))

    def _render_chatgpt(self):
        self._area.grid_columnconfigure(0, weight=1)
        fila = self._fila("Modelo de IA:", 0)
        combo = self._combo_modelo(fila, "openai")
        combo.pack(side="left", padx=(10, 0))
        self.widgets["ia_model_openai"] = combo
        fila = self._fila("OpenAI API Key:", 1)
        entry = ctk.CTkEntry(fila, placeholder_text="sk-...", height=36, show="*",
                             font=("Helvetica", 12))
        entry.insert(0, self._config.get("ia_api_key", ""))
        entry.pack(side="left", fill="x", expand=True, padx=(10, 0))
        self.widgets["ia_api_key"] = entry
        self._pie_usar("openai", "USAR CHATGPT")

    def _render_gemini(self):
        self._area.grid_columnconfigure(0, weight=1)
        fila = self._fila("Modelo de IA:", 0)
        combo = self._combo_modelo(fila, "gemini")
        combo.pack(side="left", padx=(10, 0))
        self.widgets["ia_model_gemini"] = combo

        claves = OpenAIService.claves_gemini_desde_texto(
            self._config.get("ia_gemini_api_keys") or "")

        letras = ["A", "B", "C", "D", "E"]
        for i, letra in enumerate(letras):
            f_key = self._fila(f"Gemini API Key {letra}:", 1 + i)
            entry = ctk.CTkEntry(f_key, placeholder_text=f"AIza... (Cuenta {letra})" if i == 0 else f"Opcional (Cuenta {letra})",
                                 height=32, show="*", font=("Helvetica", 12))
            val = claves[i] if i < len(claves) else ""
            if val:
                entry.insert(0, val)
            entry.pack(side="left", fill="x", expand=True, padx=(10, 0))
            self.widgets[f"ia_gemini_key_{letra}"] = entry

        self._pie_usar("gemini", "USAR GEMINI", fila=1 + len(letras))

    def _render_google_books(self):
        self._area.grid_columnconfigure(0, weight=1)
        fila = self._fila("Google Books API Key:", 0)
        entry = ctk.CTkEntry(fila, placeholder_text="AIza...", height=36, show="*",
                             font=("Helvetica", 12))
        entry.insert(0, self._config.get("google_api_key", ""))
        entry.pack(side="left", fill="x", expand=True, padx=(10, 0))
        self.widgets["google_api_key"] = entry

    def _usar(self, proveedor: str):
        """Marca el proveedor activo (se aplica al GUARDAR la configuración)."""
        self._flush()
        self._proveedor_activo = proveedor
        for child in self._area.winfo_children():
            child.destroy()
        self.widgets = {}
        if proveedor == "openai":
            self._render_chatgpt()
        else:
            self._render_gemini()
        nombre = "ChatGPT" if proveedor == "openai" else "Gemini"
        show_success(self.parent, f"Al guardar, la IA activa será {nombre}")

    # ---------- prueba de conexión ----------

    def _get_gemini_keys_from_ui(self) -> Dict[str, str]:
        """Recupera las claves no vacías introducidas en la interfaz con su letra."""
        claves_ui = {}
        for letra in ["A", "B", "C", "D", "E"]:
            w = self.widgets.get(f"ia_gemini_key_{letra}")
            if w:
                val = w.get().strip()
                if val:
                    claves_ui[letra] = val
        return claves_ui

    def test_ia_connection(self):
        """Prueba la conexión del chip visible (cada llave de Gemini con su letra A, B, C...)."""
        visible = self._chip_visible
        if visible == "gemini":
            model = self.widgets["ia_model_gemini"].get()
            claves_dict = self._get_gemini_keys_from_ui()
            if not claves_dict:
                show_error(self.parent, "Introduce al menos una API key de Gemini antes de probar.")
                return
            resultados, todo_ok = [], True
            for letra, clave in claves_dict.items():
                try:
                    ok, mensaje = OpenAIService(clave, model, proveedor="gemini").test_connection()
                except Exception:
                    logger.exception("Error probando la llave %s de Gemini", letra)
                    ok, mensaje = False, "error inesperado"
                todo_ok = todo_ok and ok
                resultados.append(f"Clave {letra}: {'OK' if ok else 'ERROR - ' + mensaje}")
            resumen = "\n".join(resultados)
            if todo_ok:
                show_success(self.parent, f"Gemini conecta correctamente:\n{resumen}")
            else:
                show_error(self.parent, f"Prueba de Gemini:\n{resumen}")
            return

        if visible == "google_books":
            show_error(self.parent, "Google Books no necesita prueba: se usa al buscar libros.")
            return

        api_key = self.widgets["ia_api_key"].get().strip()
        if not api_key:
            show_error(self.parent, "Introduce una API Key antes de probar.")
            return
        success, message = OpenAIService(api_key, self.widgets["ia_model_openai"].get()).test_connection()
        if success:
            show_success(self.parent, f"Conexión con OpenAI correcta: {message}")
        else:
            show_error(self.parent, f"Error en conexión OpenAI: {message}")

    # ---------- guardado ----------

    def _flush(self):
        """Pasa lo escrito a memoria (patrón IA PROMPTS) para no perderlo
        al cambiar de chip antes de guardar."""
        if "ia_model_openai" in self.widgets:
            self._config["ia_model_openai"] = self.widgets["ia_model_openai"].get()
        if "ia_model_gemini" in self.widgets:
            self._config["ia_model_gemini"] = self.widgets["ia_model_gemini"].get()
        if "ia_api_key" in self.widgets:
            self._config["ia_api_key"] = self.widgets["ia_api_key"].get().strip()

        # Recoger claves de Gemini individuales A, B, C, D, E
        claves_gemini = []
        hay_widgets_gemini = False
        for letra in ["A", "B", "C", "D", "E"]:
            k = f"ia_gemini_key_{letra}"
            if k in self.widgets:
                hay_widgets_gemini = True
                val = self.widgets[k].get().strip()
                if val:
                    claves_gemini.append(val)
        if hay_widgets_gemini:
            self._config["ia_gemini_api_keys"] = "\n".join(claves_gemini)

        if "google_api_key" in self.widgets:
            self._config["google_api_key"] = self.widgets["google_api_key"].get().strip()

    def harvest(self, config_dict: Dict[str, Any]):
        """Recoge los valores actuales para el diccionario de config."""
        self._flush()
        config_dict.update(self._config)
        config_dict["ia_proveedor"] = self._proveedor_activo
        config_dict["ia_model"] = config_dict.get(
            f"ia_model_{self._proveedor_activo}") or config_dict.get("ia_model") or ""
