from customtkinter import CTkFrame, CTkScrollableFrame
import customtkinter as ctk
import logging
from decimal import Decimal, InvalidOperation

from kool_tpv.utils.factories.button_factory import ButtonFactory
from kool_tpv.utils.custom_dialog import show_warning

logger = logging.getLogger(__name__)


class DescuentoSubView(CTkFrame):
    """Subview para aplicar descuentos desde TPV.

    Muestra plantillas de descuentos (si existe DescuentoRepository) y
    dos chips grandes para elegir tipo: porcentaje ('%') o importe ('€').
    """

    def __init__(self, parent, db, carrito_service, view=None):
        super().__init__(parent)
        self.db = db
        self.carrito_service = carrito_service
        self.view = view

        # Registrar handler de Power para esta sub-vista (para que Power actúe como "volver")
        try:
            root = self.winfo_toplevel()
            if hasattr(root, "register_power_handler"):
                root.register_power_handler(self._handle_power, owner=self)
        except Exception:
            pass

        # intentar obtener descuentos desde repositorio (si está disponible)
        try:
            from kool_tpv.modulos.descuento.descuento_repository import DescuentoRepository
            try:
                repo = DescuentoRepository(self.db)
                self.descuentos = repo.listar_activos() or []
            except Exception:
                logger.exception('Error instanciando DescuentoRepository')
                self.descuentos = []
        except Exception:
            # Módulo descuento no disponible: fallback a lista vacía
            self.descuentos = []

        # Frame scrollable para chips
        self.chips_frame = CTkScrollableFrame(self)
        self.chips_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Insertar dos chips grandes de tipo porcentaje/importe
        try:
            pct_btn = ButtonFactory.create_button(
                parent=self.chips_frame,
                text="%",
                style_key="cajero_chip",
                command=lambda: self._on_tipo_seleccion('%')
            )
            pct_btn.grid(row=0, column=0, columnspan=3, sticky='ew', padx=8, pady=(6, 12))

            eur_btn = ButtonFactory.create_button(
                parent=self.chips_frame,
                text="€",
                style_key="cajero_chip",
                command=lambda: self._on_tipo_seleccion('€')
            )
            eur_btn.grid(row=1, column=0, columnspan=3, sticky='ew', padx=8, pady=(0, 18))
        except Exception:
            logger.exception('Error creando chips grandes de tipo descuento')

        # NOTA: por ahora no mostramos plantillas dinámicas; reservamos
        # la fila 2 para el input directo cuando se seleccione '%' .

        # Ajustar columnas para que se expandan equitativamente (3 columnas)
        try:
            for c in range(3):
                try:
                    self.chips_frame.grid_columnconfigure(c, weight=1)
                except Exception:
                    pass
        except Exception:
            pass

        # Placeholder for dynamic input area (hidden until needed)
        self._input_area = None

    def _on_tipo_seleccion(self, tipo):
        """Callback cuando se selecciona tipo '%' o '€'.

        Delegar al servicio de carrito para abrir diálogo de entrada
        y aplicar descuento correspondiente.
        """
        try:
            # If percentage type selected, show input entry + OK button
            if tipo == '%':
                self._show_percentage_input()
                return

            # Delegar a carrito_service para otros tipos (ej: '€')
            if getattr(self.carrito_service, 'apply_discount_tipo', None):
                try:
                    self.carrito_service.apply_discount_tipo(tipo)
                except Exception:
                    logger.exception('Error aplicando descuento por tipo desde carrito_service')
            else:
                # Si no existe, intentar usar DescuentoService.apply_discount_simple (fallback)
                try:
                    from kool_tpv.modulos.descuento.descuento_service import DescuentoService
                    svc = DescuentoService(self.db)
                    svc.apply_discount_by_type(tipo)
                except Exception:
                    logger.exception('No hay servicio de descuentos o carrito_service para manejar tipo')
        except Exception:
            logger.exception('Error en _on_tipo_seleccion')

    def _show_percentage_input(self):
        """Mostrar entrada grande y botón OK para introducir porcentaje."""
        try:
            # Si ya existe, enfocarla
            if self._input_area is not None:
                try:
                    self._input_entry.focus_set()
                except Exception:
                    pass
                return

            # Crear frame dentro de chips_frame en la fila 2
            self._input_area = ctk.CTkFrame(self.chips_frame)
            self._input_area.grid(row=2, column=0, columnspan=3, sticky='ew', padx=8, pady=(6, 12))

            # Entry grande
            self._input_var = ctk.StringVar(value='')
            self._input_entry = ctk.CTkEntry(self._input_area, textvariable=self._input_var, width=300, height=50, font=('Roboto', 20), justify='center')
            self._input_entry.pack(side='left', padx=(0, 12), expand=True, fill='x')

            # Botón Ok usando ButtonFactory
            try:
                ok_btn = ButtonFactory.create_button(parent=self._input_area, text='Ok', style_key='chip_default', command=self._on_submit_percentage)
            except Exception:
                # Fallback simple
                ok_btn = ctk.CTkButton(self._input_area, text='Ok', command=self._on_submit_percentage)
            ok_btn.pack(side='left')

            # Bind Enter on entry to submit
            try:
                self._input_entry.bind('<Return>', lambda e: self._on_submit_percentage())
                self._input_entry.bind('<KP_Enter>', lambda e: self._on_submit_percentage())
            except Exception:
                pass

            # Focus entry
            try:
                self._input_entry.focus_set()
            except Exception:
                pass
        except Exception:
            logger.exception('Error mostrando input porcentaje')

    def _on_submit_percentage(self):
        """Validar valor del entry y delegar la aplicación (lógica aplicada después)."""
        try:
            txt = (self._input_var.get() or '').strip()
            if not txt:
                show_warning(self, 'VALOR INVÁLIDO', 'Introduzca un número válido')
                try:
                    self._input_entry.focus_set(); self._input_entry.select_range(0,'end')
                except Exception:
                    pass
                return

            # Normalizar coma a punto
            txt_norm = txt.replace(',', '.')
            try:
                val = Decimal(txt_norm)
            except (InvalidOperation, ValueError):
                show_warning(self, 'VALOR INVÁLIDO', 'Introduzca un número válido')
                try:
                    self._input_entry.focus_set(); self._input_entry.select_range(0,'end')
                except Exception:
                    pass
                return

            # Reglas: >0 y <=100
            if val <= 0 or val > Decimal('100'):
                show_warning(self, 'VALOR INVÁLIDO', 'El porcentaje debe ser >0 y ≤100')
                try:
                    self._input_entry.focus_set(); self._input_entry.select_range(0,'end')
                except Exception:
                    pass
                return

            # Valor válido: delegar (lógica real se implementará después)
            try:
                if getattr(self.carrito_service, 'apply_discount_tipo', None):
                    try:
                        # Intentar pasar porcentaje al servicio si soporta dos args
                        try:
                            self.carrito_service.apply_discount_tipo('%', val)
                        except TypeError:
                            # Fallback pasar solo tipo
                            try:
                                self.carrito_service.apply_discount_tipo('%')
                            except Exception:
                                logger.exception('Error aplicando descuento (fallback)')
                        except Exception:
                            logger.exception('Error aplicando descuento')
                        else:
                            logger.info('DescuentoSubView: descuento aplicado, refrescando UI')
                            # Intentar refrescar el UI por varias rutas conocidas
                            tried = []
                            try:
                                if getattr(self.view, 'carrito_ui', None) is not None:
                                    tried.append('view.carrito_ui')
                                    try:
                                        self.view.carrito_ui.update_display()
                                    except Exception:
                                        logger.exception('Error refrescando view.carrito_ui')
                            except Exception:
                                pass

                            try:
                                if getattr(self.view, 'ticket_carrito', None) is not None:
                                    tried.append('view.ticket_carrito')
                                    try:
                                        self.view.ticket_carrito.update_display()
                                    except Exception:
                                        logger.exception('Error refrescando view.ticket_carrito')
                            except Exception:
                                pass

                            try:
                                top = None
                                try:
                                    top = self.winfo_toplevel()
                                except Exception:
                                    try:
                                        top = self.view and getattr(self.view, 'winfo_toplevel', lambda: None)()
                                    except Exception:
                                        top = None
                                if top is not None and getattr(top, 'carrito_ui', None) is not None:
                                    tried.append('toplevel.carrito_ui')
                                    try:
                                        top.carrito_ui.update_display()
                                    except Exception:
                                        logger.exception('Error refrescando toplevel.carrito_ui')
                            except Exception:
                                pass

                            logger.info('DescuentoSubView: refresh attempts: %s', tried)
                    except Exception:
                        logger.exception('Error llamando carrito_service.apply_discount_tipo con porcentaje')
                else:
                    logger.info('Porcentaje validado: %s (aún no aplicado)', str(val))
            except Exception:
                logger.exception('Error delegando aplicación de porcentaje')

            # Cerrar/ocultar input area
            try:
                self._input_area.destroy()
            except Exception:
                pass
            self._input_area = None

        except Exception:
            logger.exception('Error en _on_submit_percentage')

    def _on_apply_template(self, dto_id):
        try:
            # Llamar a carrito_service para aplicar plantilla por id
            if getattr(self.carrito_service, 'apply_discount_template', None):
                try:
                    self.carrito_service.apply_discount_template(dto_id)
                except Exception:
                    logger.exception('Error aplicando plantilla descuento desde carrito_service')
            else:
                # Fallback: usar DescuentoService
                try:
                    from kool_tpv.modulos.descuento.descuento_service import DescuentoService
                    svc = DescuentoService(self.db)
                    svc.apply_discount(ticket_id=getattr(self.carrito_service, 'current_ticket_id', None), descuentos=[{'id': dto_id}])
                except Exception:
                    logger.exception('No se pudo aplicar plantilla descuento (ni carrito_service ni DescuentoService)')
        except Exception:
            logger.exception('Error en _on_apply_template')

    def _handle_power(self):
        try:
            if self.view and hasattr(self.view, "pop_subview"):
                self.view.pop_subview()
                return True
        except Exception:
            pass
        return False

    def destroy(self):
        try:
            root = self.winfo_toplevel()
            if hasattr(root, "unregister_power_handler"):
                root.unregister_power_handler(owner=self)
        except Exception:
            pass
        super().destroy()
