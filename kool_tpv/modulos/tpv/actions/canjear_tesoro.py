"""Acción: canjear tesoro (puntos) del cliente en la venta actual.

Proporciona una clase `CanjearTesoroAction` que orquesta la interacción con el
`CarritoService` y muestra un diálogo de entrada para que el cajero pueda
indicar cuánto canjear.
"""
from decimal import Decimal, InvalidOperation
import logging

from kool_tpv.utils.dialogs import show_input_dialog
from kool_tpv.utils.widgets.notificaciones import ToastWidget
from kool_tpv.utils.formatter_service import FormatterService


class CanjearTesoroAction:
    def __init__(self, view, carrito_service, fidelizacion_service):
        """Crear la acción.

        Args:
            view: referencia a la vista principal (se usará para refrescar UI)
            carrito_service: instancia de `CarritoService`
            fidelizacion_service: servicio de fidelización (no usado directo aquí,
                pero inyectado para futuras validaciones o reglas)
        """
        self.view = view
        self.carrito_service = carrito_service
        self.fidelizacion_service = fidelizacion_service
        # Formatter para mostrar tesoro formateado (truncado)
        try:
            self.formatter = FormatterService()
        except Exception:
            self.formatter = None

    def ejecutar(self) -> None:
        """Ejecutar el flujo de canje de tesoro.

        - Verifica que exista cliente en el carrito.
        - Solicita mediante diálogo la cantidad a canjear.
        - Valida que la cantidad sea Decimal válida y no supere saldo ni total.
        - Aplica el canje en `CarritoService` y refresca la UI.
        """
        # Obtener ventana padre correcta para diálogos
        try:
            parent_window = self.view.parent.winfo_toplevel()
        except Exception:
            try:
                parent_window = self.view.parent
            except Exception:
                parent_window = self.view

        # No permitir canjear si hay items de devolución en el carrito
        try:
            _cart_items = self.carrito_service.get_items() or []
            _has_devol = any(str(it.get('line_tipo', 'venta')).lower() == 'devolucion' for it in _cart_items)
        except Exception:
            _has_devol = False
        if _has_devol:
            ToastWidget.show(parent_window, 'NO SE PUEDE CANJEAR TESORO DURANTE UNA DEVOLUCIÓN', tipo='warning')
            return

        # Validar que haya productos en el carrito
        try:
            if self.carrito_service.is_empty():
                ToastWidget.show(parent_window, 'NO HAY PRODUCTOS EN EL CARRITO. NO SE PUEDE CANJEAR TESORO.', tipo='warning')
                return
        except Exception:
            logging.exception('Error validando carrito vacío')

        cliente = self.carrito_service.get_cliente()
        if not cliente:
            ToastWidget.show(parent_window, 'SELECCIONA UN CLIENTE PRIMERO PARA CANJEAR TESORO', tipo='warning')
            return

        # No permitir canjear si hay un descuento activo
        try:
            if hasattr(self.carrito_service, 'has_descuento') and self.carrito_service.has_descuento():
                ToastWidget.show(parent_window, 'NO SE PUEDE CANJEAR TESORO CON UN DESCUENTO ACTIVO. ELIMINA EL DESCUENTO PRIMERO.', tipo='error')
                return
        except Exception:
            logging.exception('Error verificando descuento activo antes de canjear tesoro')

        # Obtener saldo del cliente: esperamos que la selección añada 'tesoro_total'
        saldo_raw = cliente.get('tesoro_total', cliente.get('tesoro', 0))
        try:
            saldo = Decimal(str(saldo_raw))
        except Exception:
            saldo = Decimal('0.00')

        # Formatear tesoro con truncado a 2 decimales
        try:
            tesoro_formateado = self.formatter.format_tesoro(saldo) if self.formatter is not None else str(saldo)
        except Exception:
            tesoro_formateado = str(saldo)

        # Total base (subtotal + IVA) para validar el canje: no considerar descuentos previos
        total_actual = Decimal('0.00')
        try:
            resumen = self.carrito_service.get_resumen_financiero()
            subtotal = Decimal(str(resumen.get('subtotal', '0') or '0'))
            total_iva = Decimal(str(resumen.get('total_iva', '0') or '0'))
            total_actual = subtotal + total_iva
        except Exception:
            logging.exception('Error obteniendo subtotal/IVA para validar canje')
            total_actual = Decimal('0.00')

        # Mostrar diálogo de entrada personalizado
        prompt = f"Saldo disponible: {tesoro_formateado} €\n¿Cuánto deseas canjear?"
        try:
            valor_str = show_input_dialog(parent_window, "Canjear Tesoro", prompt, tipo='success')
        except Exception:
            logging.exception('Error mostrando diálogo de entrada personalizado')
            valor_str = None

        # Si se canceló o no se introdujo nada, salir silenciosamente
        if valor_str is None or str(valor_str).strip() == "":
            return

        # Normalizar separador decimal y validar como Decimal
        valor_normalizado = str(valor_str).strip().replace(',', '.')
        try:
            valor_decimal = Decimal(valor_normalizado)
        except (InvalidOperation, ValueError):
            ToastWidget.show(parent_window, 'INTRODUZCA UN NÚMERO VÁLIDO PARA CANJEAR', tipo='error')
            return

        # No permitir negativos
        if valor_decimal <= Decimal('0'):
            ToastWidget.show(parent_window, 'LA CANTIDAD A CANJEAR DEBE SER MAYOR QUE 0', tipo='error')
            return

        # Validaciones: no puede superar saldo ni el total del ticket
        if valor_decimal > saldo:
            ToastWidget.show(parent_window, 'LA CANTIDAD INDICADA SUPERA EL SALDO DEL CLIENTE', tipo='error')
            return

        # Comparar contra el total bruto del ticket
        try:
            if valor_decimal > total_actual:
                ToastWidget.show(parent_window, 'LA CANTIDAD NO PUEDE SUPERAR EL SUBTOTAL + IVA DEL TICKET', tipo='error')
                return
        except Exception:
            logging.exception('Error comparando valor a canjear con total_actual')
            ToastWidget.show(parent_window, 'NO SE PUDO VALIDAR LA CANTIDAD A CANJEAR', tipo='error')
            return

        # Aplicar canje
        try:
            self.carrito_service.aplicar_canje_puntos(valor_decimal)
            try:
                if hasattr(self.view, 'update_display') and callable(getattr(self.view, 'update_display')):
                    self.view.update_display()
                elif hasattr(self.view, 'carrito_ui') and hasattr(self.view.carrito_ui, 'update_display'):
                    self.view.carrito_ui.update_display()
            except Exception:
                logging.exception('Error actualizando UI tras canje')
            logging.info(f"Canje de {valor_decimal} puntos aplicado")
        except Exception:
            logging.exception('Error aplicando canje de tesoro')
            ToastWidget.show(parent_window, 'NO SE PUDO APLICAR EL CANJE DE TESORO', tipo='error')
