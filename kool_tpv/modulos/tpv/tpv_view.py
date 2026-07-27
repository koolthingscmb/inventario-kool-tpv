"""
ARCHIVO ACTIVO DEL TPV.
Cualquier desarrollo debe realizarse aquí.
tpv_view_old.py está archivado en /archive.
"""

import customtkinter as ctk
import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# 1. SERVICIO CARRITO
from kool_tpv.modulos.tpv.carrito.carrito_service import CarritoService

# 2. IMPORTACIÓN EXACTA (SOLUCIÓN)
from kool_tpv.modulos.tpv.actions.Favoritos.favoritos_subview import FavoritosSubView
from kool_tpv.utils.widgets.notificaciones.toast_widget import ToastWidget

# --- RUTA CONFIG ---
BASE_DIR = Path(__file__).resolve().parents[2] 
CONFIG_DIR = BASE_DIR / "config"

# Central ButtonFactory
from kool_tpv.utils.factories.button_factory import ButtonFactory
from kool_tpv.utils.keyboard_nav_mixin import KeyboardNavigableMixin
from kool_tpv.utils.scale_manager import get_scale_manager
from kool_tpv.utils.config_loader import load_colors

def load_config(filename: str) -> dict:
    try:
        with open(CONFIG_DIR / filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

class ClickableBreadcrumb(ctk.CTkFrame):
    def __init__(self, parent, font=None, text_color="white", bg_color="transparent", **kwargs):
        super().__init__(parent, fg_color=bg_color, **kwargs)
        self.custom_font = font
        self.text_color = text_color

    def update_parts(self, parts: list):
        for widget in self.winfo_children():
            if widget is getattr(self, '_btn_cajon_ref', None):
                continue
            if widget is getattr(self, '_btn_reposicion_ref', None):
                continue
            if widget is getattr(self, '_btn_pedidos_ref', None):
                continue
            widget.destroy()
        for i, (text, callback) in enumerate(parts):
            if i > 0:
                ctk.CTkLabel(self, text='/', text_color=self.text_color, font=self.custom_font).pack(side='left', padx=4)
            if callback is None:
                ctk.CTkLabel(self, text=text, text_color=self.text_color, font=self.custom_font).pack(side='left', padx=2)
            else:
                btn = ctk.CTkButton(self, text=text, text_color=self.text_color, fg_color='transparent', hover_color='#333333', font=self.custom_font, command=callback, width=len(text) * 12, height=28, corner_radius=4, cursor='hand2')
                btn.pack(side='left', padx=2)

# use central ButtonFactory (imported above)

class TpvView(ctk.CTkFrame, KeyboardNavigableMixin):
    def __init__(self, parent, db=None):
        ctk.CTkFrame.__init__(self, parent)
        KeyboardNavigableMixin.__init_keyboard_mixin__(self)
        self.db = db

        # Referencia al servicio de configuración para observar cambios
        try:
            from kool_tpv.modulos.config.ui.services.ui_config_service import UIConfigService
            self.ui_config_service = UIConfigService()
            self.ui_config_service.registrar_observer("colors_config", self._on_colors_changed)
        except Exception:
            self.ui_config_service = None

        # Referencia al contenedor para diálogos (requerido por TpvController)
        self.container = self

        # INICIALIZAR EL SERVICIO
        self.carrito_service = CarritoService()

        # Configs
        self.layout_cfg = load_config("layout_config.json")
        self.font_cfg = load_config("font_config.json")

        # ScaleManager para densidad de interfaz
        self.scale_mgr = get_scale_manager(db)

        # PANEL DERECHO (TICKET) - Usar ancho real del JSON sin escalar para dar control total al usuario
        right_width = self.layout_cfg.get("modules", {}).get("tpv", {}).get("right_width", 600)
        self.right_container = ctk.CTkFrame(self, width=right_width, corner_radius=0, fg_color="#1a1a1a")
        self.right_container.pack(side="right", fill="y")
        self.right_container.pack_propagate(False)

        try:
            from kool_tpv.utils.widgets.ticket_carrito import TicketCarrito
            # Pasamos el servicio al ticket
            # Resolve keyboard manager from top-level (App) if available
            try:
                root = self.winfo_toplevel()
                km = getattr(root, 'keyboard_manager', None) or getattr(root, 'keyboard_mgr', None)
            except Exception:
                km = None

            self.ticket_widget = TicketCarrito(
                self.right_container,
                carrito_service=self.carrito_service,
                db=self.db,
                keyboard_manager=km
            )
            self.ticket_widget.pack(fill="both", expand=True)

            # Alias para compatibilidad con TpvController
            self.ticket_carrito = self.ticket_widget
        except ImportError:
            ctk.CTkLabel(self.right_container, text="[ ERROR TICKET ]", text_color="red").pack()

        # PANEL CENTRAL
        self.center_area = ctk.CTkFrame(self, corner_radius=0, fg_color="#222831")
        self.center_area.pack(side="left", fill="both", expand=True)

        bread_cfg = self.font_cfg.get("breadcrumb", {})
        bread_font_size = self.scale_mgr.get_font_size(bread_cfg.get("size", 20))
        bread_font = (bread_cfg.get("family", "Courier New"), bread_font_size, "bold")

        breadcrumb_height = self.scale_mgr.get_height(50)
        self.breadcrumb = ClickableBreadcrumb(self.center_area, font=bread_font, text_color="#00FF00", height=breadcrumb_height)
        self.breadcrumb.pack(side="top", fill="x", padx=20, pady=10)
        self.breadcrumb.update_parts([("INICIO", None), ("VENTAS", None), ("TPV", None)])

        self.btn_cajon = ButtonFactory.create_button(
            parent=self.breadcrumb,
            text="CAJÓN",
            command=self._abrir_cajon,
            style_key="almacen_outline",
            width=100,
            height=36,
            font=(bread_cfg.get("family", "Courier New"), 14, "bold")
        )
        self.btn_cajon.pack(side="right", padx=4)
        self.breadcrumb._btn_cajon_ref = self.btn_cajon

        self.btn_reposicion = ButtonFactory.create_button(
            parent=self.breadcrumb,
            text="REPOSICIÓN",
            command=self._abrir_reposicion,
            color="#000000",
            hover_color="#6C3483",
            text_color="#9B59B6",
            border_color="#9B59B6",
            border_width=2,
            corner_radius=12,
            width=130,
            height=36,
            font=(bread_cfg.get("family", "Courier New"), 14, "bold")
        )
        self.btn_reposicion.pack(side="right", padx=4)
        self.breadcrumb._btn_reposicion_ref = self.btn_reposicion

        self.btn_pedidos = ButtonFactory.create_button(
            parent=self.breadcrumb,
            text="PEDIDOS",
            command=self._abrir_pedidos,
            color="#000000",
            hover_color="#827314",
            text_color="#E3C509",
            border_color="#E3C509",
            border_width=2,
            corner_radius=12,
            width=100,
            height=36,
            font=(bread_cfg.get("family", "Courier New"), 14, "bold")
        )
        self.btn_pedidos.pack(side="right", padx=4)
        self.breadcrumb._btn_pedidos_ref = self.btn_pedidos

        self.grid_frame = ctk.CTkFrame(self.center_area, fg_color="transparent")
        self.grid_frame.pack(side="top", fill="both", expand=True, padx=20, pady=20)

        # Lista para referencias a botones del grid (requerido por button_action_mapper)
        self.grid_buttons = []
        # Stack para sub-vistas dinámicas (push/pop views)
        self._subview_stack = []

        self._build_grid_buttons()
        
        # Configurar navegación por teclado para los botones del grid
        self._setup_grid_keyboard_navigation()
        
        # Instanciar controlador (gestiona payment controllers, acciones y rebind de botones)
        try:
            from kool_tpv.modulos.tpv.tpv_controller import TpvController
            self.controller = TpvController(self, db=self.db)
        except Exception:
            # No queremos que la vista deje de inicializarse si el controlador falla
            self.controller = None

        # Registrar handler de power del TPV (prioriza pop de subviews)
        try:
            root = self.winfo_toplevel()
            if hasattr(root, "register_power_handler"):
                root.register_power_handler(self._handle_power, owner=self)
        except Exception:
            pass

        # Crear controlador (gestiona payment controllers, acciones y rebind)

    def _build_grid_buttons(self):
        cols = 4
        rows = 4
        for i in range(cols): self.grid_frame.grid_columnconfigure(i, weight=1)
        for i in range(rows): self.grid_frame.grid_rowconfigure(i, weight=1)

        # Cargar colores de TPV
        tpv_colors = load_colors('tpv').get('grid_buttons', {})

        # Read buttons from layout_config.json -> modules.tpv.center.grid.buttons
        buttons = self.layout_cfg.get("modules", {}).get("tpv", {}).get("center", {}).get("grid", {}).get("buttons", [])

        for index, btn_data in enumerate(buttons):
            row = btn_data.get("row")
            col = btn_data.get("col")
            columnspan = btn_data.get("colspan", 1)
            rowspan = btn_data.get("rowspan", 1)

            # preserve command mapping for favoritos
            cmd_name = btn_data.get("command")
            cmd = self._mostrar_favoritos if cmd_name == "favoritos" else None
            label = btn_data.get("label", "???")
            shortcut = btn_data.get("shortcut", "")
            display_text = f"{label}\n({shortcut})" if shortcut else label

            # Determinar overrides de color desde colors_config.json
            color_key = cmd_name if cmd_name else label.lower().replace(" ", "_")
            # Mapeos especiales si el command no coincide con la clave en colors_config
            if color_key == "favoritos": color_key = "buscar_articulo"
            elif color_key == "Pagar en Efectivo": color_key = "cash"
            elif color_key == "Pagar con Tarjeta": color_key = "tarjeta"
            elif color_key == "Pagar en Web": color_key = "web"
            elif color_key == "Multicobro": color_key = "multi"
            elif color_key == "Cierres de caja": color_key = "cierre"
            elif color_key == "Hacer dto directo o %": color_key = "descuento"
            elif color_key == "Realizar Devolución": color_key = "devolucion"
            elif color_key == "Asignar Cajero": color_key = "cajero"
            elif color_key == "Asignar Cliente": color_key = "cliente"
            elif color_key == "Abrir Tickets": color_key = "tickets"
            
            # Limpiar color_key por si acaso
            color_key = color_key.lower().replace(" ", "_")
            
            spec = tpv_colors.get(color_key, {})
            
            overrides = {}
            if spec.get("bg"): overrides["color"] = spec["bg"]
            if spec.get("text"): overrides["text_color"] = spec["text"]
            if spec.get("hover"): overrides["hover_color"] = spec["hover"]
            if spec.get("border"): overrides["border_color"] = spec["border"]
            if spec.get("border_width") is not None: overrides["border_width"] = spec["border_width"]

            btn = ButtonFactory.create_button(
                parent=self.grid_frame,
                text=display_text,
                command=cmd,
                style_key=btn_data.get("style_key"),
                **overrides
            )

            btn.grid(row=row, column=col, columnspan=columnspan, rowspan=rowspan, padx=10, pady=10, sticky="nsew")
            # Guardar referencia para mapper (lista de widgets, como espera el mapper)
            self.grid_buttons.append(btn)

    def _setup_grid_keyboard_navigation(self):
        """Configurar navegación por teclado para los botones del grid principal (lista interna)."""
        # Poblar lista navegable con TODOS los botones del grid
        # Los callbacks se actualizarán dinámicamente en _execute_nav_command
        self._navigable_buttons = []
        for btn in self.grid_buttons:
            # Usar un wrapper que obtiene el comando actual del botón
            wrapped_callback = lambda b=btn: self._execute_nav_command(b)
            self._navigable_buttons.append((btn, wrapped_callback))
        
        # Activar navegación si hay botones
        if self._navigable_buttons:
            self._setup_keyboard_navigation()

    def _execute_nav_command(self, btn):
        """Ejecutar el comando actual de un botón (obtenido dinámicamente)."""
        try:
            cmd = btn.cget("command")
            if callable(cmd):
                cmd()
        except Exception:
            pass

    def _on_colors_changed(self, data: dict):
        """Callback cuando cambian los colores en la configuración."""
        try:
            # Re-construir los botones del grid con los nuevos colores
            self.clear_grid()
            self._build_grid_buttons()
            self._setup_grid_keyboard_navigation()
            
            # Rebind de comandos (el controlador se encarga de esto normalmente)
            if self.controller:
                from kool_tpv.modulos.tpv.button_action_mapper import rebind_buttons
                rebind_buttons(self)
                
            logger.info("Botones del TPV actualizados por cambio de configuración")
        except Exception:
            logger.exception("Error actualizando botones del TPV tras cambio de colores")

    def teardown(self):
        # Desvincular observer
        if self.ui_config_service:
            try:
                self.ui_config_service.eliminar_observer("colors_config", self._on_colors_changed)
            except Exception:
                pass

        try:
            if self.controller and hasattr(self.controller, '_barcode_service') and self.controller._barcode_service:
                self.controller._barcode_service.detach()
        except Exception:
            pass
        try:
            if self.controller and hasattr(self.controller, '_keyboard_shortcuts') and self.controller._keyboard_shortcuts:
                self.controller._keyboard_shortcuts.detach()
        except Exception:
            pass

    def clear_grid(self):
        """Eliminar todos los widgets del grid y resetear referencias."""
        # Limpiar navegación por teclado primero
        try:
            self.clear_keyboard_navigation()
        except Exception:
            pass
            
        try:
            if hasattr(self, 'grid_frame') and self.grid_frame is not None:
                for widget in list(self.grid_frame.winfo_children()):
                    try:
                        widget.destroy()
                    except Exception:
                        try:
                            widget.grid_forget()
                        except Exception:
                            pass

            # Reset referencias a botones
            try:
                self.grid_buttons = []
            except Exception:
                pass
        except Exception:
            # No queremos que limpiar el grid lance excepciones
            try:
                import logging
                logging.exception('Error en clear_grid')
            except Exception:
                pass

    def push_subview(self, view_instance, title: str):
        """Mostrar una sub-vista encima del grid (guardando en stack)."""
        try:
            # Ocultar vista actual si existe
            if self._subview_stack:
                current_view = self._subview_stack[-1]["view"]
                try:
                    current_view.pack_forget()
                except Exception:
                    pass
            else:
                # Si estamos en el grid base, ocultar el frame del grid completamente
                try:
                    self.grid_frame.pack_forget()
                except Exception:
                    pass

            # Mostrar nueva vista
            try:
                view_instance.pack(side="top", fill="both", expand=True)
                try:
                    pass
                except Exception:
                    pass
            except Exception:
                pass

            self._subview_stack.append({"view": view_instance, "title": title})
            try:
                self._update_breadcrumb()
            except Exception:
                pass
        except Exception:
            try:
                import logging
                logging.exception('Error en push_subview')
            except Exception:
                pass

    def _abrir_reposicion(self):
        """Abrir subvista de reposiciones pendientes."""
        try:
            from kool_tpv.modulos.tpv.services.reposicion_store import ReposicionStore
            from kool_tpv.modulos.tpv.subviews.reposicion_pendientes_ui import ReposicionPendientesUI
            
            store = ReposicionStore()
            pendientes_temp = store.cargar_pendientes_temp()
            configurados = store.cargar()
            if not pendientes_temp and not configurados:
                from kool_tpv.utils.widgets.notificaciones import show_info
                show_info(self.winfo_toplevel(), "NO HAY REPOSICIONES PENDIENTES")
                return
            
            # Abrir subvista de lista de pendientes
            view = ReposicionPendientesUI(
                parent=self.center_area, 
                db=self.db,
                carrito_service=self.carrito_service,
                view=self
            )
            self.push_subview(view, "REPOSICIONES PENDIENTES")
            
        except Exception:
            logging.exception("Error al abrir reposición")

    def _abrir_pedidos(self):
        """Abrir subvista de pedidos de clientes."""
        try:
            from kool_tpv.modulos.clientes.pedidos_ui import PedidosUI
            
            # Obtener keyboard manager si existe
            km = None
            try:
                root = self.winfo_toplevel()
                km = getattr(root, 'keyboard_manager', None) or getattr(root, 'keyboard_mgr', None)
            except Exception: pass

            pedidos_ui = PedidosUI(
                parent=self.center_area,
                db=self.db,
                owner=self,
                module_name='clientes',
                keyboard_manager=km
            )
            
            # PedidosUI.get_widget() devuelve el frame contenedor
            widget = pedidos_ui.get_widget()
            self.push_subview(widget, "PEDIDOS CLIENTES")
            
        except Exception:
            logging.exception("Error al abrir pedidos desde TPV")

    def show_crear_pedido(self, cliente_id: Optional[int] = None, pedido_id: Optional[int] = None):
        """Método requerido por PedidosUI para abrir la edición/creación."""
        try:
            from kool_tpv.modulos.clientes.crear_pedido_ui import CrearPedidoUI
            
            # Obtener keyboard manager
            km = None
            try:
                root = self.winfo_toplevel()
                km = getattr(root, 'keyboard_manager', None) or getattr(root, 'keyboard_mgr', None)
            except Exception: pass

            crear_ui = CrearPedidoUI(
                parent=self.center_area,
                db=self.db,
                owner=self,
                keyboard_manager=km,
                cliente_inicial_id=cliente_id,
                pedido_id=pedido_id
            )
            
            # CrearPedidoUI no es un widget, hay que obtener su contenedor
            widget = crear_ui.get_widget()
            titulo = "MODIFICAR PEDIDO" if pedido_id else "NUEVO PEDIDO"
            self.push_subview(widget, titulo)
            
        except Exception:
            logging.exception("Error al abrir creación de pedido desde TPV")

    def show_pedidos(self):
        """Método requerido por CrearPedidoUI para volver al listado."""
        self.pop_subview()

    def _abrir_cajon(self):
        """Abrir el cajón del dinero vía comando ESC/POS."""
        try:
            from kool_tpv.modulos.tpv.actions.permisos import check_permiso
            parent = None
            try:
                parent = self.winfo_toplevel()
            except Exception:
                parent = self
            if not check_permiso(self.carrito_service, 'permiso_cajon', parent):
                return

            from kool_tpv.modulos.tpv.actions.cajon import abrir_cajon
            abrir_cajon(db=self.db)
        except Exception:
            logging.exception("Error al abrir cajón")

    def _mostrar_favoritos(self):
        """Mostrar subvista de favoritos (reemplaza el grid)."""
        def refresh_ticket():
            try:
                ticket = getattr(self, 'ticket_widget', None) or getattr(self, 'ticket_carrito', None) or getattr(self, 'ticket', None)
                if ticket and hasattr(ticket, 'update_carrito'):
                    ticket.update_carrito()
            except Exception:
                pass
        
        def show_config():
            from kool_tpv.modulos.tpv.actions.Favoritos.favoritos_config_subview import FavoritosConfigSubView
            
            def on_config_closed():
                self.pop_subview()
                # Refrescar los botones de favoritos al volver
                current_view = self._subview_stack[-1]["view"]
                if hasattr(current_view, 'cargar_favoritos'):
                    current_view.cargar_favoritos()

            config_view = FavoritosConfigSubView(
                self.center_area,
                db=self.db,
                view=self,
                on_close_callback=on_config_closed
            )
            self.push_subview(config_view, "Configuración Favoritos")

        fav_view = FavoritosSubView(
            self.center_area,
            db=self.db,
            carrito_service=self.carrito_service,
            on_add_callback=refresh_ticket,
            on_close_callback=self.pop_subview,
            on_edit_callback=show_config
        )
        self.push_subview(fav_view, "Favoritos")

    def pop_subview(self):
        """Cerrar la sub-vista actual y mostrar la anterior (o el grid base)."""
        try:
            if not self._subview_stack:
                return

            # Destruir vista actual
            current = self._subview_stack.pop()
            try:
                current["view"].destroy()
            except Exception:
                try:
                    current["view"].pack_forget()
                except Exception:
                    pass

            # Mostrar anterior
            if self._subview_stack:
                previous = self._subview_stack[-1]["view"]
                try:
                    previous.pack(fill="both", expand=True)
                except Exception:
                    pass
                try:
                    pass
                except Exception:
                    pass
            else:
                # Volver al grid base: volver a mostrar el frame del grid y reconstruir botones
                try:
                    self.grid_frame.pack(side="top", fill="both", expand=True, padx=20, pady=20)
                    self.clear_grid()
                    self._build_grid_buttons()
                    if hasattr(self, "controller") and self.controller:
                        self.controller.rebind_buttons()
                    # Reconfigurar navegación por teclado después de reconstruir
                    self._setup_grid_keyboard_navigation()
                except Exception:
                    pass
                try:
                    pass
                except Exception:
                    pass

            try:
                self._update_breadcrumb()
            except Exception:
                pass
        except Exception:
            try:
                import logging
                logging.exception('Error en pop_subview')
            except Exception:
                pass

    def _update_breadcrumb(self):
        """Actualizar breadcrumb reflejando stack de sub-vistas."""
        try:
            parts = [("TPV", None)]
            for item in self._subview_stack:
                try:
                    parts.append((item.get("title", ""), None))
                except Exception:
                    parts.append(("?", None))

            try:
                self.breadcrumb.update_parts(parts)
            except Exception:
                pass
        except Exception:
            try:
                import logging
                logging.exception('Error en _update_breadcrumb')
            except Exception:
                pass

    def _on_power(self):
        """Handler de power específico para TPV.

        Prioriza cerrar sub-vistas apiladas (`_subview_stack`) llamando a
        `pop_subview()` si existe alguna. Si no hay sub-vistas, intenta
        limpiar `center_area` como comportamiento de fallback.
        """
        try:
            # Si hay sub-vistas en el stack, cerramos la última y retornamos
            if hasattr(self, '_subview_stack') and self._subview_stack:
                try:
                    self.pop_subview()
                except Exception:
                    pass
                return True

            # Fallback: si el área central tiene widgets, los removemos
            if hasattr(self, 'center_area') and self.center_area.winfo_children():
                try:
                    for w in list(self.center_area.winfo_children()):
                        try:
                            w.destroy()
                        except Exception:
                            try:
                                w.pack_forget()
                            except Exception:
                                pass
                except Exception:
                    pass

                try:
                    # Actualizar breadcrumb si procede
                    if hasattr(self, '_update_breadcrumb'):
                        self._update_breadcrumb()
                except Exception:
                    pass

                return True

            return False
        except Exception:
            try:
                import logging
                logging.exception('Error en _on_power (TPV)')
            except Exception:
                pass
            return False

    def _handle_power(self):
        # 1. Prioridad: cerrar sub-vistas (favoritos, etc)
        if hasattr(self, "_subview_stack") and self._subview_stack:
            try:
                self.pop_subview()
            except Exception:
                pass
            return True

        # 2. Bloqueo si hay carrito con productos
        if hasattr(self, 'carrito_service') and not self.carrito_service.is_empty():
            ToastWidget.show(self, "NO SE PUEDE SALIR DEL TPV CON UNA OPERACIÓN EN CURSO", tipo='error')
            return True

        return False