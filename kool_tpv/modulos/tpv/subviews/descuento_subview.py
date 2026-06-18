from customtkinter import CTkFrame, CTkScrollableFrame
import customtkinter as ctk
import logging
from decimal import Decimal, InvalidOperation

from kool_tpv.utils.factories.button_factory import ButtonFactory
from kool_tpv.utils.widgets.notificaciones import show_warning

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

        # NOTE: Power handler registration removed from __init__
        # TpvView already handles power button for subviews via pop_subview()
        # No need for individual subviews to register their own handlers

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
        
        Muestra un área de entrada para introducir el valor del descuento.
        """
        try:
            self._show_input_area(tipo)
        except Exception:
            logger.exception('Error en _on_tipo_seleccion')

    def _show_input_area(self, tipo):
        """Mostrar entrada gigante y botón OK para introducir el valor (porcentaje o importe)."""
        try:
            # Si ya existe, destruirla para recrearla con el tipo correcto (placeholder/validación)
            if self._input_area is not None:
                try:
                    self._input_area.destroy()
                except Exception:
                    pass
            
            # Crear frame dentro de chips_frame en la fila 2
            self._input_area = ctk.CTkFrame(self.chips_frame)
            self._input_area.grid(row=2, column=0, columnspan=3, sticky='ew', padx=8, pady=(6, 12))

            # Entry GIGANTE
            self._input_var = ctk.StringVar(value='')
            placeholder = "Introduzca %" if tipo == '%' else "Introduzca €"
            
            # Font mucho más grande (tamaño 50) y altura mayor
            self._input_entry = ctk.CTkEntry(
                self._input_area, 
                textvariable=self._input_var, 
                width=350, 
                height=80, 
                font=('Roboto', 50, 'bold'), 
                justify='center',
                placeholder_text=placeholder
            )
            self._input_entry.pack(side='left', padx=(0, 12), expand=True, fill='x')

            # Botón Ok usando ButtonFactory
            try:
                ok_btn = ButtonFactory.create_button(
                    parent=self._input_area, 
                    text='Aplicar', 
                    style_key='chip_default', 
                    command=lambda: self._on_submit_amount(tipo),
                    height=80 # Acompañar la altura del entry
                )
            except Exception:
                # Fallback simple
                ok_btn = ctk.CTkButton(self._input_area, text='Aplicar', command=lambda: self._on_submit_amount(tipo), height=80)
            ok_btn.pack(side='left')

            # Bind Enter on entry to submit
            try:
                self._input_entry.bind('<Return>', lambda e: self._on_submit_amount(tipo))
                self._input_entry.bind('<KP_Enter>', lambda e: self._on_submit_amount(tipo))
            except Exception:
                pass

            # Focus entry
            try:
                self._input_entry.focus_set()
            except Exception:
                pass
        except Exception:
            logger.exception(f'Error mostrando input para tipo {tipo}')

    def _on_submit_amount(self, tipo):
        """Validar valor del entry y aplicar el descuento según tipo."""
        try:
            txt = (self._input_var.get() or '').strip()
            if not txt:
                show_warning(self, 'Introduzca un número válido')
                self._input_entry.focus_set()
                return

            # Normalizar coma a punto
            txt_norm = txt.replace(',', '.')
            try:
                val = Decimal(txt_norm)
            except (InvalidOperation, ValueError):
                show_warning(self, 'Introduzca un número válido')
                self._input_entry.focus_set()
                self._input_entry.select_range(0, 'end')
                return

            # Reglas básicas: >0
            if val <= 0:
                show_warning(self, 'El valor debe ser mayor que 0')
                self._input_entry.focus_set()
                return

            # Regla específica para %: <=100
            if tipo == '%' and val > Decimal('100'):
                show_warning(self, 'El porcentaje no puede ser mayor que 100')
                self._input_entry.focus_set()
                return

            # Intentar aplicar el descuento
            try:
                if getattr(self.carrito_service, 'apply_discount_tipo', None):
                    self.carrito_service.apply_discount_tipo(tipo, val)
                    logger.info(f'Descuento {val}{tipo} aplicado correctamente')
                    
                    # Refrescar la vista del ticket
                    try:
                        if self.view and hasattr(self.view, 'ticket_carrito'):
                            self.view.ticket_carrito.update_carrito()
                    except Exception:
                        pass
                else:
                    logger.error('carrito_service no tiene el método apply_discount_tipo')
                    show_warning(self, 'Error interno: no se puede aplicar el descuento')

            except ValueError as ve:
                # El servicio lanza ValueError si el descuento supera el total, etc.
                show_warning(self, str(ve))
                self._input_entry.focus_set()
                return
            except Exception:
                logger.exception('Error aplicando descuento')
                show_warning(self, 'Error al aplicar el descuento')
                return

            # Si todo ha ido bien, cerrar/ocultar input area y tal vez cerrar la subview
            try:
                self._input_area.destroy()
                self._input_area = None
            except Exception:
                pass
            
            # Volver al grid del TPV (cerrar esta subview)
            try:
                if self.view and hasattr(self.view, 'pop_subview'):
                    self.view.pop_subview()
            except Exception:
                pass

        except Exception:
            logger.exception('Error en _on_submit_amount')

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

    # NOTE: _handle_power removed - TpvView handles power button via pop_subview()
    # Individual subviews don't need their own power handlers

    def destroy(self):
        # NOTE: No need to unregister - we don't register in __init__ anymore
        # TpvView manages power handling for all subviews
        super().destroy()
