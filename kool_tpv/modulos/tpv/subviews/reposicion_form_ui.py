from customtkinter import CTkFrame, CTkLabel, CTkEntry, CTkTextbox
import logging
from typing import List, Dict, Optional, Any

import customtkinter as ctk

from kool_tpv.base_datos.producto_service import ProductoService
from kool_tpv.utils.widgets.searchable_combo import SearchableCombo
from kool_tpv.utils.widgets.searchable_paginated_navlist import SearchablePaginatedNavList
from kool_tpv.utils.config_loader import load_layout_config
from kool_tpv.utils.factories.button_factory import ButtonFactory
from kool_tpv.utils.widgets.notificaciones import show_success, show_warning, show_error

# Servicios REPOS (obligatorio, sin queries directas)
from kool_tpv.modulos.produccion.services.produccion_tipos_service import ProduccionTiposService
from kool_tpv.modulos.produccion.services.produccion_tipos_variantes_service import ProduccionTiposVariantesService
from kool_tpv.modulos.produccion.services.produccion_tallas_service import ProduccionTallasService
from kool_tpv.modulos.produccion.services.produccion_colores_service import ProduccionColoresService
from kool_tpv.modulos.produccion.services.produccion_disenos_service import ProduccionDisenosService
from kool_tpv.modulos.produccion.repositories.produccion_colecciones_repository import ProduccionColeccionesRepository
from kool_tpv.modulos.produccion.repositories.produccion_sufijos_repository import ProduccionSufijosRepository

from kool_tpv.modulos.tpv.services.reposicion_store import ReposicionStore

logger = logging.getLogger(__name__)


class ReposicionFormUI(CTkFrame):
    """Formulario de reposición siguiendo estrictamente las zonas definidas por el usuario."""

    def __init__(self, parent, db, carrito_service=None, view=None, productos_pendientes=None, ticket_id=None, callback_finalizar=None):
        super().__init__(parent)

        self.db = db
        self.carrito_service = carrito_service
        self.view = view
        self.productos_pendientes = productos_pendientes or []
        self.ticket_id = ticket_id
        self.callback_finalizar = callback_finalizar

        self.indice_actual = 0
        self.producto_actual = None
        self.tipo_actual = None
        self.diseno_seleccionado = None

        # Servicios (SOLO repos)
        self.producto_service = ProductoService(db)
        self.tipos_service = ProduccionTiposService(db)
        self.variantes_service = ProduccionTiposVariantesService(db)
        self.tallas_service = ProduccionTallasService(db)
        self.colores_service = ProduccionColoresService(db)
        self.disenos_service = ProduccionDisenosService(db)
        self.colecciones_repo = ProduccionColeccionesRepository(db)
        self.sufijos_repo = ProduccionSufijosRepository(db)

        # Keyboard manager
        root = self.winfo_toplevel()
        self.keyboard_manager = getattr(root, 'keyboard_manager', None)

        # Header
        self.header_frame = CTkFrame(self)
        self.header_frame.pack(side="top", fill="x", padx=20, pady=10)

        nombre_inicial = ""
        if self.productos_pendientes:
            nombre_inicial = self.productos_pendientes[0].get('nombre', '')
        self.lbl_titulo = CTkLabel(
            self.header_frame,
            text=f"Reposición de '{nombre_inicial}'",
            font=("Roboto", 20, "bold")
        )
        self.lbl_titulo.pack(side="left", padx=10)

        # Body
        self.body_frame = CTkFrame(self)
        self.body_frame.pack(side="top", fill="both", expand=True, padx=20, pady=10)

        self._setup_ui()
        self._cargar_siguiente_producto()

    def _setup_ui(self):
        # ZONA 1: grid 4x1 - Producto + Tipo
        zona1 = CTkFrame(self.body_frame, fg_color="transparent")
        zona1.pack(fill="x", padx=10, pady=(5, 10))
        for c in range(4):
            zona1.grid_columnconfigure(c, weight=1 if c in (1, 3) else 0, minsize=80 if c in (0, 2) else 0)

        CTkLabel(zona1, text="Producto", font=("Roboto", 14, "bold")).grid(row=0, column=0, padx=(0, 6), sticky="w")
        self.entry_producto = CTkEntry(zona1, height=32)
        self.entry_producto.grid(row=0, column=1, padx=(0, 12), sticky="ew")
        self.entry_producto.configure(state="readonly")

        CTkLabel(zona1, text="Tipo", font=("Roboto", 14, "bold")).grid(row=0, column=2, padx=(0, 6), sticky="w")
        self.entry_tipo = CTkEntry(zona1, height=32)
        self.entry_tipo.grid(row=0, column=3, padx=(0, 0), sticky="ew")
        self.entry_tipo.configure(state="readonly")

        # ZONA 2: grid 6x1 - Variante + Talla + Color (condicionales)
        zona2 = CTkFrame(self.body_frame, fg_color="transparent")
        zona2.pack(fill="x", padx=10, pady=5)
        for c in range(6):
            zona2.grid_columnconfigure(c, weight=1 if c in (1, 3, 5) else 0)

        CTkLabel(zona2, text="Variante", font=("Roboto", 14, "bold")).grid(row=0, column=0, padx=(0, 6), sticky="w")
        self.combo_variante = SearchableCombo(zona2, placeholder="Selecciona variante...", width=220)
        self.combo_variante.grid(row=0, column=1, padx=(0, 12), sticky="ew")

        self.lbl_talla = CTkLabel(zona2, text="Talla", font=("Roboto", 14, "bold"))
        self.lbl_talla.grid(row=0, column=2, padx=(0, 6), sticky="w")
        self.combo_talla = SearchableCombo(zona2, placeholder="Talla...", width=160)
        self.combo_talla.grid(row=0, column=3, padx=(0, 12), sticky="ew")

        self.lbl_color = CTkLabel(zona2, text="Color", font=("Roboto", 14, "bold"))
        self.lbl_color.grid(row=0, column=4, padx=(0, 6), sticky="w")
        self.combo_color = SearchableCombo(zona2, placeholder="Color...", width=160)
        self.combo_color.grid(row=0, column=5, padx=(0, 0), sticky="ew")

        # ZONA 3: Comentarios (full width)
        zona3 = CTkFrame(self.body_frame, fg_color="transparent")
        zona3.pack(fill="x", padx=10, pady=(10, 5))
        CTkLabel(zona3, text="Comentarios", font=("Roboto", 14, "bold")).pack(anchor="w", pady=(0, 4))
        self.text_comentarios = CTkTextbox(zona3, height=60, font=("Roboto", 14))
        self.text_comentarios.pack(fill="x", expand=False)

        # ZONA 4: Nav list diseños (exactamente como en diseño_nuevo)
        zona4 = CTkFrame(self.body_frame, fg_color="transparent")
        zona4.pack(fill="both", expand=True, padx=10, pady=5)

        CTkLabel(zona4, text="Diseños", font=("Roboto", 14, "bold")).pack(anchor="w", pady=(0, 4))

        self.entry_buscar_diseno = CTkEntry(zona4, placeholder_text="Buscar diseño (código, nombre, colección)...", height=32)
        self.entry_buscar_diseno.pack(fill="x", pady=(0, 4))
        self.entry_buscar_diseno.bind("<Return>", self._on_buscar_diseno_enter)
        self.entry_buscar_diseno.bind("<KP_Enter>", self._on_buscar_diseno_enter)

        columns = [
            ("codigo", 100, "Código"),
            ("nombre", 220, "Nombre"),
            ("coleccion_nombre", 140, "Colección"),
            ("sufijo_nombre", 100, "Sufijo"),
            ("tipos_nombres", 140, "Tipos"),
            ("total_producido", 70, "Uds."),
        ]
        self.design_list = SearchablePaginatedNavList(
            parent=zona4,
            columns=columns,
            search_function=self._buscar_disenos,
            map_function=self._map_diseno,
            module_name="tpv",
            page_limit=50,
            on_double_click=self._on_diseno_double_click,
            keyboard_manager=self.keyboard_manager,
            layout_config=load_layout_config(),
        )
        self.design_list.pack(fill="both", expand=True)

        nav = getattr(self.design_list, 'nav_list', None)
        if nav and hasattr(nav, 'bind_return'):
            nav.bind_return(self._on_diseno_return)

        # ZONA 5: Diseño seleccionado (readonly)
        zona5 = CTkFrame(self.body_frame, fg_color="transparent")
        zona5.pack(fill="x", padx=10, pady=(5, 5))
        CTkLabel(zona5, text="Diseño escogido", font=("Roboto", 14, "bold")).pack(anchor="w", pady=(0, 4))
        self.entry_diseno = CTkEntry(zona5, height=32)
        self.entry_diseno.pack(fill="x")
        self.entry_diseno.configure(state="readonly")

        # ZONA 6: Cantidad + Botones
        zona6 = CTkFrame(self.body_frame, fg_color="transparent")
        zona6.pack(fill="x", padx=10, pady=(10, 5))

        CTkLabel(zona6, text="Cantidad", font=("Roboto", 14, "bold")).pack(side="left", padx=(0, 6))
        self.entry_cantidad = CTkEntry(zona6, width=80, height=32)
        self.entry_cantidad.pack(side="left", padx=(0, 20))

        self.btn_guardar = ButtonFactory.create_button(
            zona6,
            text="GUARDAR Y CONTINUAR",
            style_key="action_success",
            command=self._on_guardar
        )
        self.btn_guardar.pack(side="right", padx=6)

        self.btn_cancelar = ButtonFactory.create_button(
            zona6,
            text="CANCELAR",
            style_key="action_danger",
            command=self._on_cancelar
        )
        self.btn_cancelar.pack(side="right", padx=6)

    # ----------------- Carga y estado -----------------

    def _cargar_siguiente_producto(self):
        if self.indice_actual >= len(self.productos_pendientes):
            self._finalizar()
            return

        self.producto_actual = self.productos_pendientes[self.indice_actual]
        nombre = self.producto_actual.get('nombre', '')
        self.lbl_titulo.configure(text=f"Reposición de '{nombre}'")

        # Limpiar selecciones previas
        self.diseno_seleccionado = None
        self.entry_diseno.configure(state="normal")
        self.entry_diseno.delete(0, "end")
        self.entry_diseno.configure(state="readonly")
        self.text_comentarios.delete("1.0", "end")

        # Producto y Tipo vía servicios (sin queries directas aquí)
        prod_id = self.producto_actual.get('producto_id')
        tipo_id = None
        tipo_nombre = ""
        try:
            full = self.producto_service.get_producto_completo(prod_id) if prod_id else None
            if full:
                tipo_id = full.get('tipo')
                tipo_nombre = full.get('tipo_nombre') or ""
        except Exception:
            logger.exception("Error obteniendo producto completo via service")

        self.tipo_actual = self.tipos_service.obtener_por_id(tipo_id) if tipo_id else None

        # Rellenar nombre producto (readonly)
        self.entry_producto.configure(state="normal")
        self.entry_producto.delete(0, "end")
        self.entry_producto.insert(0, nombre.upper())
        self.entry_producto.configure(state="readonly")

        # Rellenar tipo (readonly)
        self.entry_tipo.configure(state="normal")
        self.entry_tipo.delete(0, "end")
        if self.tipo_actual:
            self.entry_tipo.insert(0, self.tipo_actual.nombre.upper())
        else:
            self.entry_tipo.insert(0, (tipo_nombre or "SIN TIPO").upper())
        self.entry_tipo.configure(state="readonly")

        # Variantes
        if self.tipo_actual:
            variantes = self.variantes_service.obtener_por_tipo(self.tipo_actual.id)
            self.combo_variante.set_options([(v.id, v.nombre) for v in variantes])
        else:
            self.combo_variante.set_options([])

        # Talla / Color condicionales + carga
        self._actualizar_opciones_tipo()

        # Cantidad
        self.entry_cantidad.delete(0, "end")
        self.entry_cantidad.insert(0, str(int(self.producto_actual.get('cantidad', 1))))

        # Refrescar lista de diseños (carga inicial ya hecha, pero aseguramos)
        try:
            self.design_list.search("")
        except Exception:
            pass

        # FOCO en Variante
        self.after(120, self._enfocar_variante)

    def _enfocar_variante(self):
        try:
            if hasattr(self.combo_variante, 'entry') and hasattr(self.combo_variante.entry, 'focus_set'):
                self.combo_variante.entry.focus_set()
            elif hasattr(self.combo_variante, 'focus_set'):
                self.combo_variante.focus_set()
        except Exception:
            pass

    def _actualizar_opciones_tipo(self):
        requiere_talla = bool(getattr(self.tipo_actual, 'requiere_talla', False)) if self.tipo_actual else False
        requiere_color = bool(getattr(self.tipo_actual, 'requiere_color', False)) if self.tipo_actual else False

        if requiere_talla:
            self.lbl_talla.grid()
            self.combo_talla.grid()
            try:
                tallas = self.tallas_service.obtener_todas()
                self.combo_talla.set_options([(t.id, t.nombre) for t in tallas])
            except Exception:
                self.combo_talla.set_options([])
        else:
            self.lbl_talla.grid_remove()
            self.combo_talla.grid_remove()
            self.combo_talla.set_options([])

        if requiere_color:
            self.lbl_color.grid()
            self.combo_color.grid()
            try:
                colores = self.colores_service.obtener_todos()
                self.combo_color.set_options([(c.id, c.nombre) for c in colores])
            except Exception:
                self.combo_color.set_options([])
        else:
            self.lbl_color.grid_remove()
            self.combo_color.grid_remove()
            self.combo_color.set_options([])

    # ----------------- Búsqueda y selección de diseños -----------------

    def _buscar_disenos(self, texto: str) -> List[Any]:
        try:
            if texto and texto.strip():
                return self.disenos_service.buscar(texto.strip())
            return self.disenos_service.obtener_activos()
        except Exception:
            return []

    def _map_diseno(self, d: Any) -> dict:
        try:
            col = self.colecciones_repo.get_por_id(d.coleccion_id)
            suf = self.sufijos_repo.get_por_id(d.sufijo_id) if getattr(d, 'sufijo_id', None) else None
            tipos_nombres = ""
            try:
                # Si el modelo tiene lista de tipos, mostramos nombres básicos
                if getattr(d, 'tipos', None):
                    # Intentamos resolver nombres rápidos (evitamos queries pesadas aquí)
                    tipos_nombres = ", ".join([str(tid) for tid in d.tipos])
            except Exception:
                tipos_nombres = ""
            return {
                "codigo": getattr(d, 'codigo', '') or "",
                "nombre": getattr(d, 'nombre', '') or "",
                "coleccion_nombre": col.nombre if col else "",
                "sufijo_nombre": suf.nombre if suf else "",
                "tipos_nombres": tipos_nombres,
                "total_producido": 0,
                "_obj": d,
            }
        except Exception:
            return {"codigo": "", "nombre": str(d), "coleccion_nombre": "", "sufijo_nombre": "", "tipos_nombres": "", "total_producido": 0, "_obj": d}

    def _on_buscar_diseno_enter(self, event=None):
        texto = self.entry_buscar_diseno.get()
        try:
            self.design_list.search(texto)
        except Exception:
            pass
        try:
            nav = getattr(self.design_list, 'nav_list', None)
            if nav:
                nav._canvas.focus_set()
        except Exception:
            pass
        return "break"

    def _on_diseno_double_click(self, data: dict):
        diseno = data.get("_obj") if data else None
        if not diseno:
            return
        self.diseno_seleccionado = diseno
        display = f"{getattr(diseno, 'codigo', '')} - {getattr(diseno, 'nombre', '')}".strip(" -")
        self.entry_diseno.configure(state="normal")
        self.entry_diseno.delete(0, "end")
        self.entry_diseno.insert(0, display)
        self.entry_diseno.configure(state="readonly")

    def _on_diseno_return(self):
        nav = getattr(self.design_list, 'nav_list', None)
        if nav:
            data = nav.get_selected_data()
            if data:
                self._on_diseno_double_click(data)

    # ----------------- Guardar / Cancelar -----------------

    def _on_guardar(self):
        if not self.producto_actual:
            return

        # Validaciones mínimas
        variante_id = self.combo_variante.get_id()
        if not variante_id:
            show_warning(self, "DEBES SELECCIONAR UNA VARIANTE")
            return

        if not self.diseno_seleccionado:
            show_warning(self, "DEBES SELECCIONAR UN DISEÑO (doble clic en la lista)")
            return

        try:
            cantidad = int(self.entry_cantidad.get().strip() or "1")
            if cantidad <= 0:
                raise ValueError()
        except Exception:
            show_warning(self, "CANTIDAD INVÁLIDA")
            return

        requiere_talla = bool(getattr(self.tipo_actual, 'requiere_talla', False)) if self.tipo_actual else False
        requiere_color = bool(getattr(self.tipo_actual, 'requiere_color', False)) if self.tipo_actual else False

        talla_id = self.combo_talla.get_id() if requiere_talla else None
        color_id = self.combo_color.get_id() if requiere_color else None

        diseno_codigo = getattr(self.diseno_seleccionado, 'codigo', None)

        comentarios = self.text_comentarios.get("1.0", "end").strip()

        datos = {
            "producto_id": self.producto_actual.get("producto_id"),
            "nombre": self.producto_actual.get("nombre"),
            "tipo_id": self.tipo_actual.id if self.tipo_actual else None,
            "variante_id": variante_id,
            "talla_id": talla_id,
            "color_id": color_id,
            "diseno_codigo": diseno_codigo,
            "cantidad": cantidad,
            "comentarios": comentarios,
            "ticket_id": self.ticket_id,
        }

        try:
            store = ReposicionStore()
            ok = store.añadir(datos)
            if not ok:
                show_error(self, "ERROR AL GUARDAR EN REPOS (JSON)")
                return
        except Exception:
            logger.exception("Error guardando en ReposicionStore")
            show_error(self, "ERROR AL GUARDAR")
            return

        show_success(self, "REPOSICIÓN ANOTADA")

        # Siguiente o fin
        self.indice_actual += 1
        self._cargar_siguiente_producto()

    def _on_cancelar(self):
        self._finalizar()

    def _finalizar(self):
        if self.callback_finalizar:
            try:
                self.callback_finalizar()
            except Exception:
                pass
        if self.view and hasattr(self.view, "pop_subview"):
            try:
                self.view.pop_subview()
            except Exception:
                pass
        else:
            try:
                self.destroy()
            except Exception:
                pass

