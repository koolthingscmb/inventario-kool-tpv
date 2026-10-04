"""Pantalla SUBIDA de un producto NUEVO a Shopify."""
import logging
import threading

from kool_tpv.utils.widgets.notificaciones import show_error
from kool_tpv.modulos.shopify.services.shopify_nuevo_builder import ErrorPreparacion
from .subida_base_view import SubidaBaseView

logger = logging.getLogger(__name__)


class SubidaNuevoView(SubidaBaseView):
    """Sube productos nuevos: una ficha por variante TPV marcada para web (o una agrupada)."""

    _modo = "NUEVO"
    TEXTO_BOTON = "SUBIR A SHOPIFY"

    def _finalizar_build(self):
        # En NUEVO la variante TPV no se elige: se suben todas las marcadas en CONFIG
        self._variante_combo.entry.configure(state="disabled")
        self._btn_upload.configure(text=self.TEXTO_BOTON)
        self._limpiar_formulario()
        self._seleccionar_tipo_por_defecto()

    def _despachar_subida(self, base):
        self._subir_nuevo(base)

    def _tras_subida_correcta(self):
        # Tras una subida nueva 100% correcta, dejar el formulario limpio para el siguiente producto
        self._limpiar_formulario()

    def _subir_nuevo(self, base):
        try:
            trabajos = self.nuevo_builder.construir_trabajos(
                base=base,
                titulo=self._entries["titulo"].get().strip(),
                beneficio=self._entries["beneficio"].get().strip(),
                tipo_nombre=self._tipo_combo.get().strip(),
                tipo_id=self._tipo_combo.get_id(),
                variantes_disponibles=self._variantes_disponibles,
                cuerpos={nombre: box.get("1.0", "end-1c") for nombre, box in self._body_boxes.items()},
                imagenes=self._selector_imagenes.obtener_locales(),
            )
        except ErrorPreparacion as e:
            show_error(self.frame, str(e))
            return

        self._status(f"Subiendo {len(trabajos)} productos...")
        self._btn_upload.configure(state="disabled")

        def work():
            mensajes = []
            for datos in trabajos:
                genero = datos.get('genero', 'Producto')
                try:
                    r = self.product_service.product_set(datos)
                    mensajes.append(f"{genero}: {'OK' if r['success'] else r['message']}")
                except Exception as e:
                    logger.exception(f"Error inesperado subiendo {genero}")
                    mensajes.append(f"{genero}: Error inesperado ({type(e).__name__}), revisa la terminal")
            self.frame.after(0, lambda: self._fin_upload(mensajes))
        threading.Thread(target=work, daemon=True).start()
