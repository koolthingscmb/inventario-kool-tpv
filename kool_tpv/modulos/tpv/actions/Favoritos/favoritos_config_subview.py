"""
FavoritosConfigSubView - Editor de la lista de favoritos.
Permite añadir, quitar, renombrar y ordenar los productos.
"""
import customtkinter as ctk
import logging
from typing import Optional

from kool_tpv.utils.factories.button_factory import ButtonFactory
from kool_tpv.utils.config_loader import create_action_button, load_layout_config
from .favoritos_service import FavoritosService
from kool_tpv.utils.widgets.virtual_nav_list import VirtualNavList
from kool_tpv.utils.dialogs.input_dialog import InputDialog

logger = logging.getLogger(__name__)

class FavoritosConfigSubView(ctk.CTkFrame):
    def __init__(self, parent, db, view=None, on_close_callback=None, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.db = db
        self.view = view
        self.on_close_callback = on_close_callback
        self.favoritos_service = FavoritosService(self.db)
        
        self._setup_ui()
        self.refrescar_lista()

    def _setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # 1. Header (Cerrar / Volver)
        header_frame = ctk.CTkFrame(self, fg_color="transparent", height=60)
        header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        header_frame.grid_propagate(False)
        
        # Botón Volver (Usando estilo de config si es posible, sino ButtonFactory)
        self.btn_back = ButtonFactory.create_button(
            parent=header_frame,
            text="< VOLVER",
            command=self.on_close_callback,
            style_key="action_secondary",
            width=120,
            height=40
        )
        self.btn_back.pack(side="left", padx=5)
        
        ctk.CTkLabel(
            header_frame,
            text="CONFIGURACIÓN DE FAVORITOS",
            font=("Courier New", 20, "bold"),
            text_color="#00FF00"
        ).pack(side="left", padx=20)

        # 2. Área Central (Lista a la izquierda, Controles a la derecha)
        content_frame = ctk.CTkFrame(self, fg_color="transparent")
        content_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        content_frame.grid_columnconfigure(0, weight=4) # Lista
        content_frame.grid_columnconfigure(1, weight=1) # Controles
        content_frame.grid_rowconfigure(0, weight=1)

        # 2.1 Lista de Favoritos (VirtualNavList)
        columns = [
            ("posicion", 50, "#"),
            ("nombre_favorito", 250, "NOMBRE BOTÓN"),
            ("nombre_producto", 250, "PRODUCTO REAL"),
            ("pvp", 100, "PVP")
        ]
        
        root = self.winfo_toplevel()
        _km = getattr(root, 'keyboard_manager', None)
        
        self.nav_list = VirtualNavList(
            parent=content_frame,
            columns=columns,
            module_name="tpv",
            keyboard_manager=_km,
            layout_config=load_layout_config()
        )
        self.nav_list.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        # 2.2 Panel de Controles
        controls_frame = ctk.CTkFrame(content_frame, fg_color="#1a1a1a")
        controls_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        
        # Botones de Acción
        btn_width = 160
        
        # Añadir (Abre Stock)
        self.btn_add = ButtonFactory.create_button(
            parent=controls_frame,
            text="➕ AÑADIR",
            command=self._abrir_selector_stock,
            style_key="action_primary",
            width=btn_width
        )
        self.btn_add.pack(pady=10)
        
        # Renombrar
        self.btn_rename = ButtonFactory.create_button(
            parent=controls_frame,
            text="✏️ RENOMBRAR",
            command=self._renombrar_favorito,
            style_key="action_secondary",
            width=btn_width
        )
        self.btn_rename.pack(pady=10)

        # Auto-orden (Mágico)
        self.btn_auto = ButtonFactory.create_button(
            parent=controls_frame,
            text="🪄 AUTO-ORDEN",
            command=self._ejecutar_auto_orden,
            style_key="action_secondary",
            width=btn_width
        )
        self.btn_auto.pack(pady=10)

        # Separador visual
        ctk.CTkFrame(controls_frame, height=2, fg_color="#333333").pack(fill='x', padx=10, pady=20)

        # Subir
        self.btn_up = ButtonFactory.create_button(
            parent=controls_frame,
            text="🔼 SUBIR",
            command=lambda: self._mover(subir=True),
            style_key="action_secondary",
            width=btn_width
        )
        self.btn_up.pack(pady=10)
        
        # Bajar
        self.btn_down = ButtonFactory.create_button(
            parent=controls_frame,
            text="🔽 BAJAR",
            command=lambda: self._mover(subir=False),
            style_key="action_secondary",
            width=btn_width
        )
        self.btn_down.pack(pady=10)

        # Separador visual
        ctk.CTkFrame(controls_frame, height=2, fg_color="#333333").pack(fill='x', padx=10, pady=20)

        # Eliminar
        self.btn_delete = ButtonFactory.create_button(
            parent=controls_frame,
            text="🗑️ ELIMINAR",
            command=self._eliminar_favorito,
            style_key="action_danger",
            width=btn_width
        )
        self.btn_delete.pack(side="bottom", pady=20)

    def refrescar_lista(self):
        items = self.favoritos_service.listar_favoritos()
        self.nav_list.set_items(items)

    def _abrir_selector_stock(self):
        """Abre la vista de Stock en modo selección."""
        from kool_tpv.modulos.tpv.subviews.stock_subview import StockSubView
        
        def on_selected(producto):
            if producto:
                res = self.favoritos_service.agregar_a_favoritos(
                    producto_id=producto.get('id'),
                    nombre=producto.get('nombre')
                )
                if res.get('duplicado'):
                    from kool_tpv.utils.widgets.notificaciones import ToastWidget
                    ToastWidget.show(self.winfo_toplevel(), "EL PRODUCTO YA ES UN FAVORITO", tipo="warning")
                else:
                    self.refrescar_lista()

        stock_view = StockSubView(
            parent=self.view.center_area,
            db=self.db,
            carrito_service=None, # No necesario en modo selección
            view=self.view,
            on_select_callback=on_selected
        )
        self.view.push_subview(stock_view, "SELECCIONAR PRODUCTO")

    def _renombrar_favorito(self):
        selected = self.nav_list.get_selected_data()
        if not selected:
            return

        def on_rename(nuevo_nombre):
            if nuevo_nombre:
                self.favoritos_service.actualizar_nombre(selected['id'], nuevo_nombre)
                self.refrescar_lista()

        InputDialog(
            self.view,
            titulo="RENOMBRAR BOTÓN",
            mensaje=f"NOMBRE ACTUAL: {selected['nombre_favorito']}",
            valor_defecto=selected['nombre_favorito'],
            callback=on_rename
        )

    def _mover(self, subir: bool):
        selected = self.nav_list.get_selected_data()
        if not selected:
            return
        
        if self.favoritos_service.cambiar_posicion(selected['id'], subir=subir):
            # Guardar el ID para re-seleccionar después de refrescar
            sid = selected['id']
            self.refrescar_lista()
            
            # Intentar re-seleccionar en la nueva posición
            items = self.nav_list._all_data
            for i, itm in enumerate(items):
                if itm['id'] == sid:
                    self.nav_list._select(i)
                    break

    def _ejecutar_auto_orden(self):
        """Ejecuta la reorganización por ventas después de confirmar."""
        from kool_tpv.utils.custom_dialog import show_warning
        from kool_tpv.utils.widgets.notificaciones import ToastWidget
        
        def on_confirm(res):
            if res:
                if self.favoritos_service.auto_ordenar_por_ventas():
                    self.refrescar_lista()
                    ToastWidget.show(self.view, 'LISTA REORGANIZADA POR VENTAS', tipo='success')
                else:
                    ToastWidget.show(self.view, 'NO SE PUDO REORGANIZAR LA LISTA', tipo='warning')

        show_warning(
            self.view,
            "🪄 AUTO-ORDENAR",
            "¿QUIERES ORDENAR TUS FAVORITOS POR VOLUMEN DE VENTAS?\n\n(LOS MÁS VENDIDOS APARECERÁN PRIMERO)",
            callback=on_confirm,
            confirm=True
        )

    def _eliminar_favorito(self):
        selected = self.nav_list.get_selected_data()
        if not selected:
            return
            
        from kool_tpv.utils.custom_dialog import show_warning
        
        def on_confirm(res):
            if res:
                self.favoritos_service.eliminar_de_favoritos(selected['id'])
                self.refrescar_lista()

        show_warning(
            self.view,
            "QUITAR FAVORITO",
            f"¿QUIERES QUITAR '{selected['nombre_favorito']}' DE LA LISTA?",
            callback=on_confirm,
            confirm=True
        )
