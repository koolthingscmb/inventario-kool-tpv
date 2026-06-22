"""Vista de configuración del taller de producción (Backoffice).

Permite gestionar el catálogo de colores, tallas, géneros y definir
la matriz de disponibilidad (qué géneros tienen qué colores/tallas).
"""
import tkinter as tk
import customtkinter as ctk
import logging
from typing import Callable, Optional, List

from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.produccion.services.produccion_config_service import ProduccionConfigService
from kool_tpv.modulos.produccion.ui.subvistas.config_helper import cargar_config_produccion, get_font
from kool_tpv.utils.widgets.virtual_nav_list import VirtualNavList
from kool_tpv.utils.config_loader import load_layout_config

class ProduccionConfigView:
    def __init__(self, parent, db: Database, on_cerrar: Optional[Callable] = None):
        self.parent = parent
        self.db = db
        self.on_cerrar = on_cerrar
        self.service = ProduccionConfigService(db)

        # Cargar configuración visual
        self.config = cargar_config_produccion()
        self._colors = self.config.get("colors", {})
        self._bg = self._colors.get("background", "#2c3e50")
        self._text = self._colors.get("text", "#ecf0f1")

        # Layout config y keyboard manager para VirtualNavList
        self._layout_config = load_layout_config()
        root = parent.winfo_toplevel()
        self._km = getattr(root, 'keyboard_manager', None)

        # Estado de tabs
        self._main_tabs = ["CATÁLOGO", "MATRIZ", "MENÚ", "TIPOS"]
        self._sub_tabs = ["COLORES", "TALLAS", "GÉNEROS"]
        self._current_main_tab = None
        self._current_sub_tab = None
        self._main_tab_labels = {}
        self._sub_tab_labels = {}
        self._sub_tab_bar = None

        # Frame principal (tk.Frame nativo - sin flash blanco)
        self.frame = tk.Frame(parent, bg=self._bg)
        self.frame.pack(fill=tk.BOTH, expand=True)

        # Título y botón cerrar
        self._crear_cabecera()

        # Barra de tabs principales
        self._crear_tab_bar()

        # Barra de sub-tabs (solo visible para CATÁLOGO)
        self._crear_sub_tab_bar()

        # Frame de contenido (se limpia y rellena al cambiar de tab)
        self._content_frame = tk.Frame(self.frame, bg=self._bg)
        self._content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(5, 10))

        # Seleccionar primer tab
        self._select_main_tab("CATÁLOGO")

    def _crear_cabecera(self):
        cabecera = tk.Frame(self.frame, bg=self._bg, height=50)
        cabecera.pack(fill="x", padx=20, pady=(10, 0))
        cabecera.pack_propagate(False)

        titulo = tk.Label(
            cabecera,
            text="CONFIGURACIÓN DEL TALLER",
            font=get_font(self.config, "title"),
            fg=self._text,
            bg=self._bg
        )
        titulo.pack(side="left", pady=8)

        btn_cerrar = ctk.CTkButton(
            cabecera,
            text="✕",
            width=40,
            height=40,
            fg_color="#e74c3c",
            hover_color="#c0392b",
            command=self._on_cerrar
        )
        btn_cerrar.pack(side="right", pady=5)

    # --- Sistema de tabs casero (sin CTkTabview = sin flash) ---

    _TAB_BG_NORMAL = "#34495e"
    _TAB_BG_SELECTED = "#3498db"
    _TAB_BG_SUB_NORMAL = "#2c3e50"
    _TAB_BG_SUB_SELECTED = "#9b59b6"

    def _crear_tab_bar(self):
        bar = tk.Frame(self.frame, bg=self._bg, height=36)
        bar.pack(fill="x", padx=20, pady=(5, 0))
        bar.pack_propagate(False)

        for tab_name in self._main_tabs:
            lbl = tk.Label(
                bar, text=tab_name, font=get_font(self.config, "label"),
                fg=self._text, bg=self._TAB_BG_NORMAL,
                padx=20, pady=6, cursor="hand2"
            )
            lbl.pack(side="left", padx=(0, 4))
            lbl.bind("<Button-1>", lambda e, name=tab_name: self._select_main_tab(name))
            self._main_tab_labels[tab_name] = lbl

    def _crear_sub_tab_bar(self):
        self._sub_tab_bar = tk.Frame(self.frame, bg=self._bg, height=30)
        # No se hace pack aquí, se hace cuando se selecciona CATÁLOGO
        self._sub_tab_bar.pack_propagate(False)

        for sub_name in self._sub_tabs:
            lbl = tk.Label(
                self._sub_tab_bar, text=sub_name, font=get_font(self.config, "label"),
                fg=self._text, bg=self._TAB_BG_SUB_NORMAL,
                padx=16, pady=5, cursor="hand2"
            )
            lbl.pack(side="left", padx=(0, 4))
            lbl.bind("<Button-1>", lambda e, name=sub_name: self._select_sub_tab(name))
            self._sub_tab_labels[sub_name] = lbl

    def _select_main_tab(self, tab_name):
        if self._current_main_tab == tab_name:
            return
        self._current_main_tab = tab_name

        # Actualizar estilo de botones principales
        for name, lbl in self._main_tab_labels.items():
            bg = self._TAB_BG_SELECTED if name == tab_name else self._TAB_BG_NORMAL
            lbl.configure(bg=bg)

        # Mostrar/ocultar sub-tab bar
        if tab_name == "CATÁLOGO":
            self._sub_tab_bar.pack(fill="x", padx=20, pady=(4, 0), before=self._content_frame)
            # Seleccionar primer sub-tab si no hay ninguno
            if not self._current_sub_tab:
                self._select_sub_tab("COLORES")
            else:
                self._load_sub_tab_content(self._current_sub_tab)
        else:
            self._sub_tab_bar.pack_forget()
            self._current_sub_tab = None
            self._clear_content()
            if tab_name == "MATRIZ":
                self._build_matriz()
            elif tab_name == "MENÚ":
                self._build_menu()
            elif tab_name == "TIPOS":
                self._build_tipos()

    def _select_sub_tab(self, sub_name):
        if self._current_sub_tab == sub_name:
            return
        self._current_sub_tab = sub_name

        # Actualizar estilo de botones sub-tab
        for name, lbl in self._sub_tab_labels.items():
            bg = self._TAB_BG_SUB_SELECTED if name == sub_name else self._TAB_BG_SUB_NORMAL
            lbl.configure(bg=bg)

        self._load_sub_tab_content(sub_name)

    def _load_sub_tab_content(self, sub_name):
        self._clear_content()
        if sub_name == "COLORES":
            self._build_sub_colores()
        elif sub_name == "TALLAS":
            self._build_sub_tallas()
        elif sub_name == "GÉNEROS":
            self._build_sub_generos()
        # Forzar refresh del VirtualNavList tras construir
        self.frame.after(50, self._refresh_current_nav)

    def _clear_content(self):
        for child in self._content_frame.winfo_children():
            child.destroy()

    def _refresh_current_nav(self):
        nav = getattr(self, f"_nav_{self._current_sub_tab.lower()}", None) if self._current_sub_tab else None
        if nav and hasattr(nav, '_refresh_ui'):
            nav.update_idletasks()
            nav._refresh_ui()

    def _on_cerrar(self):
        if self.on_cerrar:
            self.on_cerrar()
        self.frame.destroy()

    # --- Sub-pestaña: COLORES ---

    def _build_sub_colores(self):
        content = tk.Frame(self._content_frame, bg=self._bg)
        content.pack(fill=tk.BOTH, expand=True)

        # --- Lista (izquierda) con VirtualNavList ---
        frame_lista = tk.Frame(content, bg="#34495e", bd=0, highlightthickness=0)
        frame_lista.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        columns = [
            ("nombre", 200, "NOMBRE"),
            ("codigo_hex", 120, "HEX"),
        ]

        self._nav_colores = VirtualNavList(
            parent=frame_lista,
            columns=columns,
            on_select=self._on_color_selected,
            module_name="produccion",
            keyboard_manager=self._km,
            layout_config=self._layout_config,
        )
        self._nav_colores.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        # --- Formulario (derecha) ---
        frame_form = tk.Frame(content, bg="#34495e", bd=0, highlightthickness=0, width=300)
        frame_form.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        frame_form.pack_propagate(False)

        tk.Label(frame_form, text="Editar / Crear color", font=get_font(self.config, "label"),
                 fg=self._text, bg="#34495e").pack(pady=(10, 5))

        self._color_id_edit = None
        self._entry_color_nombre = ctk.CTkEntry(frame_form, placeholder_text="Nombre del color", width=250)
        self._entry_color_nombre.pack(pady=5, padx=20)

        self._entry_color_hex = ctk.CTkEntry(frame_form, placeholder_text="Código HEX (#FFFFFF)", width=250)
        self._entry_color_hex.pack(pady=5, padx=20)

        self._color_preview = ctk.CTkFrame(frame_form, fg_color="#FFFFFF", width=250, height=40, corner_radius=6)
        self._color_preview.pack(pady=5, padx=20)
        self._entry_color_hex.bind("<KeyRelease>", lambda e: self._actualizar_preview_color())

        frame_btns = tk.Frame(frame_form, bg="#34495e")
        frame_btns.pack(pady=15, padx=20, fill=tk.X)

        ctk.CTkButton(frame_btns, text="GUARDAR", fg_color="#27ae60", hover_color="#2ecc71",
                      command=self._guardar_color).pack(side=tk.LEFT, padx=(0, 5), expand=True, fill=tk.X)
        ctk.CTkButton(frame_btns, text="NUEVO", fg_color="#2980b9", hover_color="#3498db",
                      command=self._limpiar_form_color).pack(side=tk.LEFT, padx=(5, 0), expand=True, fill=tk.X)
        ctk.CTkButton(frame_btns, text="ELIMINAR", fg_color="#e74c3c", hover_color="#c0392b",
                      command=self._eliminar_color).pack(side=tk.LEFT, padx=(5, 0), expand=True, fill=tk.X)

        self._cargar_lista_colores()

    def _cargar_lista_colores(self):
        colores = self.service.obtener_todos_colores()
        items = [{"id": c.id, "nombre": c.nombre, "codigo_hex": c.codigo_hex or ""} for c in colores]
        self._nav_colores.set_items(items)

    def _on_color_selected(self, data):
        """Callback desde VirtualNavList cuando se selecciona una fila."""
        self._color_id_edit = data.get("id")
        self._entry_color_nombre.delete(0, tk.END)
        self._entry_color_nombre.insert(0, data.get("nombre", ""))
        self._entry_color_hex.delete(0, tk.END)
        self._entry_color_hex.insert(0, data.get("codigo_hex", ""))
        self._actualizar_preview_color()

    def _actualizar_preview_color(self):
        hex_code = self._entry_color_hex.get().strip()
        if hex_code:
            try:
                self._color_preview.configure(fg_color=hex_code)
            except Exception:
                pass

    def _guardar_color(self):
        nombre = self._entry_color_nombre.get().strip()
        hex_code = self._entry_color_hex.get().strip()
        if not nombre:
            return
        ok = self.service.guardar_color(nombre, hex_code, self._color_id_edit)
        if ok:
            self._limpiar_form_color()
            self._cargar_lista_colores()

    def _limpiar_form_color(self):
        self._color_id_edit = None
        self._entry_color_nombre.delete(0, tk.END)
        self._entry_color_hex.delete(0, tk.END)
        self._color_preview.configure(fg_color="#FFFFFF")

    def _eliminar_color(self):
        if self._color_id_edit:
            self.service.eliminar_color(self._color_id_edit)
            self._limpiar_form_color()
            self._cargar_lista_colores()

    # --- Sub-pestaña: TALLAS ---

    def _build_sub_tallas(self):
        content = tk.Frame(self._content_frame, bg=self._bg)
        content.pack(fill=tk.BOTH, expand=True)

        # --- Lista (izquierda) con VirtualNavList ---
        frame_lista = tk.Frame(content, bg="#34495e", bd=0, highlightthickness=0)
        frame_lista.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        columns = [
            ("nombre", 200, "NOMBRE"),
            ("orden", 80, "ORDEN"),
            ("estado", 60, "ACT"),
        ]

        self._nav_tallas = VirtualNavList(
            parent=frame_lista,
            columns=columns,
            on_select=self._on_talla_selected,
            module_name="produccion",
            keyboard_manager=self._km,
            layout_config=self._layout_config,
        )
        self._nav_tallas.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        # --- Formulario (derecha) ---
        frame_form = tk.Frame(content, bg="#34495e", bd=0, highlightthickness=0, width=300)
        frame_form.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        frame_form.pack_propagate(False)

        tk.Label(frame_form, text="Editar / Crear talla", font=get_font(self.config, "label"),
                 fg=self._text, bg="#34495e").pack(pady=(10, 5))

        self._talla_id_edit = None
        self._entry_talla_nombre = ctk.CTkEntry(frame_form, placeholder_text="Nombre (S, M, L, XL...)", width=250)
        self._entry_talla_nombre.pack(pady=5, padx=20)

        self._entry_talla_orden = ctk.CTkEntry(frame_form, placeholder_text="Orden (0, 1, 2...)", width=250)
        self._entry_talla_orden.pack(pady=5, padx=20)

        self._var_talla_activo = ctk.IntVar(value=1)
        ctk.CTkCheckBox(frame_form, text="Activo", variable=self._var_talla_activo,
                        fg_color="#27ae60", text_color=self._text).pack(pady=5, padx=20, anchor="w")

        frame_btns = tk.Frame(frame_form, bg="#34495e")
        frame_btns.pack(pady=15, padx=20, fill=tk.X)

        ctk.CTkButton(frame_btns, text="GUARDAR", fg_color="#27ae60", hover_color="#2ecc71",
                      command=self._guardar_talla).pack(side=tk.LEFT, padx=(0, 5), expand=True, fill=tk.X)
        ctk.CTkButton(frame_btns, text="NUEVO", fg_color="#2980b9", hover_color="#3498db",
                      command=self._limpiar_form_talla).pack(side=tk.LEFT, padx=(5, 0), expand=True, fill=tk.X)
        ctk.CTkButton(frame_btns, text="ELIMINAR", fg_color="#e74c3c", hover_color="#c0392b",
                      command=self._eliminar_talla).pack(side=tk.LEFT, padx=(5, 0), expand=True, fill=tk.X)

        self._cargar_lista_tallas()

    def _cargar_lista_tallas(self):
        tallas = self.service.obtener_todas_tallas()
        items = [{
            "id": t.id,
            "nombre": t.nombre,
            "orden": str(t.orden),
            "estado": "✓" if t.activo else "✗",
            "_activo": t.activo,
        } for t in tallas]
        self._nav_tallas.set_items(items)

    def _on_talla_selected(self, data):
        """Callback desde VirtualNavList cuando se selecciona una fila."""
        self._talla_id_edit = data.get("id")
        self._entry_talla_nombre.delete(0, tk.END)
        self._entry_talla_nombre.insert(0, data.get("nombre", ""))
        self._entry_talla_orden.delete(0, tk.END)
        self._entry_talla_orden.insert(0, data.get("orden", "0"))
        self._var_talla_activo.set(data.get("_activo", 1))

    def _guardar_talla(self):
        nombre = self._entry_talla_nombre.get().strip()
        if not nombre:
            return
        try:
            orden = int(self._entry_talla_orden.get().strip() or "0")
        except ValueError:
            orden = 0
        activo = self._var_talla_activo.get()
        ok = self.service.guardar_talla(nombre, orden, activo, self._talla_id_edit)
        if ok:
            self._limpiar_form_talla()
            self._cargar_lista_tallas()

    def _limpiar_form_talla(self):
        self._talla_id_edit = None
        self._entry_talla_nombre.delete(0, tk.END)
        self._entry_talla_orden.delete(0, tk.END)
        self._var_talla_activo.set(1)

    def _eliminar_talla(self):
        if self._talla_id_edit:
            self.service.tallas_repo.eliminar(self._talla_id_edit)
            self._limpiar_form_talla()
            self._cargar_lista_tallas()

    # --- Sub-pestaña: GÉNEROS ---

    def _build_sub_generos(self):
        content = tk.Frame(self._content_frame, bg=self._bg)
        content.pack(fill=tk.BOTH, expand=True)

        # --- Lista (izquierda) con VirtualNavList ---
        frame_lista = tk.Frame(content, bg="#34495e", bd=0, highlightthickness=0)
        frame_lista.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        columns = [
            ("nombre", 200, "NOMBRE"),
            ("orden", 80, "ORDEN"),
            ("estado", 60, "ACT"),
        ]

        self._nav_generos = VirtualNavList(
            parent=frame_lista,
            columns=columns,
            on_select=self._on_genero_selected,
            module_name="produccion",
            keyboard_manager=self._km,
            layout_config=self._layout_config,
        )
        self._nav_generos.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        # --- Formulario (derecha) ---
        frame_form = tk.Frame(content, bg="#34495e", bd=0, highlightthickness=0, width=300)
        frame_form.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        frame_form.pack_propagate(False)

        tk.Label(frame_form, text="Editar / Crear género", font=get_font(self.config, "label"),
                 fg=self._text, bg="#34495e").pack(pady=(10, 5))

        self._genero_id_edit = None
        self._entry_genero_nombre = ctk.CTkEntry(frame_form, placeholder_text="Nombre (Hombre, Oversized...)", width=250)
        self._entry_genero_nombre.pack(pady=5, padx=20)

        self._entry_genero_orden = ctk.CTkEntry(frame_form, placeholder_text="Orden (0, 1, 2...)", width=250)
        self._entry_genero_orden.pack(pady=5, padx=20)

        self._var_genero_activo = ctk.IntVar(value=1)
        ctk.CTkCheckBox(frame_form, text="Activo", variable=self._var_genero_activo,
                        fg_color="#27ae60", text_color=self._text).pack(pady=5, padx=20, anchor="w")

        frame_btns = tk.Frame(frame_form, bg="#34495e")
        frame_btns.pack(pady=15, padx=20, fill=tk.X)

        ctk.CTkButton(frame_btns, text="GUARDAR", fg_color="#27ae60", hover_color="#2ecc71",
                      command=self._guardar_genero).pack(side=tk.LEFT, padx=(0, 5), expand=True, fill=tk.X)
        ctk.CTkButton(frame_btns, text="NUEVO", fg_color="#2980b9", hover_color="#3498db",
                      command=self._limpiar_form_genero).pack(side=tk.LEFT, padx=(5, 0), expand=True, fill=tk.X)
        ctk.CTkButton(frame_btns, text="ELIMINAR", fg_color="#e74c3c", hover_color="#c0392b",
                      command=self._eliminar_genero).pack(side=tk.LEFT, padx=(5, 0), expand=True, fill=tk.X)

        self._cargar_lista_generos()

    def _cargar_lista_generos(self):
        generos = self.service.obtener_todos_generos()
        items = [{
            "id": g.id,
            "nombre": g.nombre,
            "orden": str(g.orden),
            "estado": "✓" if g.activo else "✗",
            "_activo": g.activo,
        } for g in generos]
        self._nav_generos.set_items(items)

    def _on_genero_selected(self, data):
        """Callback desde VirtualNavList cuando se selecciona una fila."""
        self._genero_id_edit = data.get("id")
        self._entry_genero_nombre.delete(0, tk.END)
        self._entry_genero_nombre.insert(0, data.get("nombre", ""))
        self._entry_genero_orden.delete(0, tk.END)
        self._entry_genero_orden.insert(0, data.get("orden", "0"))
        self._var_genero_activo.set(data.get("_activo", 1))

    def _guardar_genero(self):
        nombre = self._entry_genero_nombre.get().strip()
        if not nombre:
            return
        try:
            orden = int(self._entry_genero_orden.get().strip() or "0")
        except ValueError:
            orden = 0
        activo = self._var_genero_activo.get()
        ok = self.service.guardar_genero(nombre, orden, activo, self._genero_id_edit)
        if ok:
            self._limpiar_form_genero()
            self._cargar_lista_generos()

    def _limpiar_form_genero(self):
        self._genero_id_edit = None
        self._entry_genero_nombre.delete(0, tk.END)
        self._entry_genero_orden.delete(0, tk.END)
        self._var_genero_activo.set(1)

    def _eliminar_genero(self):
        if self._genero_id_edit:
            self.service.generos_repo.eliminar(self._genero_id_edit)
            self._limpiar_form_genero()
            self._cargar_lista_generos()

    def _build_matriz(self):
        lbl = tk.Label(self._content_frame, text="Matriz de Disponibilidad (Próximamente)",
                       font=get_font(self.config, "label"), fg=self._text, bg=self._bg)
        lbl.pack(pady=40)

    def _build_menu(self):
        lbl = tk.Label(self._content_frame, text="Configuración del Menú Principal (Próximamente)",
                       font=get_font(self.config, "label"), fg=self._text, bg=self._bg)
        lbl.pack(pady=40)

    def _build_tipos(self):
        lbl = tk.Label(self._content_frame, text="Configuración de Tipos y Costes (Próximamente)",
                       font=get_font(self.config, "label"), fg=self._text, bg=self._bg)
        lbl.pack(pady=40)
