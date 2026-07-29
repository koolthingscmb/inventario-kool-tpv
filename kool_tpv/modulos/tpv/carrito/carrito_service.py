"""
CarritoService: gestión del carrito de compras.

Implementación canónica: add/remove/update/clear/getters/pagos.
Todos los cálculos usan truncado mediante FormatterService.
"""
from typing import List, Dict, Optional
import logging

from decimal import Decimal
from kool_tpv.utils.formatter_service import FormatterService
from kool_tpv.modulos.tpv.carrito.financial import calculate_resumen


class CarritoService:
    """Servicio para gestión del carrito de compras"""

    def __init__(self):
        self._items: List[Dict] = []
        # _cajero will store a dict {'nombre': str, 'id': int, 'rol': str} or None
        self._cajero = None
        # cliente actual asociado al carrito (puede contener id, nombre, etc.)
        self._cliente: Optional[Dict] = None
        self._forma_pago: str = ""
        self._total_pagado = Decimal('0.00')
        self._efectivo_entregado = Decimal('0.00')
        self._cambio_devuelto = Decimal('0.00')
        self._num_ticket: Optional[int] = None
        self.formatter = FormatterService()
        # puntos canjeados aplicados al carrito (Decimal for precision)
        self._puntos_canjeados = Decimal('0.00')
        # descuento aplicado al carrito: dict {'tipo': str, 'valor': Decimal, 'euros': Decimal}
        self._descuento = None
        # vale de devolución aplicado al carrito: dict con 'id', 'importe_cents'
        self._vale_aplicado = None


    def add_item(self, producto_data: Dict, parent_window=None) -> bool:
        from kool_tpv.utils.widgets.notificaciones import ToastWidget
        producto_id = producto_data.get('id')
        if producto_id is None:
            logging.error('Producto sin ID no se puede añadir al carrito')
            return False
        # Normalizar datos básicos
        line_tipo = producto_data.get('line_tipo', 'venta')
        try:
            cantidad_in = int(producto_data.get('cantidad', 1))
        except Exception:
            try:
                cantidad_in = int(float(producto_data.get('cantidad', 1)))
            except Exception:
                cantidad_in = 1

        # Bloquear la adición de artículos con cantidad positiva si hay una devolución activa
        try:
            if getattr(self, '_devolucion_active', False) and line_tipo != 'devolucion' and cantidad_in > 0:
                ToastWidget.show(parent_window, 'NO SE PUEDE INICIAR UNA VENTA CON UNA DEVOLUCIÓN EN CURSO', tipo='error')
                return False
        except Exception:
            # si hay error leyendo la bandera, no bloquear pero loguear
            logging.exception('Error comprobando estado de devolución antes de añadir item')

        # Buscar ítem existente con mismo id y mismo tipo de línea
        for item in self._items:
            try:
                if item.get('id') == producto_id and item.get('line_tipo', 'venta') == line_tipo:
                    # sumar cantidades
                    item['cantidad'] = int(item.get('cantidad', 0)) + cantidad_in
                    # Normalizar pvp y total_linea a Decimal (evitar floats)
                    pvp_dec = Decimal(str(item.get('pvp', 0)))
                    item['pvp'] = pvp_dec
                    item['total_linea'] = pvp_dec * Decimal(item['cantidad'])
                    return True
            except Exception:
                continue

        # Use Decimal for internal calculations but keep pvp stored (Decimal-compatible)
        pvp_raw = producto_data.get('pvp', 0.0)
        try:
            pvp_dec = Decimal(str(pvp_raw))
        except Exception:
            pvp_dec = Decimal('0.00')

        nuevo = {
            'id': producto_id,
            'sku': producto_data.get('sku', ''),
            'nombre': producto_data.get('nombre', 'Producto'),
            'pvp': pvp_dec,
            'cantidad': cantidad_in,
            'tipo_iva': int(producto_data.get('tipo_iva', 21)),
            'total_linea': pvp_dec * Decimal(cantidad_in),
            'line_tipo': producto_data.get('line_tipo', 'venta')
        }
        # ensure numeric fields are Decimal/int
        try:
            nuevo['pvp'] = Decimal(str(nuevo.get('pvp', 0)))
            nuevo['total_linea'] = Decimal(str(nuevo.get('total_linea', 0)))
            nuevo['cantidad'] = int(nuevo.get('cantidad', 0))
        except Exception:
            logging.exception('Error normalizando valores del nuevo item')
        self._items.append(nuevo)
        logging.info(f"Producto añadido al carrito: {producto_data.get('nombre')}")
        return True

    def remove_item(self, index: int) -> bool:
        if 0 <= index < len(self._items):
            eliminado = self._items.pop(index)
            logging.info(f"Producto eliminado del carrito: {eliminado.get('nombre')}")
            # Si se elimina una línea, comprobar si aún quedan líneas de devolución;
            # si no quedan, desactivar modo devolución para permitir ventas posteriores.
            try:
                has_devol = any(str(it.get('line_tipo', '')).lower() == 'devolucion' for it in self._items)
                setattr(self, '_devolucion_active', bool(has_devol))
                # Si tras eliminar no quedan items, olvidar descuentos y puntos canjeados
                if len(self._items) == 0:
                    try:
                        self._descuento = None
                        self._puntos_canjeados = Decimal('0.00')
                        self._vale_aplicado = None
                    except Exception:
                        self._descuento = None
                        self._puntos_canjeados = Decimal(0)
                        self._vale_aplicado = None
            except Exception:
                logging.exception('Error actualizando bandera _devolucion_active tras eliminar item')
            return True
        logging.warning(f"Índice inválido para eliminar: {index}")
        return False

    def update_cantidad(self, index: int, nueva_cantidad: int) -> bool:
        if not (0 <= index < len(self._items)):
            return False
        if nueva_cantidad <= 0:
            return self.remove_item(index)
        item = self._items[index]
        item['cantidad'] = nueva_cantidad
        pvp_dec = Decimal(str(item.get('pvp', 0)))
        item['total_linea'] = pvp_dec * Decimal(nueva_cantidad)
        return True

    def clear(self) -> None:
        self._items.clear()
        self._forma_pago = ''
        self._total_pagado = Decimal('0.00')
        self._efectivo_entregado = Decimal('0.00')
        self._cambio_devuelto = Decimal('0.00')
        self._num_ticket = None
        # limpiar cliente asociado al carrito
        if getattr(self, '_cliente', None) is not None:
            logging.info(f"Cliente limpiado del carrito: {self._cliente}")
        self._cliente = None
        # reset puntos canjeados
        try:
            self._puntos_canjeados = Decimal('0.00')
        except Exception:
            self._puntos_canjeados = Decimal(0)
        # limpiar descuento aplicado
        try:
            self._descuento = None
        except Exception:
            self._descuento = None
        # limpiar vale aplicado
        try:
            self._vale_aplicado = None
        except Exception:
            self._vale_aplicado = None
        
        # Al limpiar el carrito también debe desactivarse el modo devolución
        try:
            setattr(self, '_devolucion_active', False)
        except Exception:
            pass
        logging.info('Carrito limpiado completamente')

    def get_items(self) -> List[Dict]:
        return [item.copy() for item in self._items]

    def get_item_count(self) -> int:
        return sum(item['cantidad'] for item in self._items)

    def get_subtotal(self) -> Decimal:
        subtotal = Decimal('0.00')
        for item in self._items:
            pvp_dec = Decimal(str(item.get('pvp', 0)))
            iva_factor = Decimal('1') + (Decimal(item.get('tipo_iva', 21)) / Decimal('100'))
            precio_sin_iva = pvp_dec / iva_factor
            sign = Decimal('-1') if str(item.get('line_tipo', 'venta')) == 'devolucion' else Decimal('1')
            subtotal += precio_sin_iva * Decimal(item.get('cantidad', 0)) * sign
        # Devolver Decimal sin truncar; la vista/impresión hará el formateo
        return subtotal

    def get_iva_desglose(self) -> Dict[int, Decimal]:
        iva_desglose: Dict[int, Decimal] = {}
        for item in self._items:
            pvp_dec = Decimal(str(item.get('pvp', 0)))
            cantidad = Decimal(item.get('cantidad', 0))
            iva_rate = Decimal(item.get('tipo_iva', 21)) / Decimal('100')
            sign = Decimal('-1') if str(item.get('line_tipo', 'venta')) == 'devolucion' else Decimal('1')
            base = (pvp_dec / (Decimal('1') + iva_rate)) * cantidad * sign
            iva = base * iva_rate
            key = int(item.get('tipo_iva', 21))
            iva_desglose[key] = iva_desglose.get(key, Decimal('0.00')) + iva

        # Asegurar claves mínimas y devolver Decimals sin truncar (vistas harán el formateo)
        iva_desglose.setdefault(4, Decimal('0.00'))
        iva_desglose.setdefault(21, Decimal('0.00'))
        return iva_desglose

    def get_total_iva(self) -> Decimal:
        return sum(self.get_iva_desglose().values(), Decimal('0.00'))

    def get_total_deprecated(self) -> Decimal:
        # Esta versión anterior se mantiene como método renombrado por compatibilidad interna.
        total = Decimal('0.00')
        for item in self._items:
            try:
                total_linea = Decimal(str(item.get('total_linea', Decimal('0.00'))))
            except Exception:
                logging.exception('Valor inválido en total_linea al calcular total')
                continue
            sign = Decimal('-1') if str(item.get('line_tipo', 'venta')) == 'devolucion' else Decimal('1')
            total += total_linea * sign

        puntos = self.get_puntos_canjeados()
        # Si ya existe una línea de tipo 'tesoro' en los items,
        # el descuento ya está representado en las líneas (total_linea negativo),
        # por lo que NO debemos restar `puntos` de nuevo.
        try:
            has_tesoro = any(str(it.get('line_tipo', '')).lower() == 'tesoro' for it in self._items)
        except Exception:
            has_tesoro = False

        if has_tesoro:
            total_after = total
        else:
            total_after = total - puntos
        if total_after < Decimal('0.00'):
            total_after = Decimal('0.00')
        return total_after

    def aplicar_canje_puntos(self, cantidad: Decimal) -> None:
        """Aplicar canje de puntos como descuento monetario sobre el total del carrito.

        `cantidad` debe ser un Decimal representando la cantidad monetaria a descontar.
        Guarda el valor en `self._puntos_canjeados`.
        """
        try:
            if cantidad is None:
                cantidad = Decimal('0.00')
            self._puntos_canjeados = Decimal(str(cantidad))
        except Exception:
            logging.exception('Error aplicando canje de puntos')
            self._puntos_canjeados = Decimal('0.00')

    def set_puntos_canjeados(self, cantidad) -> None:
        """Alias explícito que normaliza y guarda `puntos_canjeados` como Decimal."""
        try:
            if cantidad is None:
                cantidad = Decimal('0.00')
            self._puntos_canjeados = Decimal(str(cantidad))
        except Exception:
            logging.exception('Error en set_puntos_canjeados')
            self._puntos_canjeados = Decimal('0.00')

    def get_puntos_canjeados(self) -> Decimal:
        """Devuelve la cantidad de puntos canjeados actualmente aplicados al carrito."""
        try:
            return Decimal(str(self._puntos_canjeados))
        except Exception:
            return Decimal('0.00')

    def aplicar_descuento(self, descuento_data: Dict) -> None:
        """Aplica un descuento al carrito.

        descuento_data: {'tipo': 'directo'|'porcentaje', 'valor': float, 'euros': float}
        """
        if not self._items:
            raise ValueError('No hay productos en el carrito')

        # No permitir aplicar descuento si ya hay puntos canjeados
        try:
            puntos = self.get_puntos_canjeados()
            try:
                puntos_dec = Decimal(str(puntos))
            except Exception:
                puntos_dec = puntos
            if puntos_dec > Decimal('0.00'):
                raise ValueError('No se puede aplicar un descuento mientras hay puntos canjeados. Elimine el canje primero.')
        except ValueError:
            # re-raise Validation error
            raise
        except Exception:
            # si hay error leyendo puntos, no bloquear (pero loguear)
            logging.exception('Error comprobando puntos canjeados antes de aplicar descuento')

        # Obtener subtotal SIN IVA y total IVA para calcular el bruto
        resumen = self.get_resumen_financiero()
        try:
            subtotal = Decimal(str(resumen.get('subtotal', '0')))
        except Exception:
            subtotal = Decimal('0.00')
        try:
            total_iva_res = Decimal(str(resumen.get('total_iva', '0')))
        except Exception:
            total_iva_res = Decimal('0.00')
        # total bruto (precio con IVA) sobre el que debe calcularse un descuento porcentual
        total_bruto = subtotal + total_iva_res

        tipo = descuento_data.get('tipo')
        try:
            valor = Decimal(str(descuento_data.get('valor', 0)))
        except Exception:
            valor = Decimal('0.00')

        if tipo == 'directo':
            euros_descuento = valor
        elif tipo == 'porcentaje':
            # calcular euros sobre el importe bruto (precio CON IVA)
            euros_descuento = (total_bruto * valor / Decimal('100'))
        else:
            raise ValueError('Tipo de descuento inválido')

        # Validar que el descuento no supere el total bruto (no tiene sentido descontar más del total)
        if euros_descuento > total_bruto:
            raise ValueError(f"El descuento ({euros_descuento}€) no puede superar el total ({total_bruto}€)")

        # Guardar descuento
        try:
            self._descuento = {
                'tipo': tipo,
                'valor': valor,
                'euros': euros_descuento
            }
            logging.info(f"Descuento aplicado: {self._descuento}")
        except Exception:
            logging.exception('Error guardando descuento en carrito')

    def eliminar_descuento(self) -> None:
        try:
            self._descuento = None
            logging.info('Descuento eliminado')
        except Exception:
            logging.exception('Error eliminando descuento')

    def get_descuento(self) -> Optional[Dict]:
        return self._descuento

    def has_descuento(self) -> bool:
        """Indica si hay un descuento aplicado y mayor que 0€."""
        try:
            d = self._descuento
            if not d:
                return False
            euros = d.get('euros', Decimal('0.00'))
            try:
                euros_dec = Decimal(str(euros))
            except Exception:
                euros_dec = Decimal('0.00')
            return euros_dec > Decimal('0.00')
        except Exception:
            logging.exception('Error comprobando existencia de descuento')
            return False

    def set_cajero(self, nombre_cajero: str) -> None:
        try:
            # Allow passing either a dict {'nombre', 'id', 'rol'} or a name string
            if isinstance(nombre_cajero, dict):
                self._cajero = nombre_cajero.copy()
            else:
                # legacy: only name provided
                self._cajero = {'nombre': nombre_cajero, 'id': None, 'rol': None}
        except Exception:
            self._cajero = {'nombre': nombre_cajero, 'id': None, 'rol': None}

    def get_cajero(self):
        try:
            return None if not self._cajero else self._cajero.copy()
        except Exception:
            return None

    def set_cliente(self, cliente_data: Dict) -> None:
        """Asignar cliente al carrito. `cliente_data` puede contener al menos `id` y `nombre`."""
        try:
            self._cliente = cliente_data.copy() if isinstance(cliente_data, dict) else {'id': cliente_data}
            logging.info(f"Cliente asignado al carrito: {self._cliente}")
        except Exception:
            logging.exception('Error asignando cliente al carrito')

    def get_cliente(self) -> Optional[Dict]:
        """Retornar el cliente actualmente asignado al carrito, o None."""
        try:
            return self._cliente.copy() if isinstance(self._cliente, dict) else self._cliente
        except Exception:
            logging.exception('Error obteniendo cliente del carrito')
            return None

    def set_forma_pago(self, forma_pago: str, efectivo_entregado: float = 0.0) -> bool:
        if forma_pago not in ['Efectivo', 'Tarjeta', 'Web']:
            logging.error(f"Forma de pago inválida: {forma_pago}")
            return False
        self._forma_pago = forma_pago
        # Obtener total como Decimal
        total = self.get_total()
        self._total_pagado = total
        if forma_pago == 'Efectivo':
            try:
                efectivo_dec = Decimal(str(efectivo_entregado))
            except Exception:
                efectivo_dec = Decimal('0.00')
            self._efectivo_entregado = efectivo_dec
            cambio = efectivo_dec - total
            self._cambio_devuelto = cambio
            if self._cambio_devuelto < Decimal('0.00'):
                logging.error('Efectivo entregado insuficiente')
                return False
        else:
            self._efectivo_entregado = Decimal('0.00')
            self._cambio_devuelto = Decimal('0.00')
        return True

    def get_datos_pago(self) -> Dict:
        return {
            'forma_pago': self._forma_pago,
            'total_pagado': self._total_pagado,
            'efectivo_entregado': self._efectivo_entregado,
            'cambio_devuelto': self._cambio_devuelto
        }

    def set_num_ticket(self, num_ticket: int) -> None:
        self._num_ticket = num_ticket

    def get_num_ticket(self) -> Optional[int]:
        return self._num_ticket

    def is_empty(self) -> bool:
        return len(self._items) == 0

    def get_resumen_financiero(self) -> Dict:
        # Delegate calculation to financial.calculate_resumen which applies per-line rounding
        try:
            puntos = self.get_puntos_canjeados()
        except Exception:
            logging.exception('Error obteniendo puntos canjeados')
            puntos = Decimal('0.00')

        resumen = calculate_resumen(self._items, puntos_canjeados=puntos, descuento=self._descuento)

        # Aplicar vale de devolución si existe
        if self._vale_aplicado:
            try:
                from kool_tpv.base_datos.money_adapter import read_from_db
                vale_euros = read_from_db(self._vale_aplicado['importe_cents'])
                total_actual = Decimal(str(resumen.get('total', '0')))
                nuevo_total = total_actual - vale_euros
                if nuevo_total < Decimal('0.00'):
                    nuevo_total = Decimal('0.00')
                resumen['total'] = nuevo_total
                resumen['vale_euros'] = vale_euros
                resumen['vale_id'] = self._vale_aplicado.get('id')
            except Exception:
                logging.exception('Error aplicando vale al resumen financiero')

        return resumen

    def get_total(self) -> Decimal:
        """Obtener total del carrito (con descuentos y canje aplicados).

        Returns:
            Decimal: Total final del carrito
        """
        try:
            resumen = self.get_resumen_financiero()
            total = resumen.get('total', Decimal('0.00'))
            # Asegurar que es Decimal
            if not isinstance(total, Decimal):
                total = Decimal(str(total))
            return total
        except Exception:
            logging.exception('Error obteniendo total del carrito')
            return Decimal('0.00')

    def get_ticket_type(self) -> str:
        """Determina el tipo de ticket según el estado del carrito.

        Reglas:
        - Si hay items con `line_tipo == 'devolucion'` -> 'devolucion'
        - Si hay cliente asignado -> 'venta_fidelizacion'
        - Default -> 'venta'

        Returns:
            str: tipo de ticket ('venta', 'venta_fidelizacion', 'devolucion', ...)
        """
        items = self.get_items() or []
        cliente = self.get_cliente()

        # Detectar devolución (pura o mixta)
        try:
            tiene_devolucion = any(str(item.get('line_tipo', '')).lower() == 'devolucion' for item in items)
        except Exception:
            tiene_devolucion = False
        if tiene_devolucion:
            return 'devolucion'

        # Detectar venta con fidelización (si hay cliente)
        try:
            if cliente:
                return 'venta_fidelizacion'
        except Exception:
            pass

        # Default: venta normal
        return 'venta'

    # ------------------------------------------------------------------
    # Vale de devolución
    # ------------------------------------------------------------------
    def aplicar_vale(self, vale_data: Dict) -> None:
        """Aplica un vale de devolución al carrito.

        vale_data: dict con al menos 'id' (str) e 'importe_cents' (int).
        El importe se resta del total del carrito en get_resumen_financiero().
        """
        if not vale_data or 'id' not in vale_data or 'importe_cents' not in vale_data:
            raise ValueError('Datos de vale inválidos: requiere id e importe_cents')
        self._vale_aplicado = {
            'id': vale_data['id'],
            'importe_cents': int(vale_data['importe_cents']),
        }
        logging.info(f"Vale aplicado al carrito: {self._vale_aplicado}")

    def get_vale_aplicado(self) -> Optional[Dict]:
        """Devuelve el vale aplicado o None."""
        return self._vale_aplicado.copy() if self._vale_aplicado else None

    def quitar_vale(self) -> None:
        """Elimina el vale aplicado del carrito."""
        if self._vale_aplicado:
            logging.info(f"Vale removido del carrito: {self._vale_aplicado['id']}")
        self._vale_aplicado = None

    # ------------------------------------------------------------------
    def apply_discount_tipo(self, tipo: str, valor=None) -> bool:
        """Convenience wrapper to apply a discount by `tipo`.

        - tipo '%' expects `valor` as Decimal (percentage, e.g. Decimal('10')).
        - tipo '€' expects `valor` as Decimal representing euros.

        Returns True when applied successfully.
        """
        try:
            from decimal import Decimal
            if tipo == '%':
                if valor is None:
                    raise ValueError('Porcentaje requerido')
                pct = Decimal(str(valor))
                self.aplicar_descuento({'tipo': 'porcentaje', 'valor': pct})
                return True
            elif tipo == '€' or tipo == 'directo':
                if valor is None:
                    raise ValueError('Importe requerido')
                euros = Decimal(str(valor))
                self.aplicar_descuento({'tipo': 'directo', 'valor': euros})
                return True
            else:
                # unsupported tipo
                raise ValueError(f"Tipo de descuento desconocido: {tipo}")
        except Exception:
            # Let caller handle/log exceptions; do not swallow all
            raise
