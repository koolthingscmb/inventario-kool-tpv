"""
UI del carrito de compras
Interfaz visual para mostrar y gestionar el carrito

Implementación: `ttk.Treeview` con columnas Producto | Cant | Precio | Total
soporta selección simple y tecla Delete para reducir cantidad.
"""
import logging
from pathlib import Path
from decimal import Decimal
import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
from typing import Optional
from kool_tpv.modulos.tpv.actions.canjear_tesoro import CanjearTesoroAction
from kool_tpv.modulos.clientes.fidelizacion_service import FidelizacionService


class CarritoUI:
    """Interfaz visual del carrito de compras"""

    def __init__(self, parent: tk.Widget, carrito_service=None):
        self.parent = parent
        self.carrito_service = carrito_service
        # Instanciar servicio de fidelización con acceso a la DB de la ventana toplevel
        try:
            top = self.parent.winfo_toplevel()
            db_handle = getattr(top, 'db', None)
            self.fidelizacion_service = FidelizacionService(db_handle)
        except Exception:
            logging.exception('No se pudo instanciar FidelizacionService en CarritoUI')
            self.fidelizacion_service = None
        self._tree: Optional[ttk.Treeview] = None
        self._vsb: Optional[ttk.Scrollbar] = None
        # Registered payment controllers (DirectPaymentController, CashController, etc.)
        self._payment_controllers = []
        self._setup_ui()

    def _setup_ui(self):
        """Configurar interfaz visual: Treeview + scrollbar"""
        try:
            # Create a container frame using native tk to host ttk widgets
            container = tk.Frame(self.parent)
            container_bg = container.cget('bg')
            # decide text color based on container background brightness
            text_color = '#000000'
            try:
                bg = container_bg
                if isinstance(bg, str) and bg.startswith('#'):
                    hexc = bg.lstrip('#')
                    if len(hexc) == 3:
                        hexc = ''.join([c * 2 for c in hexc])
                    if len(hexc) == 6:
                        r = int(hexc[0:2], 16) / 255.0
                        g = int(hexc[2:4], 16) / 255.0
                        b = int(hexc[4:6], 16) / 255.0
                        luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
                        text_color = '#000000' if luminance > 0.5 else '#FFFFFF'
            except Exception:
                text_color = '#000000'
            container.pack(fill='both', expand=True, padx=6, pady=6)

            # Cliente bar: muestra info de fidelización (icono, nombre, puntos, canjear)
            self._cliente_bar_frame = tk.Frame(container, bg=container_bg)
            self._cliente_bar_frame.grid(row=0, column=0, columnspan=2, sticky='we', padx=6, pady=(6, 6))

            # Load icons safely; fallbacks ensure UI doesn't break if assets missing.
            # Calcular ruta base de assets (kool_tpv/assets/)
            try:
                base_assets = Path(__file__).resolve().parents[3] / "assets"
            except Exception:
                base_assets = Path('assets')
            self._user_icon_image = None
            self._tesoro_icon_image = None
            self._varita_icon_image = None
            try:
                from PIL import Image
                try:
                    user_img = Image.open(base_assets / 'user_icon.png').resize((20, 20), Image.LANCZOS)
                    self._user_icon_image = ctk.CTkImage(user_img, size=(20, 20))
                except Exception:
                    self._user_icon_image = None
                try:
                    tesoro_img = Image.open(base_assets / 'tesoro_icon.png').resize((20, 20), Image.LANCZOS)
                    self._tesoro_icon_image = ctk.CTkImage(tesoro_img, size=(20, 20))
                except Exception:
                    self._tesoro_icon_image = None
                try:
                    varita_img = Image.open(base_assets / 'varita_icon.png').resize((20, 20), Image.LANCZOS)
                    self._varita_icon_image = ctk.CTkImage(varita_img, size=(20, 20))
                except Exception:
                    self._varita_icon_image = None
            except Exception:
                # PIL not available; try tkinter PhotoImage
                try:
                    try:
                        self._user_icon_image = tk.PhotoImage(file=str(base_assets / 'user_icon.png'))
                    except Exception:
                        self._user_icon_image = None
                    try:
                        self._tesoro_icon_image = tk.PhotoImage(file=str(base_assets / 'tesoro_icon.png'))
                    except Exception:
                        self._tesoro_icon_image = None
                    try:
                        self._varita_icon_image = tk.PhotoImage(file=str(base_assets / 'varita_icon.png'))
                    except Exception:
                        self._varita_icon_image = None
                except Exception:
                    self._user_icon_image = None
                    self._tesoro_icon_image = None
                    self._varita_icon_image = None

            # Left: user icon + name
            try:
                if isinstance(self._user_icon_image, ctk.CTkImage):
                    self._cliente_user_icon = ctk.CTkLabel(self._cliente_bar_frame, image=self._user_icon_image, text='', fg_color='transparent')
                elif self._user_icon_image is not None:
                    self._cliente_user_icon = tk.Label(self._cliente_bar_frame, image=self._user_icon_image, bg=container_bg)
                else:
                    self._cliente_user_icon = tk.Label(self._cliente_bar_frame, text='', bg=container_bg)
                self._cliente_user_icon.grid(row=0, column=0, sticky='w')
            except Exception:
                self._cliente_user_icon = None

            self._cliente_name_lbl = tk.Label(self._cliente_bar_frame, text='SELECCIONAR CLIENTE...', fg="#0484B3", bg=container_bg, font=('Roboto', 15, 'bold'), anchor='w')
            self._cliente_name_lbl.grid(row=0, column=1, sticky='w', padx=(6, 12))

            # flexible spacer
            try:
                spacer = tk.Frame(self._cliente_bar_frame, bg=container_bg)
                spacer.grid(row=0, column=2, sticky='we')
                self._cliente_bar_frame.columnconfigure(2, weight=1)
            except Exception:
                pass

            # Tesoro icon + points
            try:
                if isinstance(self._tesoro_icon_image, ctk.CTkImage):
                    self._tesoro_icon_lbl = ctk.CTkLabel(self._cliente_bar_frame, image=self._tesoro_icon_image, text='', fg_color='transparent')
                elif self._tesoro_icon_image is not None:
                    self._tesoro_icon_lbl = tk.Label(self._cliente_bar_frame, image=self._tesoro_icon_image, bg=container_bg)
                else:
                    self._tesoro_icon_lbl = tk.Label(self._cliente_bar_frame, text='', bg=container_bg)
                self._tesoro_icon_lbl.grid(row=0, column=3, sticky='e', padx=(6, 2))
            except Exception:
                self._tesoro_icon_lbl = None

            self._tesoro_points_lbl = tk.Label(self._cliente_bar_frame, text='0', fg='#0484B3', bg=container_bg, font=('Roboto', 15, 'bold'))
            self._tesoro_points_lbl.grid(row=0, column=4, sticky='e', padx=(2, 6))

            # Canjear button with varita icon only
            try:
                # Pass `self` (CarritoUI) as the view so the action can call update_display()
                cmd = lambda: CanjearTesoroAction(self, self.carrito_service, self.fidelizacion_service).ejecutar()
                if isinstance(self._varita_icon_image, ctk.CTkImage):
                    self._canjear_btn = ctk.CTkButton(self._cliente_bar_frame, image=self._varita_icon_image, text='', fg_color='transparent', hover=False, command=cmd)
                elif self._varita_icon_image is not None:
                    self._canjear_btn = tk.Button(self._cliente_bar_frame, image=self._varita_icon_image, text='', bg=container_bg, relief='flat', command=cmd)
                else:
                    self._canjear_btn = tk.Button(self._cliente_bar_frame, text='Canjear', bg=container_bg, relief='flat', command=cmd)
                self._canjear_btn.grid(row=0, column=5, sticky='e', padx=(4, 0))
            except Exception:
                try:
                    cmd = lambda: CanjearTesoroAction(self.parent.winfo_toplevel(), self.carrito_service, self.fidelizacion_service).ejecutar()
                    self._canjear_btn = tk.Button(self._cliente_bar_frame, text='Canjear', command=cmd)
                    self._canjear_btn.grid(row=0, column=5, sticky='e', padx=(4, 0))
                except Exception:
                    self._canjear_btn = None

            cols = ('producto', 'cantidad', 'precio', 'total')
            self._tree = ttk.Treeview(container, columns=cols, show='headings', selectmode='browse')
            self._tree.heading('producto', text='Producto')
            self._tree.heading('cantidad', text='Cant')
            self._tree.heading('precio', text='Precio')
            self._tree.heading('total', text='Total')

            # column sizing
            self._tree.column('producto', anchor='w', width=180)
            self._tree.column('cantidad', anchor='center', width=60)
            self._tree.column('precio', anchor='e', width=80)
            self._tree.column('total', anchor='e', width=100)

            # visual tag for canje row
            try:
                self._tree.tag_configure("canje_style", foreground="red")
            except Exception:
                pass

            # visual tag for descuento row (red, bold)
            try:
                self._tree.tag_configure("descuento", foreground="#ff6b6b", font=("Arial", 11, "bold"))
            except Exception:
                pass

            # vertical scrollbar
            self._vsb = ttk.Scrollbar(container, orient='vertical', command=self._tree.yview)
            self._tree.configure(yscrollcommand=self._vsb.set)

            # Use grid so totals stay pinned to the bottom. Reserve row 0 for cliente label.
            container.grid_rowconfigure(1, weight=1)
            container.grid_columnconfigure(0, weight=1)

            # Treeview occupies row 1 (below cliente label)
            self._tree.grid(row=1, column=0, sticky='nsew')
            self._vsb.grid(row=1, column=1, sticky='ns')

            # Bind Enter key on tree to add another unit of selected article
            self._tree.bind('<Return>', lambda e: self._on_tree_enter())

            # Frame for totals (under the treeview)
            self._totals_frame = tk.Frame(container)
            self._totals_frame.grid(row=3, column=0, columnspan=2, sticky='we', pady=(6, 0))

            # Container for cash controls (entry + button) placed above totals
            self._cash_container = tk.Frame(self._totals_frame, bg=container_bg)
            self._cash_container.grid(row=0, column=0, columnspan=3, sticky='we')
            # remember original bg to restore when deactivating cash mode
            self._cash_container_orig_bg = container_bg
            # 'VENTA EN EFECTIVO' label (hidden by default) above the entry
            self._venta_label = tk.Label(self._cash_container, text='VENTA EN EFECTIVO', fg='#FFFFFF', bg='#2ecc71')
            # place it but keep hidden initially
            self._venta_label.grid(row=0, column=0, columnspan=3, sticky='we')
            self._venta_label.grid_remove()

            # Separator label (will be filled in update_display)
            self._sep_label = tk.Label(self._totals_frame, text='', anchor='w', fg=text_color, bg=container_bg)
            self._sep_label.grid(row=1, column=0, columnspan=3, sticky='we')

            # Headers for subtotal / iva / total
            self._hdr_subtotal = tk.Label(self._totals_frame, text='Subtotal', anchor='w', fg=text_color, bg=container_bg)
            self._hdr_iva = tk.Label(self._totals_frame, text='IVA', anchor='center', fg=text_color, bg=container_bg)
            self._hdr_total = tk.Label(self._totals_frame, text='TOTAL', anchor='e', fg=text_color, bg=container_bg)
            self._hdr_subtotal.grid(row=2, column=0, sticky='w')
            self._hdr_iva.grid(row=2, column=1)
            self._hdr_total.grid(row=2, column=2, sticky='e')

            # Amount labels (values will be set in update_display)
            self._val_subtotal = tk.Label(self._totals_frame, text='', anchor='w', fg=text_color, bg=container_bg)
            self._val_iva = tk.Label(self._totals_frame, text='', anchor='center', fg=text_color, bg=container_bg)
            self._val_total = tk.Label(self._totals_frame, text='', anchor='e', fg=text_color, bg=container_bg)
            self._val_subtotal.grid(row=3, column=0, sticky='w')
            self._val_iva.grid(row=3, column=1)
            self._val_total.grid(row=3, column=2, sticky='e')

            # Configure grid columns to distribute space
            self._totals_frame.columnconfigure(0, weight=3)
            self._totals_frame.columnconfigure(1, weight=2)
            self._totals_frame.columnconfigure(2, weight=2)

            # Bind Delete key to remove one unit
            self._tree.bind('<Delete>', lambda e: self._on_delete_key())
            # Bind BackSpace as alternative to Delete (supr)
            self._tree.bind('<BackSpace>', lambda e: self._on_delete_key())
            # Ensure tree has focus when clicked
            self._tree.bind('<Button-1>', lambda e: self._tree.focus_set())
        except Exception:
            logging.exception('Error inicializando CarritoUI')

    def set_cash_active(self, active: bool):
        """Visually toggle the cash area active state (green background when active)."""
        try:
            if not hasattr(self, '_cash_container'):
                return
            if active:
                try:
                    self._cash_container.config(bg='#2ecc71')
                except Exception:
                    pass
            else:
                try:
                    self._cash_container.config(bg=getattr(self, '_cash_container_orig_bg', ''))
                except Exception:
                    pass
        except Exception:
            logging.exception('Error toggling cash active visual')

    def show_venta_efectivo(self, show: bool):
        """Mostrar u ocultar el label 'VENTA EN EFECTIVO' encima del entry."""
        try:
            if not hasattr(self, '_venta_label'):
                return
            if show:
                try:
                    self._venta_label.grid()
                except Exception:
                    pass
            else:
                try:
                    self._venta_label.grid_remove()
                except Exception:
                    pass
        except Exception:
            logging.exception('Error toggling venta efectivo label')

    def show_temporary_message(self, message: str, duration_ms: int = 3000):
        """Mostrar un mensaje temporal en la zona de totales que desaparece tras `duration_ms`."""
        try:
            # create or reuse a transient label in totals_frame
            if not hasattr(self, '_temp_msg_lbl'):
                self._temp_msg_lbl = tk.Label(self._totals_frame, text=message, fg='white', bg='red')
                self._temp_msg_lbl.grid(row=4, column=0, columnspan=3, sticky='we', pady=(6, 0))
            else:
                try:
                    self._temp_msg_lbl.config(text=message)
                    self._temp_msg_lbl.grid()
                except Exception:
                    pass

            # cancel previous hide job if present
            try:
                if hasattr(self, '_temp_msg_job') and self._temp_msg_job:
                    self._totals_frame.after_cancel(self._temp_msg_job)
            except Exception:
                pass

            def _hide():
                try:
                    self._temp_msg_lbl.grid_remove()
                except Exception:
                    pass

            self._temp_msg_job = self._totals_frame.after(duration_ms, _hide)
        except Exception:
            logging.exception('Error mostrando mensaje temporal en CarritoUI')

    def register_controller(self, controller) -> None:
        """Register a payment controller for exclusivity management.

        The controller is added to `self._payment_controllers` if not already present.
        """
        try:
            if controller is None:
                return
            if not hasattr(self, '_payment_controllers'):
                self._payment_controllers = []
            if controller not in self._payment_controllers:
                self._payment_controllers.append(controller)
        except Exception:
            logging.exception('Error registrando controlador de pago en CarritoUI')

    def deactivate_all_controllers(self, except_controller=None) -> None:
        """Deactivate all registered payment controllers except an optional one.

        For each controller, attempts to call `deactivate()` then `_deactivate()` if available.
        Exceptions from one controller do not interrupt others.
        """
        try:
            controllers = getattr(self, '_payment_controllers', []) or []
            for ctl in list(controllers):
                try:
                    if ctl is except_controller:
                        continue
                    # prefer public API
                    if hasattr(ctl, 'deactivate') and callable(getattr(ctl, 'deactivate')):
                        try:
                            ctl.deactivate()
                        except Exception:
                            logging.exception('Error al llamar deactivate() en controlador')
                        continue
                    if hasattr(ctl, '_deactivate') and callable(getattr(ctl, '_deactivate')):
                        try:
                            ctl._deactivate()
                        except Exception:
                            logging.exception('Error al llamar _deactivate() en controlador')
                except Exception:
                    logging.exception('Error procesando controlador en deactivate_all_controllers')
        except Exception:
            logging.exception('Error en deactivate_all_controllers CarritoUI')

    def update_display(self):
        """Actualizar visualización del carrito leyendo `carrito_service.get_items()`"""
        if self._tree is None or self.carrito_service is None:
            return

        # 1) Limpiar Treeview
        for iid in list(self._tree.get_children()):
            try:
                self._tree.delete(iid)
            except Exception:
                pass

        # 2) Insertar productos
        items = self.carrito_service.get_items() or []
        for idx, item in enumerate(items):
            try:
                from decimal import Decimal

                prod = item.get('nombre', '')
                cant = int(item.get('cantidad', 0))
                precio = Decimal(str(item.get('pvp', 0.0)))
                total_linea = Decimal(str(item.get('total_linea', precio * cant)))

                # Usar FormatterService.format_precio SIEMPRE
                precio_s = self.carrito_service.formatter.format_precio(precio)
                total_s = self.carrito_service.formatter.format_precio(total_linea)

                iid = str(item.get('id', idx))
                self._tree.insert('', 'end', iid=iid, values=(prod, str(cant), precio_s, total_s))
            except Exception as e:
                logging.exception(f"ERROR insertando línea {idx}: {e}")

        # 3) Insertar linea de descuento si existe (usar resumen dinámico para obtener euros)
        try:
            try:
                resumen_tmp = self.carrito_service.get_resumen_financiero() or {}
            except Exception:
                resumen_tmp = {}

            descuento_euros = resumen_tmp.get('descuento_euros', None)
            descuento_tipo = resumen_tmp.get('descuento_tipo', None)
            descuento_valor = resumen_tmp.get('descuento_valor', None)

            if descuento_euros and descuento_euros > 0:
                try:
                    if descuento_tipo == 'directo':
                        texto_descuento = '>> Descuento Directo:'
                    elif descuento_tipo == 'porcentaje':
                        texto_descuento = f'>> Descuento -{descuento_valor}%:'
                    else:
                        texto_descuento = '>> Descuento:'

                    try:
                        f = self.carrito_service.formatter
                        total_text = f.format_precio(-descuento_euros)
                    except Exception:
                        total_text = f"-{descuento_euros} €"

                    self._tree.insert('', 'end', values=(texto_descuento, '', '', total_text), tags=('descuento',))
                except Exception:
                    logging.exception('Error insertando línea de descuento en Treeview')
        except Exception:
            pass

        resumen = {}
        try:
            puntos = self.carrito_service.get_puntos_canjeados()
        except Exception:
            from decimal import Decimal
            puntos = getattr(self.carrito_service, 'get_puntos_canjeados', lambda: Decimal('0'))()

        try:
            from decimal import Decimal
            if puntos and puntos > Decimal('0'):
                try:
                    f = self.carrito_service.formatter
                    puntos_formatted = f.format_precio(-puntos)
                except Exception:
                    puntos_formatted = f"-{puntos} €"
                try:
                    # Insertar canje al final y asegurarnos que sea visible y seleccionado
                    self._tree.insert('', 'end', iid='__canje_tesoro__', values=('>> CANJE PUNTOS', '', puntos_formatted, puntos_formatted))
                    try:
                        self._tree.see('__canje_tesoro__')
                    except Exception:
                        pass
                    try:
                        self._tree.selection_set('__canje_tesoro__')
                        self._tree.focus('__canje_tesoro__')
                    except Exception:
                        pass
                except Exception as e:
                    logging.exception(f"ERROR insertando canje en Treeview: {e}")
        except Exception:
            pass

        # 4) Actualizar labels de totales
        try:
            resumen = self.carrito_service.get_resumen_financiero() or {}
            f = self.carrito_service.formatter
            try:
                # Format total and IVA first (presentation truncation), then compute displayed
                # subtotal as (total_display - iva_display) so displayed pieces sum exactly.
                total_val = resumen.get('total', 0.0)
                iva_val = resumen.get('total_iva', 0.0)

                total_s = f.format_precio(total_val)
                iva_s = f.format_precio(iva_val)

                # Convert formatted strings back to Decimal for exact subtraction
                try:
                    from decimal import Decimal
                    total_dec = Decimal(str(total_s).replace(' €', '').strip())
                    iva_dec = Decimal(str(iva_s).replace(' €', '').strip())
                    subtotal_calc = total_dec - iva_dec
                except Exception:
                    # Fallback to using raw resumen values
                    try:
                        subtotal_calc = Decimal(str(resumen.get('subtotal', 0.0)))
                    except Exception:
                        subtotal_calc = resumen.get('subtotal', 0.0)

                try:
                    subtotal_s = f.format_precio(subtotal_calc)
                except Exception:
                    subtotal_s = f.format_precio(resumen.get('subtotal', 0.0))

                self._val_subtotal.config(text=subtotal_s)
                self._val_iva.config(text=iva_s)
                self._val_total.config(text=total_s)
            except Exception:
                # fallback simple
                subtotal = resumen.get('subtotal', 0.0)
                total_iva = resumen.get('total_iva', 0.0)
                total = resumen.get('total', 0.0)
                try:
                    self._val_subtotal.config(text=f"{subtotal:.2f} €")
                    self._val_iva.config(text=f"{total_iva:.2f} €")
                    self._val_total.config(text=f"{total:.2f} €")
                except Exception:
                    pass
        except Exception:
            resumen = {}

        # Actualizar información de cliente sin bloquear la UI
        try:
            cliente = None
            try:
                cliente = self.carrito_service.get_cliente()
            except Exception:
                cliente = None

            if cliente:
                try:
                    nombre_cliente = cliente.get('nombre') or cliente.get('name') or ''
                    if hasattr(self, '_cliente_name_lbl'):
                        self._cliente_name_lbl.config(text=nombre_cliente)
                except Exception:
                    pass
                try:
                    tesoro = cliente.get('tesoro_total', 0)
                    if hasattr(self, '_tesoro_points_lbl'):
                        tesoro_formatted = self.carrito_service.formatter.format_tesoro(tesoro)
                        self._tesoro_points_lbl.config(text=tesoro_formatted)
                except Exception:
                    pass
                try:
                    if hasattr(self, '_canjear_btn') and self._canjear_btn is not None:
                        enabled = False
                        try:
                            enabled = (float(cliente.get('tesoro_total', 0)) > 0)
                        except Exception:
                            enabled = bool(cliente.get('tesoro_total'))
                        try:
                            if enabled:
                                self._canjear_btn.config(state='normal')
                            else:
                                self._canjear_btn.config(state='disabled')
                        except Exception:
                            pass
                except Exception:
                    pass
            else:
                try:
                    if hasattr(self, '_cliente_name_lbl'):
                        self._cliente_name_lbl.config(text='SELECCIONAR CLIENTE...')
                except Exception:
                    pass
                try:
                    if hasattr(self, '_tesoro_points_lbl'):
                        self._tesoro_points_lbl.config(text='')
                except Exception:
                    pass
                try:
                    if hasattr(self, '_canjear_btn') and self._canjear_btn is not None:
                        try:
                            self._canjear_btn.config(state='disabled')
                        except Exception:
                            try:
                                self._canjear_btn['state'] = 'disabled'
                            except Exception:
                                pass
                except Exception:
                    pass
        except Exception:
            pass

        # Asegurar visibilidad del treeview
        try:
            if hasattr(self, '_tree') and self._tree is not None:
                self._tree.grid()
        except Exception:
            pass

        # No test rows: production logic only

        # Resumen final
        try:
            logging.info(f"RESUMEN UI: Items={len(items)} | Canje={puntos} | Total={resumen.get('total')}")
        except Exception:
            try:
                logging.exception(f"RESUMEN UI failed to log: Items={len(items)} | Canje={puntos}")
            except Exception:
                logging.exception('RESUMEN UI: error generando resumen final')
            # Duplicate canje/totals block removed (handled earlier in function)

    def clear_display(self):
        try:
            if self._tree is None:
                return
            for iid in list(self._tree.get_children()):
                self._tree.delete(iid)
        except Exception:
            logging.exception('Error limpiando display CarritoUI')

    def _on_delete_key(self):
        """Handler para tecla Delete: reduce 1 unidad o elimina línea completa"""
        try:
            if self._tree is None or self.carrito_service is None:
                return
            sel = self._tree.selection()
            if not sel:
                return
            iid = sel[0]

            # Si es la línea de canje, cancelar canje
            if iid == '__canje_tesoro__':
                try:
                    self.carrito_service.set_puntos_canjeados(Decimal('0'))
                    try:
                        self.update_display()
                    except Exception:
                        pass
                    logging.info('Canje cancelado por usuario (tecla Supr/Del)')
                except Exception:
                    logging.exception('Error cancelando canje')
                return

            # Si la fila seleccionada es la de descuento, eliminar descuento
            try:
                item_tags = self._tree.item(iid).get('tags', ()) or ()
                if 'descuento' in item_tags:
                    try:
                        # Llamar al servicio para eliminar descuento y refresh
                        if hasattr(self.carrito_service, 'eliminar_descuento'):
                            self.carrito_service.eliminar_descuento()
                        elif hasattr(self.carrito_service, 'set_descuento'):
                            # fallback if different API
                            try:
                                self.carrito_service.set_descuento(None)
                            except Exception:
                                pass
                        try:
                            self.update_display()
                        except Exception:
                            pass
                        logging.info('Descuento eliminado por usuario (tecla Supr/Del)')
                    except Exception:
                        logging.exception('Error eliminando descuento por tecla Delete')
                    return
            except Exception:
                pass

            # capture children order before mutation to choose next focus after update
            try:
                children_before = list(self._tree.get_children())
                pos_before = children_before.index(iid) if iid in children_before else None
            except Exception:
                children_before = []
                pos_before = None

            # find index in carrito_service internal list by id
            items = self.carrito_service.get_items() or []
            index = None
            current_cant = 0
            for idx, item in enumerate(items):
                if str(item.get('id')) == str(iid):
                    index = idx
                    current_cant = int(item.get('cantidad', 0))
                    break
            if index is None:
                return

            # decrease or remove
            if current_cant > 1:
                self.carrito_service.update_cantidad(index, current_cant - 1)
            else:
                self.carrito_service.remove_item(index)

            # refresh view
            try:
                self.update_display()
            except Exception:
                pass

            # after updating, restore selection/focus properly
            try:
                children_after = list(self._tree.get_children())
                if str(iid) in children_after:
                    # same line still exists (quantity decreased)
                    try:
                        self._tree.selection_set(iid)
                        self._tree.focus(iid)
                        self._tree.see(iid)
                    except Exception:
                        pass
                else:
                    # choose neighbor: prefer next at same index, else previous
                    if children_after:
                        try:
                            if pos_before is None:
                                target = children_after[0]
                            else:
                                idx_choice = pos_before
                                if idx_choice >= len(children_after):
                                    idx_choice = len(children_after) - 1
                                target = children_after[idx_choice]
                            self._tree.selection_set(target)
                            self._tree.focus(target)
                            self._tree.see(target)
                        except Exception:
                            pass
                    else:
                        # no children left; ensure no selection
                        try:
                            self._tree.selection_remove(self._tree.selection())
                        except Exception:
                            pass
            except Exception:
                logging.exception('Error restaurando selección tras borrar')

            # Also if cart became empty, deactivate cash controller
            try:
                if self.carrito_service.is_empty():
                    try:
                        if hasattr(self, '_cash_controller') and self._cash_controller is not None:
                            self._cash_controller.deactivate()
                    except Exception:
                        pass
            except Exception:
                pass
        except Exception:
            logging.exception('Error procesando Delete en CarritoUI')

    def _on_tree_enter(self):
        """Handler for Enter on tree: if cash mode active, forward action; else add one unit of selected item."""
        try:
            # if cash mode active, forward to controller
            try:
                cc = getattr(self, '_cash_controller', None)
            except Exception:
                cc = None
            if cc is not None and getattr(cc, 'state', 'inactive') != 'inactive':
                try:
                    cc._on_action()
                except Exception:
                    logging.exception('Error delegando Enter al CashController')
                return

            # otherwise, add another unit of selected article
            try:
                sel = self._tree.selection()
                if not sel:
                    return
                iid = sel[0]
                # Find matching item in carrito_service
                items = self.carrito_service.get_items() or []
                for item in items:
                    if str(item.get('id')) == str(iid):
                        # add another unit by calling add_item with minimal data
                        try:
                            self.carrito_service.add_item({'id': item.get('id'), 'nombre': item.get('nombre'), 'pvp': str(item.get('pvp')), 'tipo_iva': item.get('tipo_iva', 21)})
                            self.update_display()
                        except Exception:
                            logging.exception('Error añadiendo unidad por Enter')
                        break
            except Exception:
                logging.exception('Error procesando Enter en Treeview')
        except Exception:
            logging.exception('Error en _on_tree_enter')

