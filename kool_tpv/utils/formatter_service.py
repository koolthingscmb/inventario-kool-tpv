"""
Service para formateo de datos del TPV
Formateo de precios, cantidades, descuentos, fechas, etc.
"""
from typing import Union
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
import math
from datetime import datetime


class FormatterService:
    """Servicio para formateo de datos del TPV"""
    
    def __init__(self):
        self.ticket_width = 50  # Ancho del ticket en caracteres
        self.separador = "-" * 15  # 15 guiones
    
    def format_precio(self, precio: Union[float, str, int]) -> str:
        """
        Formatear precio con redondeo a 2 decimales (ROUND_HALF_UP)
        Ejemplo: 12.567 → "12.57 €"
        """
        try:
            d = Decimal(str(precio))
            d_round = d.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            return f"{d_round:.2f} €"
        except (InvalidOperation, ValueError, TypeError):
            return "0.00 €"

    def format_tesoro(self, tesoro: Union[float, str, int, Decimal]) -> str:
        """
        Formatear valor de "tesoro" redondeando a 2 decimales (ROUND_HALF_UP).
        - Siempre devuelve una cadena con 2 decimales, sin símbolo monetario.
        - Uso: mostrar saldo de tesoro en UI (ej. '12.56').
        """
        try:
            # Convertir de forma segura a Decimal
            d = Decimal(str(tesoro))
            d_round = d.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            return f"{d_round:.2f}"
        except (InvalidOperation, ValueError, TypeError):
            return "0.00"

    def format_precio_cents(self, cents: int) -> str:
        """Recibe céntimos, convierte a euros y formatea."""
        from kool_tpv.utils.money import from_cents
        return self.format_precio(from_cents(cents))

    def format_tesoro_cents(self, cents: int) -> str:
        """Recibe céntimos, convierte a euros y formatea sin símbolo (€)."""
        from kool_tpv.utils.money import from_cents
        return self.format_tesoro(from_cents(cents))
    
    def format_cantidad(self, cantidad: Union[int, float, str]) -> str:
        """
        Formatear cantidad (solo enteros)
        Ejemplo: 2 → "2 uds"
        """
        try:
            cantidad_int = int(float(cantidad))
            return f"{cantidad_int} uds"
        except (ValueError, TypeError):
            return "0 uds"
    
    def format_descuento(self, descuento: Union[float, str, int]) -> str:
        """
        Formatear descuento en porcentaje
        Ejemplo: 0.15 → "-15%"
        """
        try:
            descuento_float = float(descuento)
            if descuento_float == 0:
                return "0%"
            descuento_porcentaje = int(descuento_float * 100)
            return f"-{descuento_porcentaje}%"
        except (ValueError, TypeError):
            return "0%"
    
    def format_fecha(self, fecha: Union[datetime, str] = None) -> str:
        """
        Formatear fecha y hora
        Ejemplo: datetime.now() → "15/01/2024 14:30"
        """
        try:
            if fecha is None:
                fecha = datetime.now()
            elif isinstance(fecha, str):
                # Si viene como string, intentar parsearlo
                fecha = datetime.fromisoformat(fecha.replace('Z', '+00:00'))
            
            return fecha.strftime("%d/%m/%Y %H:%M")
        except (ValueError, TypeError, AttributeError):
            return datetime.now().strftime("%d/%m/%Y %H:%M")
    
    def format_linea_producto(self, nombre: str, cantidad: Union[int, str], precio_total: Union[float, str]) -> str:
        """
        Formatear línea completa de producto
        Ejemplo: "Coca Cola x2 uds - 3.50 €"
        """
        try:
            cantidad_formateada = self.format_cantidad(cantidad)
            precio_formateado = self.format_precio(precio_total)
            return f"{nombre} x{cantidad_formateada} - {precio_formateado}"
        except Exception:
            return f"{nombre} x0 uds - 0.00 €"
    
    def format_separador(self) -> str:
        """
        Devolver separador estándar
        Ejemplo: "---------------"
        """
        return self.separador
    
    def format_iva(self, porcentaje_iva: Union[int, float], importe_iva: Union[float, str]) -> str:
        """
        Formatear línea de IVA
        Ejemplo: "IVA 21%: 0.99 €"
        """
        try:
            porcentaje = int(float(porcentaje_iva))
            importe_formateado = self.format_precio(importe_iva)
            return f"IVA {porcentaje}%: {importe_formateado}"
        except (ValueError, TypeError):
            return f"IVA 0%: 0.00 €"
    
    def format_subtotal(self, subtotal: Union[float, str]) -> str:
        """
        Formatear subtotal
        Ejemplo: "Subtotal: 4.70 €"
        """
        precio_formateado = self.format_precio(subtotal)
        return f"Subtotal: {precio_formateado}"
    
    def format_total(self, total: Union[float, str]) -> str:
        """
        Formatear total (para destacar visualmente)
        Ejemplo: "TOTAL: 5.74 €"
        """
        precio_formateado = self.format_precio(total)
        return f"TOTAL: {precio_formateado}"
    
    def truncar_decimales(self, numero: Union[float, str], decimales: int = 2, rounding_mode=ROUND_HALF_UP) -> Decimal:
        """
        Cuantizar número a X decimales.
        - Por defecto usa `ROUND_HALF_UP` (comportamiento financiero estándar)
        - Devuelve un `Decimal` cuantizado.
        - Si necesitas truncado puro, pasa `rounding_mode=ROUND_DOWN`.
        """
        try:
            d = Decimal(str(numero))
            if decimales <= 0:
                d_q = d.quantize(Decimal('1'), rounding=rounding_mode)
            else:
                # Construir patrón dinámico: '0.01' para decimales=2
                pattern = '0.' + ('0' * (decimales - 1)) + '1' if decimales > 0 else '1'
                d_q = d.quantize(Decimal(pattern), rounding=rounding_mode)
            return d_q
        except (InvalidOperation, ValueError, TypeError):
            return Decimal('0.00')
    
    def format_centrado(self, texto: str, ancho: int = None) -> str:
        """
        Centrar texto en el ancho del ticket
        Ejemplo para cabeceras de ticket
        """
        if ancho is None:
            ancho = self.ticket_width
        
        if len(texto) >= ancho:
            return texto[:ancho]
        
        espacios = (ancho - len(texto)) // 2
        return " " * espacios + texto

# Nota: se eliminó la función de prueba `test_formatter` para evitar
# ejecuciones accidentales de código de ejemplo. Si necesitas realizar
# pruebas unitarias, crea un script en `tests/` o usa un entorno REPL.
