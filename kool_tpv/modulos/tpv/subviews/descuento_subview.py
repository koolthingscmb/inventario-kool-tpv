from customtkinter import CTkFrame, CTkScrollableFrame
import logging

from kool_tpv.utils.factories.button_factory import ButtonFactory

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

        # Crear chips a partir de plantillas en self.descuentos
        for i, dto in enumerate(self.descuentos):
            try:
                # dto puede ser dict o objeto; acceder de forma defensiva
                nombre = dto.get('nombre') if isinstance(dto, dict) else getattr(dto, 'nombre', str(dto))
                dto_id = dto.get('id') if isinstance(dto, dict) else getattr(dto, 'id', None)
                btn = ButtonFactory.create_button(
                    parent=self.chips_frame,
                    text=nombre or f"Descuento {i+1}",
                    style_key="chip_default",
                    command=(lambda _id=dto_id: self._on_apply_template(_id))
                )
                # start placing templates from row 2 (after two large chips)
                btn.grid(row=(i // 3) + 2, column=i % 3, padx=8, pady=8, sticky="nsew")
            except Exception:
                logger.exception('Error creando chip para plantilla descuento')

        # Ajustar columnas para que se expandan equitativamente (3 columnas)
        try:
            for c in range(3):
                try:
                    self.chips_frame.grid_columnconfigure(c, weight=1)
                except Exception:
                    pass
        except Exception:
            pass

    def _on_tipo_seleccion(self, tipo):
        """Callback cuando se selecciona tipo '%' o '€'.

        Delegar al servicio de carrito para abrir diálogo de entrada
        y aplicar descuento correspondiente.
        """
        try:
            # Delegar a carrito_service (si implementa apply_discount_tipo)
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
