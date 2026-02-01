"""
Servicio de impresión (limpieza inicial).

Este archivo ha sido limpiado el 2026-02-01. El contenido original se ha
respaldado en `backups/impresion_print_service.py.backup.2026-02-01`.

Objetivo: dejar una plantilla segura y sin lógica de impresión activa,
manteniendo las firmas públicas usadas por el resto de la aplicación
(`ImpresionService`, `imprimir_ticket`, `listar_impresoras`, `guardar_configuracion`).

NOTA: No implementar lógica de impresión real en este archivo hasta que
se planifique la reconstrucción.
"""

import logging
from typing import List, Optional


class ImpresionService:
    """Stub seguro de `ImpresionService`.

    Proporciona métodos con firmas compatibles que realizan operaciones
    neutras (simulación / no-op) para evitar errores en importaciones.
    """

    def __init__(self, config_file: str = 'Configuracion/config.ini') -> None:
        self.config_file = config_file
        self.nombre_impresora: Optional[str] = None
        self.ticket_width: str = '80mm'
        self.SIMULACION: bool = True

    def listar_impresoras(self) -> List[str]:
        """Devuelve lista vacía: no hay impresoras detectadas en el stub."""
        return []

    def guardar_configuracion(self, nombre_impresora: str, ancho_ticket: str) -> bool:
        """Almacena valores en atributos en memoria y retorna True."""
        self.nombre_impresora = nombre_impresora
        self.ticket_width = ancho_ticket
        return True

    def abrir_cajon(self) -> None:
        """No-op seguro: registra la llamada para depuración."""
        logging.info('ImpresionService.abrir_cajon() llamado (stub).')
    def imprimir_ticket(self, *args, **kwargs) -> bool:
        """Compone y simula la impresión completa del ticket usando los generadores.

        Soporta dos firmas para compatibilidad:

        1) Antigua firma (texto simple):
           imprimir_ticket(texto: str, abrir_cajon: bool = False, no_wrap: bool = False)

        2) Nueva firma (composición automática):
           imprimir_ticket(config_path: str, ticket_id: int, fecha: str, cajero: str, carrito: list, puntos_canjeados: float = 0.00, width: int = 50)

        :return: True si la simulación completó sin excepciones, False en caso contrario.
        """
        try:
            logging.info('ImpresionService.imprimir_ticket() llamado (compatibilidad).')

            # Si vienen al menos 5 args posicionales asumimos la firma nueva
            if len(args) >= 5:
                config_path, ticket_id, fecha, cajero, carrito = args[:5]
                puntos_canjeados = float(args[5]) if len(args) >= 6 else float(kwargs.get('puntos_canjeados', 0.0))
                width = int(args[6]) if len(args) >= 7 else int(kwargs.get('width', 50))

            # Detectar llamada antigua (texto simple) si no es la firma nueva
            elif len(args) >= 1 and isinstance(args[0], str) and ('config_path' not in kwargs and 'ticket_id' not in kwargs):
                texto = args[0]
                abrir_cajon = False
                no_wrap = False
                if len(args) >= 2:
                    abrir_cajon = bool(args[1])
                if len(args) >= 3:
                    no_wrap = bool(args[2])

                # Simulación antigua: imprimir texto
                print('\n[IMPRESIÓN SIMULADA - TEXTO]')
                print(texto if texto is not None else '(sin contenido)')
                if abrir_cajon:
                    logging.info('Simulación: abrir cajón solicitado (antiguo).')
                return True
            else:
                config_path = kwargs.get('config_path') or kwargs.get('ruta_config') or 'Configuracion/config.ini'
                ticket_id = kwargs.get('ticket_id')
                fecha = kwargs.get('fecha')
                cajero = kwargs.get('cajero')
                carrito = kwargs.get('carrito', [])
                puntos_canjeados = float(kwargs.get('puntos_canjeados', 0.0))
                width = int(kwargs.get('width', 50))

            # Importar generadores
            try:
                from modulos.impresion.ticket_generator import generar_encabezado, generar_linea_fija, generar_cuerpo
            except Exception:
                logging.exception('No se pudo importar generadores de ticket')
                return False

            encabezado = generar_encabezado(config_path, width)
            linea_fija = generar_linea_fija(ticket_id, fecha, cajero, width)
            cuerpo = generar_cuerpo(carrito, puntos_canjeados, width)

            # Intentar obtener resumen financiero desde kwargs; si no, calcular fallback
            subtotal = kwargs.get('subtotal')
            desglose_iva = kwargs.get('desglose_iva')
            total = kwargs.get('total')
            forma_pago = kwargs.get('forma_pago')

            if subtotal is None or desglose_iva is None or total is None:
                # Calcular a partir del carrito (asumiendo precios brutos en 'precio')
                try:
                    subtotal_calc = 0.0
                    iva_map = {}
                    total_calc = 0.0
                    for it in (carrito or []):
                        try:
                            cantidad = int(it.get('cantidad', 1))
                        except Exception:
                            cantidad = 1
                        try:
                            precio = float(it.get('precio', 0.0))
                        except Exception:
                            precio = 0.0
                        try:
                            iva_pct = float(it.get('iva', 0) or 0)
                        except Exception:
                            iva_pct = 0.0

                        linea_total = round(cantidad * precio, 2)
                        total_calc += linea_total
                        if iva_pct and iva_pct > 0:
                            # Suponer que `precio` incluye IVA -> extraer IVA
                            try:
                                iva_amount = linea_total * (iva_pct / (100.0 + iva_pct))
                            except Exception:
                                iva_amount = round(linea_total * (iva_pct / 100.0), 2)
                            neto = linea_total - iva_amount
                        else:
                            iva_amount = 0.0
                            neto = linea_total

                        subtotal_calc += neto
                        key = f"{int(iva_pct)}%" if iva_pct is not None else "0%"
                        iva_map[key] = round(iva_map.get(key, 0.0) + iva_amount, 2)

                    subtotal = float(round(subtotal_calc, 2)) if subtotal is None else float(subtotal)
                    desglose_iva = iva_map if desglose_iva is None else desglose_iva
                    total = float(round(total_calc, 2)) if total is None else float(total)
                except Exception:
                    subtotal = float(kwargs.get('subtotal', 0.0) or 0.0)
                    desglose_iva = kwargs.get('desglose_iva', {}) or {}
                    total = float(kwargs.get('total', 0.0) or 0.0)

            if forma_pago is None:
                forma_pago = {
                    'pago': kwargs.get('forma_pago', 'efectivo') or 'efectivo',
                    'total': float(kwargs.get('total', total) or total or 0.0),
                    'entregado': float(kwargs.get('entregado', kwargs.get('pagado', 0.0) or 0.0)),
                    'devuelto': float(kwargs.get('devuelto', 0.0) or 0.0)
                }

            # Intentar añadir resumen financiero si el generador está disponible
            try:
                from modulos.impresion.ticket_generator import generar_resumen_financiero
                resumen = generar_resumen_financiero(subtotal, desglose_iva or {}, total, forma_pago, width=width)
            except Exception:
                resumen = []

            ticket_completo = encabezado + linea_fija + cuerpo + resumen

            # Simular la impresión (mostrar en terminal)
            print('\n=== IMPRESIÓN DE TICKET ===')
            for linea in ticket_completo:
                print(linea)
            print('=== FIN DEL TICKET ===')

            return True
        except Exception:
            logging.exception('Error al imprimir el ticket (compatibilidad)')
            return False


__all__ = ['ImpresionService']
