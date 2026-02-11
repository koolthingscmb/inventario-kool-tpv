"""kool_tpv.modulos.tpv.tpv_view

Vista estática y receptiva del módulo TPV.

Características principales:
- `BUTTON_CONFIG` editable en la parte superior para texto y color.
- Botón de búsqueda (botón ancho, no entrada) con tamaño base ~1000x60 pero responsive.
- Grid de 4x3 botones grandes (texto en mayúsculas).
- Comportamiento responsive: los botones y las fuentes escalan al redimensionar.
- `show()` construye la vista, `teardown()` cancela tareas y unbinds.

Diseñado para ser legible y modificable; no incluye lógica de negocio.
"""

from __future__ import annotations
from datetime import datetime
from typing import Optional, List, Dict
import logging
import json
from pathlib import Path
from decimal import Decimal
try:
    from kool_tpv.modulos.impresion.impresora_service import ImpresoraService
except Exception:
    ImpresoraService = None

import customtkinter as ctk
import tkinter as tk
from kool_tpv.utils.custom_dialog import show_error, show_success, show_info, show_warning
from kool_tpv.modulos.tpv.actions.descuento import DescuentoAction


# --- Configuración editable de botones (texto y color). Modifica aquí. ---
BUTTON_CONFIG: List[Dict[str, str]] = [
    {"text": "COBRAR", "color": "#E27D60"},
    {"text": "PENDIENTE", "color": "#C38D9E"},
    {"text": "DESCUENTO", "color": "#41B3A3"},
    {"text": "CLIENTE", "color": "#6B5B95"},
    {"text": "PRODUCTOS", "color": "#FF6F61"},
    {"text": "CANCELAR", "color": "#F7CAC9"},
    {"text": "BUSCAR", "color": "#92A8D1"},
    {"text": "REIMPRIMIR", "color": "#034F84"},
    {"text": "RECARGO", "color": "#F7B32B"},
    {"text": "IMPRIMIR", "color": "#88B04B"},
    {"text": "CONFIG", "color": "#6C5B7B"},
    {"text": "OTROS", "color": "#2E8B57"},
]


def load_button_config_from_json() -> List[Dict]:
    """Attempt to read button definitions from kool_tpv/config/buttons_config.json.

    Returns a list of button config dicts. If the file is missing or invalid,
    returns the in-code BUTTON_CONFIG as fallback (mapped to same shape).
    """
    try:
        base = Path(__file__).resolve().parents[2]  # kool_tpv/
        cfg_file = base / "config" / "buttons_config.json"
        if cfg_file.exists():
            with cfg_file.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            buttons = data.get("buttons") or []
            parsed = []
            for b in buttons:
                parsed.append(
                    {
                        "text": b.get("label", ""),
                        "color": b.get("color", "#CCCCCC"),
                        "hover_color": b.get("hover_color"),
                        "font_size": b.get("font_size"),
                        "width": b.get("width"),
                        "height": b.get("height"),
                        "command": b.get("command"),
                    }
                )
            if parsed:
                return parsed
    except Exception:
        logging.exception("Error leyendo buttons_config.json")

    # Fallback: map BUTTON_CONFIG to expected shape
    fallback = []
    for b in BUTTON_CONFIG:
        fallback.append({
            "text": b.get("text"),
            "color": b.get("color"),
            "hover_color": None,
            "font_size": None,
            "width": None,
            "height": None,
            "command": None,
        })
    return fallback

# Tamaños base / constantes
RIGHT_WIDTH = 420
INFO_BAR_HEIGHT = 90
# Hover color shared with main navigation
HOVER_COLOR = "#00A4DF"


class ButtonFactory:
    """Factory simple para crear botones reutilizables en TPV.

    - Convierte `text` a mayúsculas automáticamente.
    - Todos los parámetros de estilo son modificables desde el llamador.
    """

    @staticmethod
    def create_button(
        parent,
        text: str,
        command=None,
        font=("Roboto-SemiBold", 14),
        color="#FFFFFF",
        text_color="black",
        hover_color=None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        corner_radius: int = 12,
        **kwargs,
    ) -> ctk.CTkButton:
        # Use shared HOVER_COLOR when none provided
        _hover = hover_color if hover_color is not None else HOVER_COLOR
        params = dict(
            master=parent,
            text=(text or "").upper(),
            command=command,
            fg_color=color,
            hover_color=_hover,
            text_color=text_color,
            font=font,
            corner_radius=corner_radius,
        )
        # Only include width/height when explicitly provided (avoid passing None)
        if width is not None:
            params["width"] = width
        if height is not None:
            params["height"] = height

        params.update(kwargs)
        return ctk.CTkButton(**params)


class TpvView:
    """Vista TPV responsiva y limpia.

    Uso:
        view = TpvView(parent_frame, db=optional_db)
        view.show()
        view.teardown()  # al cerrar la vista
    """

    def __init__(self, parent: ctk.CTkFrame, db: Optional[object] = None):
        self.parent = parent
        self.db = db
        self._clock_job = None
        self.info_label: Optional[ctk.CTkLabel] = None
        self._resize_bound = False

        # Referencias a widgets que necesitamos actualizar/teardown
        self.action_panel: Optional[ctk.CTkFrame] = None
        self.right_container: Optional[ctk.CTkFrame] = None
        self.grid_frame: Optional[ctk.CTkFrame] = None
        self.search_button: Optional[ctk.CTkButton] = None
        self.grid_buttons: List[ctk.CTkButton] = []
        # Sesión de cajero
        self.cajero_nombre = None
        self.cajero_id = None
        self.cajero_rol = None

    def _on_producto_stock_selected(self, producto: Dict) -> None:
        """Callback cuando se selecciona producto desde StockUI (doble clic o Aceptar).

        Añade el producto al carrito automáticamente.

        Args:
            producto: Dict con datos del producto
        """
        try:
            if not producto or not producto.get('id'):
                logging.warning('Producto inválido recibido en callback stock')
                return

            # Añadir al carrito usando carrito_service
            if hasattr(self, 'carrito_service') and self.carrito_service is not None:
                try:
                    self.carrito_service.add_item(producto)
                    logging.info(f"Producto añadido desde STOCK: {producto.get('nombre')}")

                    # Actualizar display del carrito
                    if hasattr(self, 'carrito_ui') and self.carrito_ui is not None:
                        try:
                            self.carrito_ui.update_display()
                        except Exception:
                            logging.exception('Error actualizando carrito_ui tras añadir desde stock')
                except Exception:
                    logging.exception('Error añadiendo producto al carrito desde stock')

        except Exception:
            logging.exception('Error en _on_producto_stock_selected')

    def _open_cajero_overlay(self) -> None:
        """Abrir el overlay/acción de Cajero para autenticación.

        Intenta reutilizar la instancia de `CajeroAction` si existe,
        o instanciarla como fallback.
        """
        try:
            if getattr(self, '_cajero_action', None) is not None:
                try:
                    # `ejecutar` es el método usado por los botones para abrir el overlay
                    self._cajero_action.ejecutar()
                    return
                except Exception:
                    logging.exception('Error ejecutando _cajero_action.ejecutar()')

            # Fallback: intentar instanciar y ejecutar
            try:
                from kool_tpv.modulos.tpv.actions.cajero import CajeroAction
                caj = CajeroAction(self, self.db)
                try:
                    caj.ejecutar()
                except Exception:
                    logging.exception('Error ejecutando CajeroAction fallback')
            except Exception:
                logging.exception('No se pudo abrir overlay de Cajero (no disponible)')
        except Exception:
            logging.exception('Error en _open_cajero_overlay')
    # Ticket viewer methods removed in rollback: Stock→Consultar→Volver (sin visor)

    # ---------------------- Reloj y teardown ----------------------
    def _update_clock(self, cashier_name: str = None) -> None:
        try:
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Usar cajero actual si está autenticado, sino usar el pasado por parámetro
            cajero_actual = getattr(self, 'cajero_nombre', None) or cashier_name or "Sin cajero"

            info_text = f"KOOL TPV V1.0 - {now_str}\nCajero: {cajero_actual}"
            if self.info_label:
                self.info_label.configure(text=info_text)
            # programar siguiente actualización
            if self.parent is not None:
                self._clock_job = self.parent.after(1000, lambda: self._update_clock())
        except Exception:
            logging.exception("Error actualizando reloj TPV")

    def teardown(self) -> None:
        # Cancelar after() y desbind si es necesario
        try:
            if self._clock_job and self.parent is not None:
                self.parent.after_cancel(self._clock_job)
                self._clock_job = None
        except Exception:
            logging.exception("Error cancelando reloj TPV")

        try:
            if self._resize_bound and self.parent is not None:
                self.parent.unbind("<Configure>")
                self._resize_bound = False
        except Exception:
            logging.exception("Error desbind resize TPV")

    # ---------------------- Responsive resizing ----------------------
    def _on_resize(self, event=None) -> None:
        """Recalcula tamaños y fuentes de los botones para comportamiento responsive."""
        try:
            total_w = max(1, self.parent.winfo_width())
            total_h = max(1, self.parent.winfo_height())

            # espacio reservado para la columna derecha fija
            right_w = RIGHT_WIDTH
            action_w = max(200, total_w - right_w)

            # grid: 4 columnas x 3 filas
            cols = 4
            rows = 3
            spacing = 12
            horizontal_padding = spacing * (cols + 1)
            vertical_padding = spacing * (rows + 1)

            # espacio disponible para botones
            available_w = max(100, action_w - horizontal_padding)
            available_h = max(100, total_h - INFO_BAR_HEIGHT - vertical_padding - 120)

            btn_w = int(available_w / cols)
            btn_h = int(available_h / rows)

            # elegir tamaño cuadrado para botones, limitado
            btn_size = max(80, min(btn_w, btn_h, 400))

            # Tamaño del search button: ancho completo del action panel menos márgenes
            search_h = int(max(40, min(80, total_h * 0.07)))
            search_w = max(300, action_w - 40)

            # Tamaños de fuente heurísticos
            btn_font_size = max(12, int(btn_size * 0.20))
            search_font_size = max(14, int(search_h * 0.45))

            # Aplicar al botón de búsqueda
            if self.search_button:
                try:
                    self.search_button.configure(width=search_w, height=search_h, font=("Roboto-SemiBold", search_font_size))
                except Exception:
                    logging.exception("Error ajustando search_button")

            # Aplicar a botones de la grid
            for b in self.grid_buttons:
                try:
                    b.configure(width=btn_size, height=btn_size, font=("Roboto-SemiBold", btn_font_size))
                except Exception:
                    logging.exception("Error ajustando grid button")

            # Ensure grid cells don't squash buttons: set minsize for columns/rows
            try:
                for c in range(cols):
                    self.grid_frame.grid_columnconfigure(c, minsize=btn_size + spacing)
                for r in range(rows):
                    self.grid_frame.grid_rowconfigure(r, minsize=btn_size + spacing)
            except Exception:
                pass
        except Exception:
            logging.exception("Error en _on_resize TPV")

    # ---------------------- Construcción de la vista ----------------------
    def show(self) -> None:
        # Limpiar contenedor
        for w in list(self.parent.winfo_children()):
            try:
                w.destroy()
            except Exception:
                pass

        # Left action panel
        self.action_panel = ctk.CTkFrame(self.parent, fg_color="#393E46")
        self.action_panel.pack(side="left", fill="both", expand=True)
        self.action_panel.pack_propagate(False)

        # Search button (ancho grande, comportamiento como botón)
        self.search_button = ButtonFactory.create_button(
            parent=self.action_panel,
            text="BUSCAR ARTÍCULO",
            command=None,
            font=("Roboto-SemiBold", 24),
            color="#00BFFF",
            text_color="#000000",
            hover_color="#00A4DF",
            corner_radius=18,
        )
        self.search_button.pack(pady=(18, 8), padx=20)

        # Grid frame para 4x3 botones
        self.grid_frame = ctk.CTkFrame(self.action_panel, fg_color="transparent")
        self.grid_frame.pack(fill="both", expand=True, padx=12, pady=12)

        # Crear botones desde configuración JSON (o fallback interno)
        self.grid_buttons = []
        cfg_list = load_button_config_from_json()
        # ensure we have at least 12 entries by repeating if necessary
        if len(cfg_list) < 12:
            times = (12 + len(cfg_list) - 1) // max(1, len(cfg_list)) if cfg_list else 12
            cfg_list = (cfg_list * times)[:12]

        for idx in range(12):
            cfg = cfg_list[idx]
            row = idx // 4
            col = idx % 4
            # derive font tuple
            font_size = cfg.get("font_size") or 36
            # prefer explicit font_family from config, fallback to Roboto-SemiBold
            fam = cfg.get("font_family") or "Roboto-SemiBold"
            font = (fam, int(font_size))
            hover = cfg.get("hover_color")
            # Create button without fixed pixel width/height so it can be
            # resized responsively in `_on_resize`.
            btn = ButtonFactory.create_button(
                parent=self.grid_frame,
                text=cfg.get("text", f"BTN{idx+1}"),
                command=(lambda name=cfg.get("command", cfg.get("text")): logging.info(f"Acción '{name}' pulsada")),
                font=font,
                color=cfg.get("color", "#CCCCCC"),
                text_color="#000000",
                hover_color=hover,
                corner_radius=28,
            )
            # place button centered in its cell; sizing handled in _on_resize
            btn.grid(row=row, column=col, padx=12, pady=12)
            self.grid_frame.grid_columnconfigure(col, weight=1)
            self.grid_frame.grid_rowconfigure(row, weight=1)
            # store base font size so _on_resize can scale relative to it
            try:
                btn._base_font_size = int(font_size)
            except Exception:
                btn._base_font_size = 36
            self.grid_buttons.append(btn)

        # Right container (fijo en la derecha)
        self.right_container = ctk.CTkFrame(self.parent, fg_color="#222831", width=RIGHT_WIDTH)
        self.right_container.pack(side="right", fill="y")
        self.right_container.pack_propagate(False)

        # Info bar (blanca) encima del cart_view
        info_bar = ctk.CTkFrame(self.right_container, height=INFO_BAR_HEIGHT, fg_color="#FFFFFF")
        info_bar.pack(side="top", fill="x")
        info_bar.pack_propagate(False)

        # Recuperar nombre del cajero si está disponible
        cashier_name = "Nombre Cajero"
        try:
            if self.db is not None:
                getter = getattr(self.db, "get_active_cashier", None)
                if callable(getter):
                    result = getter()
                    if isinstance(result, str) and result:
                        cashier_name = result
                    elif isinstance(result, dict) and result.get("name"):
                        cashier_name = result.get("name")
        except Exception:
            logging.exception("Error recuperando nombre cajero")

        # Info label (actualizable)
        self.info_label = ctk.CTkLabel(
            info_bar,
            text="",
            font=("Roboto-Regular", 18),
            text_color="#000000",
            anchor="center",
            justify="center",
        )
        self.info_label.pack(fill="both", expand=True)

        # Cart view (negra) - keep as attribute for external wiring
        self.cart_view = ctk.CTkFrame(self.right_container, fg_color="#000000")
        self.cart_view.pack(side="top", fill="both", expand=True)
        self.cart_view.pack_propagate(False)

        # Cart view placeholder for carrito and ticket display (ticket_display created after carrito)
        # Instantiate carrito service + UI
        try:
            from kool_tpv.modulos.tpv.carrito.carrito_service import CarritoService
            from kool_tpv.modulos.tpv.carrito.carrito_ui import CarritoUI
            self.carrito_service = CarritoService()
            # CarritoUI expects a tk-compatible parent; CTkFrame works as master
            self.carrito_ui = CarritoUI(self.cart_view, self.carrito_service)

            # ticket_display removed in rollback — no widget created here

            # Instanciar servicio de fidelización
            try:
                from kool_tpv.modulos.clientes.fidelizacion_service import FidelizacionService
                try:
                    self.fidelizacion_service = FidelizacionService(self.db)
                except Exception:
                    logging.exception('Error instanciando FidelizacionService')
                    self.fidelizacion_service = None
            except Exception:
                logging.exception('Error importando FidelizacionService')
                self.fidelizacion_service = None
            # ClienteAction: conectar botón CLIENTE con el panel de selección
            try:
                from kool_tpv.modulos.tpv.actions.cliente import ClienteAction
                try:
                    self._cliente_action = ClienteAction(self, self.db, self.carrito_service)
                except Exception:
                    self._cliente_action = None
            except Exception:
                self._cliente_action = None
            # Instanciar CajeroAction
            try:
                from kool_tpv.modulos.tpv.actions.cajero import CajeroAction
                try:
                    self._cajero_action = CajeroAction(self, self.db)
                except Exception:
                    logging.exception('Error instanciando CajeroAction')
                    self._cajero_action = None
            except Exception:
                logging.exception('Error importando CajeroAction')
                self._cajero_action = None
            # Instanciar DescuentoAction
            try:
                try:
                    self.descuento_action = DescuentoAction(self, self.carrito_service)
                except Exception:
                    logging.exception('Error instanciando DescuentoAction')
                    self.descuento_action = None
            except Exception:
                logging.exception('Error creando DescuentoAction')
                self.descuento_action = None
            # Instanciar DevolucionAction
            try:
                try:
                    from kool_tpv.modulos.tpv.actions.devolucion import DevolucionAction
                    self._devolucion_action = DevolucionAction(self, self.db, self.carrito_service)
                except Exception:
                    logging.exception('Error instanciando DevolucionAction')
                    self._devolucion_action = None
            except Exception:
                logging.exception('Error creando DevolucionAction')
                self._devolucion_action = None
            # Instanciar StockUI
            try:
                from kool_tpv.modulos.tpv.ui.stock_ui import StockUI
                try:
                    self._stock_ui = StockUI(self, self.db, on_selection_callback=self._on_producto_stock_selected)
                except Exception:
                    logging.exception('Error instanciando StockUI')
                    self._stock_ui = None
            except Exception:
                logging.exception('Error importando StockUI')
                self._stock_ui = None
            # attach cash controller UI (entry + CASH button)
            try:
                from kool_tpv.modulos.tpv.actions.cash import CashController
                # on_finalize: simple default that clears carrito and refreshes UI
                def _on_finalize(efectivo, forma_pago='Efectivo', importe_efectivo=None, importe_tarjeta=None):
                    """Finalize wrapper used by payment controllers.

                    If `efectivo` is None (used for non-cash payments), treat pagado as
                    the total amount so ticket fields remain numeric.
                    """
                    # Guard: do not allow finalizing when cart is empty
                    try:
                        try:
                            empty = False
                            if getattr(self.carrito_service, 'is_empty', None) and callable(self.carrito_service.is_empty):
                                empty = self.carrito_service.is_empty()
                            else:
                                empty = (self.carrito_service.get_item_count() == 0)
                        except Exception:
                            empty = True
                        if empty:
                            try:
                                show_warning(self.parent if hasattr(self, 'parent') else None, 'Carrito vacío', 'No se puede realizar una venta sin artículos.')
                            except Exception:
                                logging.exception('Error mostrando warning carrito vacío')
                            return
                    except Exception:
                        logging.exception('Error comprobando carrito vacío en on_finalize')

                    success = False
                    try:
                        # Persist the ticket, lines and update stock in DB
                        from kool_tpv.base_datos.ticket_service import save_ticket
                        resumen = self.carrito_service.get_resumen_financiero()
                        # Capturar items antes de cualquier limpieza para impresión
                        try:
                            items_to_print = list(self.carrito_service.get_items() or [])
                        except Exception:
                            items_to_print = []

                        # Capturar puntos canjeados ANTES de save_ticket (clear resetea a 0)
                        try:
                            puntos_canjeados_capturados = self.carrito_service.get_puntos_canjeados() or Decimal('0')
                        except Exception:
                            puntos_canjeados_capturados = Decimal('0')
                        cajero = getattr(self, 'cajero_nombre', None) or None

                        # Recuperar cliente desde CarritoService (si existe)
                        cliente_info = None
                        cliente_nombre = None
                        cliente_id = None
                        try:
                            cliente_info = self.carrito_service.get_cliente()
                            if cliente_info:
                                cliente_nombre = cliente_info.get('nombre') or cliente_info.get('name') or None
                                cliente_id = cliente_info.get('id') or cliente_info.get('cliente_id') or None
                        except Exception:
                            logging.exception('Error obteniendo cliente desde CarritoService')

                        # Prepare importe_efectivo / importe_tarjeta as Decimals (or 0)
                        try:
                            importe_efectivo_val = Decimal(str(importe_efectivo)) if importe_efectivo is not None else Decimal('0')
                        except Exception:
                            importe_efectivo_val = Decimal('0')
                        try:
                            importe_tarjeta_val = Decimal(str(importe_tarjeta)) if importe_tarjeta is not None else Decimal('0')
                        except Exception:
                            importe_tarjeta_val = Decimal('0')

                        # Determine pagado value: if efectivo is None (card), use total
                        try:
                            if efectivo is None:
                                total_val = resumen.get('total', 0.0)
                                pagado_val = Decimal(str(total_val))
                            else:
                                pagado_val = Decimal(str(efectivo))

                            # Obtener descuento si existe
                            try:
                                descuento_data = None
                                try:
                                    descuento_data = self.carrito_service.get_descuento()
                                except Exception:
                                    descuento_data = None
                            except Exception:
                                descuento_data = None

                            # Si existe un flujo de Devolución activo y tiene líneas, delegar la confirmación
                            save_res = None
                            try:
                                devol_svc = None
                                if getattr(self, '_devolucion_action', None) is not None:
                                    devol_svc = getattr(self._devolucion_action, 'devolucion_service', None)
                                if devol_svc is not None and callable(getattr(devol_svc, 'listar_lineas', None)) and len(devol_svc.listar_lineas()) > 0:
                                    # Delegar la persistencia a DevolucionService (convierte/valida internamente)
                                    save_res = devol_svc.confirmar_devolucion(usuario=cajero, cliente_id=cliente_id, efectivo=pagado_val, forma_pago=forma_pago, importe_efectivo=importe_efectivo_val, importe_tarjeta=importe_tarjeta_val, descuento_data=descuento_data)
                                else:
                                    save_res = save_ticket(
                                        self.db,
                                        self.carrito_service.get_items(),
                                        resumen,
                                        pagado_val,
                                        cajero=cajero,
                                        cliente=cliente_nombre,
                                        cliente_id=cliente_id,
                                        forma_pago=forma_pago,
                                        importe_efectivo=importe_efectivo_val,
                                        importe_tarjeta=importe_tarjeta_val,
                                        descuento_data=descuento_data,
                                        carrito_service=self.carrito_service,
                                        fidelizacion_service=getattr(self, 'fidelizacion_service', None),
                                    )
                            except Exception:
                                # fallback to direct save_ticket if devolucion confirm fails
                                logging.exception('Error delegando a DevolucionService; intentando save_ticket directo')
                                save_res = save_ticket(
                                    self.db,
                                    self.carrito_service.get_items(),
                                    resumen,
                                    pagado_val,
                                    cajero=cajero,
                                    cliente=cliente_nombre,
                                    cliente_id=cliente_id,
                                    forma_pago=forma_pago,
                                    importe_efectivo=importe_efectivo_val,
                                    importe_tarjeta=importe_tarjeta_val,
                                    descuento_data=descuento_data,
                                    carrito_service=self.carrito_service,
                                    fidelizacion_service=getattr(self, 'fidelizacion_service', None),
                                )
                            # soportar distintos retornos: (id,num) o (id,num,tesoro_dict)
                            ticket_id = None
                            num_ticket = None
                            try:
                                if isinstance(save_res, (list, tuple)):
                                    if len(save_res) >= 2:
                                        ticket_id, num_ticket = save_res[0], save_res[1]
                            except Exception:
                                # dejar ticket_id/num_ticket como None si unpack falla
                                ticket_id = None
                                num_ticket = None

                            logging.info(f'Ticket guardado id={ticket_id} num={num_ticket} forma_pago={forma_pago} Efectivo: {importe_efectivo_val} Tarjeta: {importe_tarjeta_val}')
                            success = True
                        except Exception as e:
                            logging.exception('Error guardando ticket en DB')
                            # try to surface DB path and error to the user
                            try:
                                db_path = getattr(self.db, 'db_path', 'unknown')
                            except Exception:
                                db_path = 'unknown'
                            msg = f"Error guardando ticket en la base de datos.\nDB: {db_path}\nDetalle: {e}"
                            try:
                                show_error(self.parent if hasattr(self, 'parent') else None, 'Error guardando ticket', msg)
                            except Exception:
                                logging.exception('No se pudo mostrar el diálogo de error')
                    except Exception:
                        logging.exception('Error en on_finalize wrapper')
                        try:
                            show_error(self.parent if hasattr(self, 'parent') else None, 'Error', 'Se produjo un error interno al finalizar la operación de cobro.')
                        except Exception:
                            pass

                    # Only clear carrito if persistence succeeded
                    if success:
                        try:
                            self.carrito_service.clear()
                            self.carrito_ui.update_display()
                            try:
                                show_success(self.parent if hasattr(self, 'parent') else None, 'Venta guardada', f'Ticket guardado correctamente (#{num_ticket})')
                            except Exception:
                                pass
                        except Exception:
                            logging.exception('Error limpiando carrito tras guardar ticket')

                        # Intentar imprimir ticket (simulación) sin bloquear flujo
                        try:
                            if getattr(self, 'impresora_service', None) is not None:
                                try:
                                    now = datetime.now()
                                    total_val = resumen.get('total', 0) if isinstance(resumen, dict) else 0
                                    # entregado: efectivo si se proporcionó, o total si pago con tarjeta
                                    if efectivo is None:
                                        entregado_val = total_val
                                        cambio_val = 0
                                    else:
                                        try:
                                            entregado_val = Decimal(str(efectivo))
                                        except Exception:
                                            entregado_val = Decimal(str(total_val))
                                        try:
                                            cambio_val = Decimal(str(efectivo)) - Decimal(str(total_val))
                                        except Exception:
                                            cambio_val = Decimal('0')

                                    # Calcular tesoro_data para impresión
                                    tesoro_data_for_ticket = {
                                        'gastado': Decimal('0'),
                                        'ganado': Decimal('0'),
                                        'acumulado': Decimal('0'),
                                        'total': Decimal('0')
                                    }
                                    try:
                                        puntos_gastados = puntos_canjeados_capturados

                                        # Calcular puntos ganados usando fidelizacion_service
                                        puntos_ganados = Decimal('0')
                                        puntos_restar = Decimal('0')
                                        try:
                                            if hasattr(self, 'fidelizacion_service') and self.fidelizacion_service is not None:
                                                # separar items venta/devolución para cálculo correcto de puntos
                                                items_venta = []
                                                items_devol = []
                                                for itp in (items_to_print or []):
                                                    item_repr = {
                                                        'id': itp.get('id'),
                                                        'pvp': str(itp.get('pvp', itp.get('precio', 0))),
                                                        'cantidad': itp.get('cantidad', 0)
                                                    }
                                                    try:
                                                        if str(itp.get('line_tipo', '')).lower() == 'devolucion':
                                                            items_devol.append(item_repr)
                                                        else:
                                                            items_venta.append(item_repr)
                                                    except Exception:
                                                        items_venta.append(item_repr)

                                                puntos_ganados = self.fidelizacion_service.calcular_puntos_ganados(
                                                    items_venta,
                                                    puntos_canjeados=puntos_gastados
                                                ) or Decimal('0')

                                                # calcular puntos que se restan por devoluciones (presentación)
                                                try:
                                                    puntos_restar = self.fidelizacion_service.calcular_puntos_ganados(items_devol, puntos_canjeados=Decimal('0')) or Decimal('0')
                                                except Exception:
                                                    puntos_restar = Decimal('0')
                                        except Exception:
                                            logging.exception('Error calculando puntos ganados para ticket')
                                            puntos_ganados = Decimal('0')
                                            puntos_restar = Decimal('0')

                                        # Obtener saldo ANTES de la venta (del cliente en el carrito)
                                        tesoro_antes = Decimal('0')
                                        try:
                                            if cliente_info:
                                                tesoro_antes = Decimal(str(cliente_info.get('tesoro_total', 0)))
                                        except Exception:
                                            tesoro_antes = Decimal('0')

                                        # Calcular valores para el ticket (mostrar neto ganado-restar devoluciones)
                                        try:
                                            neto_ganado = (puntos_ganados - puntos_restar)
                                        except Exception:
                                            neto_ganado = puntos_ganados

                                        tesoro_data_for_ticket = {
                                            'gastado': puntos_gastados,
                                            'ganado': neto_ganado,
                                            'acumulado': tesoro_antes - puntos_gastados,
                                            'total': tesoro_antes - puntos_gastados + neto_ganado,
                                        }
                                    except Exception:
                                        logging.exception('Error construyendo tesoro_data para ticket')

                                    ticket_data = {
                                        'fecha': now.strftime('%Y-%m-%d'),
                                        'hora': now.strftime('%H:%M:%S'),
                                        'cajero': cajero,
                                        'num_ticket': num_ticket,
                                        'subtotal': resumen.get('subtotal') if isinstance(resumen, dict) else 0,
                                        'iva_desglose': resumen.get('iva_desglose') if isinstance(resumen, dict) else {},
                                        'total': total_val,
                                        'forma_pago': forma_pago,
                                        'entregado': entregado_val,
                                        'cambio': cambio_val,
                                        'importe_efectivo': importe_efectivo_val,
                                        'importe_tarjeta': importe_tarjeta_val,
                                        # tesoro_data calculado arriba para asegurar valores reales
                                        'tesoro_data': tesoro_data_for_ticket,
                                        # datos de descuento (si existe)
                                        'descuento_euros': str(descuento_data['euros']) if descuento_data else '0',
                                        'descuento_tipo': descuento_data['tipo'] if descuento_data else None,
                                        'descuento_valor': descuento_data['valor'] if descuento_data else None,
                                     }
                                    # Marcar tipo devolucion para presentación si alguna línea es de devolución
                                    try:
                                        if any(str(it.get('line_tipo', '')).lower() == 'devolucion' for it in (items_to_print or [])):
                                            ticket_data['tipo'] = 'devolucion'
                                    except Exception:
                                        pass
                                    # Construir cliente_for_print con nivel resuelto
                                    cliente_for_print = None
                                    if cliente_info:
                                        cliente_for_print = cliente_info.copy()
                                        try:
                                            id_nivel = cliente_info.get('id_nivel')
                                            if id_nivel and getattr(self, 'db', None):
                                                try:
                                                    nivel_row = self.db.fetch_one(
                                                        "SELECT nombre_nivel, grafismo_nivel, level FROM niveles_fidelidad WHERE id = ?",
                                                        (id_nivel,)
                                                    )
                                                except Exception:
                                                    nivel_row = None
                                                if nivel_row:
                                                    cliente_for_print['nivel'] = nivel_row[0]
                                                    cliente_for_print['grafismo'] = nivel_row[1] or ''
                                                    cliente_for_print['level_num'] = nivel_row[2] or ''
                                                else:
                                                    cliente_for_print['nivel'] = ''
                                                    cliente_for_print['grafismo'] = ''
                                                    cliente_for_print['level_num'] = ''
                                            else:
                                                cliente_for_print['nivel'] = ''
                                                cliente_for_print['grafismo'] = ''
                                                cliente_for_print['level_num'] = ''
                                        except Exception:
                                            logging.exception('Error resolviendo nivel de fidelidad')
                                            cliente_for_print['nivel'] = ''
                                    try:
                                        self.impresora_service.imprimir_ticket(ticket_data, items_to_print, cliente_for_print)
                                    except Exception:
                                        logging.exception('Error en impresión de ticket (simulada)')
                                except Exception:
                                    logging.exception('Error preparando datos para impresión de ticket')
                        except Exception:
                            logging.exception('ImpresoraService no disponible o error al llamar imprimir_ticket')

                self._cash_controller = CashController(self.carrito_ui, self.carrito_service, on_finalize=_on_finalize)
            except Exception:
                pass
            # MultiPago controller (mixed payments)
            try:
                from kool_tpv.modulos.tpv.actions.multi_s import MultiPagoController
                try:
                    self._multi_controller = MultiPagoController(self.carrito_ui, self.carrito_service, on_finalize=_on_finalize)
                except Exception:
                    self._multi_controller = None
            except Exception:
                self._multi_controller = None
            # Direct payment controllers: Tarjeta (card) and Web
            try:
                from kool_tpv.modulos.tpv.actions.tarjeta import DirectPaymentController
                try:
                    self._tarjeta_controller = DirectPaymentController(self.carrito_ui, self.carrito_service, on_finalize=_on_finalize)
                except Exception:
                    self._tarjeta_controller = None

                try:
                    self._web_controller = DirectPaymentController(
                        self.carrito_ui,
                        self.carrito_service,
                        on_finalize=_on_finalize,
                        payment_method='Web',
                        banner_text='Finalizar venta WEB?',
                        banner_color='#88B04B',
                        help_bg_color='#6A8E3D',
                    )
                except Exception:
                    self._web_controller = None
            except Exception:
                # if import fails, ensure safe defaults
                self._tarjeta_controller = None
                self._web_controller = None
            # initial display
            try:
                self.carrito_ui.update_display()
            except Exception:
                pass
            # Instantiate impresora service (simulada) for printing tickets
            try:
                if ImpresoraService is not None:
                    try:
                        self.impresora_service = ImpresoraService(db=self.db)
                    except Exception:
                        self.impresora_service = None
                else:
                    self.impresora_service = None
            except Exception:
                self.impresora_service = None
            # Rebind big 'COBRAR' grid button (if present) to trigger cash action
            try:
                for btn in self.grid_buttons:
                    try:
                        txt = (btn.cget('text') or '').strip().upper()
                        # Bind CLIENTE button to ClienteAction if available
                        if txt == 'CLIENTE' and getattr(self, '_cliente_action', None) is not None:
                            btn.configure(command=lambda act=self._cliente_action: act.ejecutar())
                            logging.info('Grid button CLIENTE bound to ClienteAction')
                        if txt == 'CAJERO' and getattr(self, '_cajero_action', None) is not None:
                            btn.configure(command=lambda act=self._cajero_action: act.ejecutar())
                            logging.info('Grid button CAJERO bound to CajeroAction')
                        if txt in ('COBRAR', 'CASH') and getattr(self, '_cash_controller', None) is not None:
                            btn.configure(command=lambda ctl=self._cash_controller: ctl._on_action())
                            logging.info(f'Grid button {txt} bound to CashController')
                        if txt == 'STOCK' and getattr(self, '_stock_ui', None) is not None:
                            btn.configure(command=(lambda ui=self._stock_ui: ui.show()))
                            logging.info('Grid button STOCK bound to StockUI')
                        if txt == 'DESCUENTO' and getattr(self, 'descuento_action', None) is not None:
                            btn.configure(command=lambda act=self.descuento_action: act.ejecutar())
                            logging.info('Grid button DESCUENTO bound to DescuentoAction')
                        if txt in ('DEVOLUCIÓN', 'DEVOLUCION', 'REALIZAR DEVOLUCIÓN', 'REALIZAR DEVOLUCION') and getattr(self, '_devolucion_action', None) is not None:
                            btn.configure(command=lambda act=self._devolucion_action: act.ejecutar())
                            logging.info('Grid button DEVOLUCIÓN bound to DevolucionAction')
                        if any(k in txt for k in ('MULTI', 'MIXTO')) and getattr(self, '_multi_controller', None) is not None:
                            btn.configure(command=lambda ctl=self._multi_controller: ctl._on_action())
                            logging.info(f'Grid button {txt} bound to MultiPagoController')
                        if txt in ('TARJETA', 'CARD') and getattr(self, '_tarjeta_controller', None) is not None:
                            btn.configure(command=lambda ctl=self._tarjeta_controller: ctl._on_action())
                            logging.info(f'Grid button {txt} bound to DirectPaymentController (Tarjeta)')
                        if txt == 'WEB' and getattr(self, '_web_controller', None) is not None:
                            btn.configure(command=lambda ctl=self._web_controller: ctl._on_action())
                            logging.info(f'Grid button {txt} bound to DirectPaymentController (Web)')
                    except Exception:
                        pass
            except Exception:
                logging.exception('Error rebinding grid buttons to payment controllers')
        except Exception:
            logging.exception("Error instanciando CarritoService/CarritoUI")

        # Si no hay cajero autenticado, mostrar warning que abre overlay de Cajeros
        try:
            active = None
            if self.db is not None:
                getter = getattr(self.db, 'get_active_cashier', None)
                if callable(getter):
                    try:
                        active = getter()
                    except Exception:
                        active = None

            has_cajero = False
            if active:
                if isinstance(active, dict):
                    nombre = active.get('name') or active.get('nombre')
                    if nombre:
                        self.cajero_nombre = nombre
                        self.cajero_id = active.get('id') or active.get('cajero_id')
                        has_cajero = True
                elif isinstance(active, str):
                    self.cajero_nombre = active
                    has_cajero = True

            if not has_cajero:
                try:
                    parent_win = self.parent if hasattr(self, 'parent') else None
                    show_warning(
                        parent_win,
                        'Cajero no autenticado',
                        'No hay cajero autenticado. Pulsa Aceptar para abrir el panel de cajeros y autenticar uno.',
                        callback=lambda: self._open_cajero_overlay(),
                    )
                except Exception:
                    logging.exception('Error mostrando diálogo de cajero no autenticado')
        except Exception:
            logging.exception('Error comprobando sesión de cajero')

        # Iniciar reloj
        try:
            self._update_clock(cashier_name)
        except Exception:
            logging.exception("Error iniciando reloj")
        # Conectar controlador de acciones (buscar artículo, etc.)
        try:
            from kool_tpv.modulos.tpv.tpv_controller import TpvController
            # guardar referencia para teardown si es necesario
            self.controller = TpvController(self)
        except Exception:
            logging.exception("Error inicializando TpvController")

        # Bind resize para comportamiento responsive
        try:
            if not self._resize_bound:
                self.parent.bind("<Configure>", lambda e: self._on_resize(e))
                self._resize_bound = True
            # ajuste inicial
            self._on_resize()
        except Exception:
            logging.exception("Error bind resize TPV")


# Export limpio
__all__ = ["TpvView", "ButtonFactory", "BUTTON_CONFIG"]

