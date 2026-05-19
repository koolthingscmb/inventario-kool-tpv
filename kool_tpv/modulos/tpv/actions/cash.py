"""
Cash action controller: attaches cash input and button to `CarritoUI` totals area.

Behavior:
 - Entry for 'efectivo entregado' and a 'CASH' button are placed above totals.
 - Pressing Enter or clicking the button toggles:
     * first press: calculate change and show it
     * second press: finalize sale (calls on_finalize callback)

This module implements UI wiring only; DB transaction and ticket persistence
are delegated to the `on_finalize` callback passed when attaching.
"""
from decimal import Decimal, InvalidOperation
import logging
import tkinter as tk


class CashController:
    """Controller para manejar cobro en efectivo sin botón pequeño.

    Flujo de estados:
      inactive -> waiting -> calculated -> confirmed

    - El botón grande de la zona de acción (COBRAR/CASH) debe invocar `controller._on_action()`.
    - Si el estado es `inactive`, la primera pulsación activa el modo efectivo (zona verde) y pone foco en el Entry.
    - Si el estado es `waiting`, pulsar Enter o invocar `_on_action()` calcula el cambio y pide confirmación textual.
    - Si el estado es `calculated`, pulsar Enter o invocar `_on_action()` finaliza la venta y llama a `on_finalize`.
    """

    def __init__(self, carrito_ui, carrito_service, on_finalize=None):
        self.carrito_ui = carrito_ui
        self.carrito_service = carrito_service
        self.on_finalize = on_finalize
        self.state = 'inactive'
        self.efectivo = Decimal('0.00')
        self._build_ui()
        # register back-reference so UI can call deactivate when carrito empties
        try:
            setattr(self.carrito_ui, '_cash_controller', self)
        except Exception:
            pass
        # Register with CarritoUI for exclusivity management when available
        try:
            if hasattr(self.carrito_ui, 'register_controller') and callable(getattr(self.carrito_ui, 'register_controller')):
                try:
                    self.carrito_ui.register_controller(self)
                except Exception:
                    pass
        except Exception:
            pass

    def deactivate(self):
        """Forcefully deactivate cash mode and reset UI elements."""
        try:
            self.state = 'inactive'
            try:
                # reset visuals
                if hasattr(self, '_container'):
                    self._container.config(bg=getattr(self.carrito_ui, '_cash_container_orig_bg', ''))
            except Exception:
                pass
            try:
                # hide venta label
                try:
                    self.carrito_ui.show_venta_efectivo(False)
                except Exception:
                    pass
            except Exception:
                pass
            try:
                # clear and unfocus entry
                if hasattr(self, '_entry'):
                    try:
                        self._entry.delete(0, 'end')
                    except Exception:
                        pass
                try:
                    if hasattr(self.carrito_ui, '_tree') and self.carrito_ui._tree is not None:
                        self.carrito_ui._tree.focus_set()
                except Exception:
                    pass
            except Exception:
                pass
            try:
                if hasattr(self, '_lbl_change'):
                    self._lbl_change.config(text='')
            except Exception:
                pass
        except Exception:
            logging.exception('Error al desactivar CashController')

    def _build_ui(self):
        try:
            container = getattr(self.carrito_ui, '_cash_container', None)
            if container is None:
                return

            # keep reference to container
            self._container = container

            # Entry for efectivo entregado (row 1 to leave row 0 for 'VENTA EN EFECTIVO')
            self._entry = tk.Entry(container)
            self._entry.grid(row=1, column=0, sticky='we', padx=(2, 6))

            # Change / hint label (empty initially) at row 2
            self._lbl_change = tk.Label(container, text='')
            self._lbl_change.grid(row=2, column=0, sticky='w')

            container.columnconfigure(0, weight=1)

            # Bind Enter key in entry to same action
            self._entry.bind('<Return>', lambda e: self._on_action())
            # Recalculate change live when user edits the amount after calculation
            self._entry.bind('<KeyRelease>', lambda e: self._on_entry_change())
        except Exception:
            logging.exception('Error building CashController UI')

    def _on_entry_change(self):
        """Recalculate change when the entry content changes (useful if user corrects amount)."""
        try:
            # only recalc if we're in waiting or calculated state
            if getattr(self, 'state', 'inactive') not in ('waiting', 'calculated'):
                return
            txt = self._entry.get().strip()
            try:
                efectivo = Decimal(str(txt))
            except (InvalidOperation, ValueError):
                try:
                    self._lbl_change.config(text='Importe no válido')
                except Exception:
                    pass
                return

            total = Decimal(str(self.carrito_service.get_total()))
            cambio = efectivo - total
            try:
                if cambio < 0:
                    self._lbl_change.config(text=f'Importe insuficiente — faltan {(-cambio):.2f} €')
                    if self.state == 'calculated':
                        self.state = 'waiting'  # retrocede: no se puede confirmar con importe bajo
                    # NO actualizar self.efectivo cuando el importe es insuficiente
                    return
                elif self.state == 'calculated':
                    self._lbl_change.config(text=f'Cambio: {cambio:.2f} € — Confirmar venta en efectivo? (Enter/COBRAR)')
                else:
                    self._lbl_change.config(text=f'Cambio: {cambio:.2f} €')
            except Exception:
                pass
            self.efectivo = efectivo
            # remain in same state
        except Exception:
            logging.exception('Error recalculando cambio en entry')

    def _on_action(self):
        try:
            # inactive -> activate mode (visual cue + focus)
            if self.state == 'inactive':
                # ensure other payment controllers are deactivated (except this)
                try:
                    if hasattr(self.carrito_ui, 'deactivate_all_controllers') and callable(getattr(self.carrito_ui, 'deactivate_all_controllers')):
                        try:
                            self.carrito_ui.deactivate_all_controllers(except_controller=self)
                        except Exception:
                            pass
                except Exception:
                    pass
                # validate cart not empty
                try:
                    if getattr(self.carrito_service, 'is_empty', None) and callable(self.carrito_service.is_empty):
                        empty = self.carrito_service.is_empty()
                    else:
                        empty = self.carrito_service.get_item_count() == 0
                except Exception:
                    empty = True

                if empty:
                    try:
                        self.carrito_ui.show_temporary_message('NO HAY ARTÍCULOS PARA VENDER', duration_ms=3000)
                    except Exception:
                        logging.exception('Error mostrando mensaje carrito vacío')
                    return

                try:
                    # visually indicate active cash area
                    try:
                        # prefer a pleasant green
                        self._container.config(bg='#2ecc71')
                        # set venta label explicitly (text + bg) and ensure it's shown
                        try:
                            lbl = getattr(self.carrito_ui, '_venta_label', None)
                            if lbl is not None:
                                try:
                                    lbl.config(text='INTRODUCE EL EFECTIVO ENTREGADO', bg='#2ecc71')
                                    lbl.grid()
                                except Exception:
                                    pass
                        except Exception:
                            pass
                        # inform carrito UI to show venta label (keeps compatibility)
                        try:
                            self.carrito_ui.show_venta_efectivo(True)
                        except Exception:
                            pass
                    except Exception:
                        pass
                    # ensure entry and labels are visible (they may have been grid_removed by other controllers)
                    try:
                        if hasattr(self, '_entry') and self._entry is not None:
                            try:
                                self._entry.grid()
                            except Exception:
                                pass
                        else:
                            # if entry missing, rebuild UI
                            try:
                                self._build_ui()
                            except Exception:
                                pass
                    except Exception:
                        pass
                    # ensure change label visible
                    try:
                        if hasattr(self, '_lbl_change') and self._lbl_change is not None:
                            try:
                                self._lbl_change.grid()
                            except Exception:
                                pass
                    except Exception:
                        pass
                    # focus entry for keyboard input
                    try:
                        self._entry.focus_set()
                    except Exception:
                        pass
                    # clear previous labels
                    try:
                        self._lbl_change.config(text='')
                    except Exception:
                        pass
                except Exception:
                    logging.exception('Error activando modo efectivo')
                self.state = 'waiting'
                # let caller know UI changed
                try:
                    self.carrito_ui.set_cash_active(True)
                except Exception:
                    pass
                return

            # waiting -> calculate change and prompt confirmation textually
            if self.state == 'waiting':
                txt = self._entry.get().strip()
                try:
                    efectivo = Decimal(str(txt))
                except (InvalidOperation, ValueError):
                    try:
                        self._lbl_change.config(text='Importe no válido')
                    except Exception:
                        pass
                    return

                total = Decimal(str(self.carrito_service.get_total()))
                cambio = efectivo - total
                if cambio < 0:
                    # importe insuficiente: mostrar error y NO avanzar de estado
                    try:
                        self._lbl_change.config(text=f'Importe insuficiente — faltan {(-cambio):.2f} €')
                    except Exception:
                        pass
                    return
                # show change and textual confirmation prompt
                try:
                    self._lbl_change.config(text=f'Cambio: {cambio:.2f} € — Confirmar venta en efectivo? (Enter/COBRAR)')
                except Exception:
                    pass
                self.efectivo = efectivo
                self.state = 'calculated'
                return

            # calculated -> finalize sale
            if self.state == 'calculated':
                try:
                    # validate sufficient amount before finalizing
                    # Fail closed: if we cannot read the total, block the sale
                    total = Decimal(str(self.carrito_service.get_total()))
                    if total <= Decimal('0'):
                        # Carrito vacío o total indeterminado: no finalizar
                        try:
                            self._lbl_change.config(text='Error al leer el total del carrito')
                        except Exception:
                            pass
                        return
                    try:
                        efectivo_val = Decimal(str(self.efectivo))
                    except Exception:
                        efectivo_val = Decimal('0')

                    cambio_val = efectivo_val - total
                    if cambio_val < 0:
                        # insufficient amount: show error and do not finalize
                        try:
                            if hasattr(self, '_lbl_change') and self._lbl_change is not None:
                                try:
                                    self._lbl_change.config(text='Importe insuficiente')
                                except Exception:
                                    pass
                            else:
                                try:
                                    from tkinter import messagebox
                                    messagebox.showerror('Importe insuficiente', 'El importe entregado es inferior al total.')
                                except Exception:
                                    logging.exception('Error mostrando messagebox Importe insuficiente')
                        except Exception:
                            logging.exception('Error mostrando aviso de importe insuficiente')
                        # DO NOT deactivate or finalize; keep user in payment mode
                        return

                    # call carrito_service to set payment if supported
                    try:
                        self.carrito_service.set_forma_pago('Efectivo', float(self.efectivo))
                    except Exception:
                        logging.exception('Error setting forma_pago in CarritoService')

                    # Delegate full finalization (DB insertion, stock updates) to callback
                    if callable(self.on_finalize):
                        try:
                            self.on_finalize(self.efectivo)
                        except Exception:
                            logging.exception('Error en callback on_finalize')
                    else:
                        try:
                            self.carrito_service.clear()
                            self.carrito_ui.update_display()
                        except Exception:
                            logging.exception('Error clearing carrito after finalize')

                    # reset visuals and state only after successful finalization
                    try:
                        self._container.config(bg=getattr(self.carrito_ui, '_cash_container_orig_bg', None) or '')
                    except Exception:
                        pass
                    try:
                        # hide venta label
                        try:
                            self.carrito_ui.show_venta_efectivo(False)
                        except Exception:
                            pass
                        try:
                            self._lbl_change.config(text='Venta finalizada')
                        except Exception:
                            pass
                    except Exception:
                        pass
                    # clear and unfocus entry
                    try:
                        self._entry.delete(0, 'end')
                        # move focus to treeview if available
                        try:
                            if hasattr(self.carrito_ui, '_tree') and self.carrito_ui._tree is not None:
                                self.carrito_ui._tree.focus_set()
                        except Exception:
                            pass
                    except Exception:
                        pass
                    self.state = 'inactive'
                except Exception:
                    logging.exception('Error finalizando cash action')
                return

        except Exception:
            logging.exception('Error handling cash action')
