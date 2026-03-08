"""
Controlador genérico para pagos directos (tarjeta, web, etc.).

Flujo:
 - Pulsar botón de pago -> `_activate()` muestra banner y bind de Enter
 - Pulsar Enter o pulsar el botón de pago de nuevo -> `_on_action()` finaliza la venta

El controlador usa `root.bind`/`root.unbind` para la tecla Enter y mantiene
la lógica de finalización delegada en `on_finalize`.
"""

from typing import Optional, Dict
import logging
import tkinter as tk


class DirectPaymentController:
    def __init__(
        self,
        carrito_ui,
        carrito_service,
        on_finalize=None,
        payment_method: str = 'Tarjeta',
        banner_text: str = 'Finalizar venta con tarjeta?',
        banner_color: str = '#1abc9c',
        help_bg_color: str = '#16a085',
    ):
        self.carrito_ui = carrito_ui
        self.carrito_service = carrito_service
        self.on_finalize = on_finalize
        self.payment_method = payment_method
        self.banner_text = banner_text
        self.banner_color = banner_color
        self.help_bg_color = help_bg_color
        self.state = 'inactive'  # inactive -> active
        self._root = None
        self._bind_id = None

        # register back-reference
        try:
            setattr(self.carrito_ui, '_direct_payment_controller', self)
        except Exception:
            pass
        # Register controller with CarritoUI for exclusivity management when available
        try:
            if hasattr(self.carrito_ui, 'register_controller') and callable(getattr(self.carrito_ui, 'register_controller')):
                try:
                    self.carrito_ui.register_controller(self)
                except Exception:
                    pass
        except Exception:
            pass

    def _activate(self):
        try:
            # ensure other payment controllers are deactivated (except this)
            try:
                if hasattr(self.carrito_ui, 'deactivate_all_controllers') and callable(getattr(self.carrito_ui, 'deactivate_all_controllers')):
                    try:
                        self.carrito_ui.deactivate_all_controllers(except_controller=self)
                    except Exception:
                        pass
            except Exception:
                pass
            # check cart non-empty
            try:
                empty = self.carrito_service.is_empty()
            except Exception:
                empty = (self.carrito_service.get_item_count() == 0)
            if empty:
                try:
                    self.carrito_ui.show_temporary_message('NO HAY ARTÍCULOS PARA VENDER', duration_ms=3000)
                except Exception:
                    logging.exception('Error mostrando mensaje carrito vacío')
                return

            # set visual: active banner and help
            try:
                self.carrito_ui.set_cash_active(True)

                lbl = getattr(self.carrito_ui, '_venta_label', None)
                if lbl is not None:
                    try:
                        lbl.config(text=self.banner_text, bg=self.banner_color)
                        lbl.grid()
                    except Exception:
                        pass

                help_lbl = getattr(self.carrito_ui, '_venta_help_label', None)
                if help_lbl is None:
                    try:
                        help_lbl = tk.Label(self.carrito_ui._cash_container, text=f"Pulsa Enter o '{self.payment_method}' para confirmar", fg='#FFFFFF', bg=self.help_bg_color)
                        setattr(self.carrito_ui, '_venta_help_label', help_lbl)
                    except Exception:
                        help_lbl = None

                try:
                    if help_lbl is not None:
                        help_lbl.grid(row=1, column=0, columnspan=3, sticky='we')
                except Exception:
                    pass

                # bind Enter on the root to confirm while active; store bind id for cleanup
                try:
                    root = self.carrito_ui.parent.winfo_toplevel()
                    self._root = root

                    def _enter_handler(event=None):
                        try:
                            self._on_action()
                        except Exception:
                            logging.exception('Error manejando Enter en DirectPaymentController')
                        return 'break'

                    try:
                        self._bind_id = root.bind('<Return>', _enter_handler)
                    except Exception:
                        root.bind('<Return>', _enter_handler)
                        self._bind_id = None
                except Exception:
                    pass
            except Exception:
                logging.exception('Error activando visual pago directo')

            self.state = 'active'
        except Exception:
            logging.exception('Error en _activate DirectPaymentController')

    def deactivate(self):
        try:
            self.state = 'inactive'
            try:
                lbl = getattr(self.carrito_ui, '_venta_label', None)
                if lbl is not None:
                    try:
                        lbl.grid_remove()
                    except Exception:
                        pass
            except Exception:
                pass
            try:
                help_lbl = getattr(self.carrito_ui, '_venta_help_label', None)
                if help_lbl is not None:
                    try:
                        help_lbl.grid_remove()
                    except Exception:
                        pass
            except Exception:
                pass
            try:
                self.carrito_ui.set_cash_active(False)
            except Exception:
                pass
            try:
                if getattr(self, '_root', None):
                    try:
                        if getattr(self, '_bind_id', None):
                            try:
                                self._root.unbind('<Return>', self._bind_id)
                            except Exception:
                                try:
                                    self._root.unbind('<Return>')
                                except Exception:
                                    pass
                        else:
                            try:
                                self._root.unbind('<Return>')
                            except Exception:
                                pass
                    except Exception:
                        pass
                    finally:
                        self._root = None
                        self._bind_id = None
            except Exception:
                pass
        except Exception:
            logging.exception('Error en deactivate DirectPaymentController')

    # (deactivate is public) no wrapper needed

    def _on_action(self):
        try:
            if self.state == 'inactive':
                self._activate()
                return

            if self.state == 'active':
                # finalize sale with configured payment method
                try:
                    try:
                        self.carrito_service.set_forma_pago(self.payment_method)
                    except Exception:
                        logging.exception('Error setting forma_pago %s', self.payment_method)

                    if callable(self.on_finalize):
                        try:
                            # pass None for efectivo to indicate non-cash; let on_finalize handle forma_pago
                            self.on_finalize(None, forma_pago=self.payment_method)
                        except TypeError:
                            try:
                                self.on_finalize(None)
                            except Exception:
                                logging.exception('Error calling on_finalize from DirectPaymentController')
                except Exception:
                    logging.exception('Error finalizando venta con %s', self.payment_method)
                finally:
                    try:
                        self.deactivate()
                    except Exception:
                        pass
                    self.state = 'inactive'
                return
        except Exception:
            logging.exception('Error handling direct payment action')
