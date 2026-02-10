from kool_tpv.modulos.impresion.venta_ticket_generator import VentaTicketGenerator
import logging


class ImpresoraService:
    def __init__(self, db=None, imprimir_en_consola=True, verbose=False):
        self.db = db
        self.imprimir_en_consola = imprimir_en_consola
        self.verbose = verbose
        self.ticket_generator = VentaTicketGenerator()
        self.logger = logging.getLogger(__name__)
        # Cargar configuración de ticket desde BD
        self.config = self._load_config_from_db()

    def _load_config_from_db(self):
        """Cargar configuración del ticket desde tabla configuracion.

        Claves esperadas:
        - ticket_nombre_negocio
        - ticket_direccion
        - ticket_nif
        - ticket_pie_texto

        Returns:
            dict con configuración (usa fallback si no existe en BD)
        """
        # Valores por defecto (fallback)
        config = {
            'nombre_negocio': 'KOOL DREAMS',
            'direccion': 'C/ Ejemplo 123, Ciudad',
            'nif': 'NIF: 00000000A',
            'pie_texto': 'Gracias por su compra'
        }

        if self.db is None:
            return config

        # Leer de BD
        try:
            claves = ['ticket_nombre_negocio', 'ticket_direccion', 'ticket_nif', 'ticket_pie_texto']
            mapeo = {
                'ticket_nombre_negocio': 'nombre_negocio',
                'ticket_direccion': 'direccion',
                'ticket_nif': 'nif',
                'ticket_pie_texto': 'pie_texto'
            }

            for clave_bd in claves:
                try:
                    row = self.db.fetch_one(
                        "SELECT valor FROM configuracion WHERE clave = ?",
                        (clave_bd,)
                    )
                    if row and row[0]:
                        clave_config = mapeo[clave_bd]
                        config[clave_config] = row[0]
                except Exception:
                    pass  # Usar fallback para esta clave
        except Exception:
            logging.exception('Error cargando configuración de ticket desde BD')

        return config

    def imprimir_ticket(self, ticket_data, items, cliente_data=None):
        texto = self.ticket_generator.generate(self.config, ticket_data, items, cliente_data)

        if self.imprimir_en_consola:
            print("\n" + "="*50)
            print(" SIMULACIÓN IMPRESIÓN TICKET ")
            print("="*50 + "\n")
            print(texto)
            print("\n" + "="*50 + "\n")

        self.logger.info("Ticket impreso (simulado) num_ticket=%s", ticket_data.get('num_ticket'))
# Servicio para gestión de la impresora y envío de trabajos de impresión
# Placeholder para integración con impresoras térmicas u otros dispositivos.

    def generar_ticket_desde_id(self, ticket_id: int) -> str:
        """Generar ticket completo desde ID (reconstruir desde BD).

        Args:
            ticket_id: ID del ticket

        Returns:
            Texto del ticket formateado, o None si no existe
        """
        try:
            from decimal import Decimal

            # Obtener ticket
            ticket_row = self.db.fetch_one(
                """SELECT id, num_ticket, created_at, cajero, cliente, cliente_id,
                          total, forma_pago, importe_efectivo, importe_tarjeta,
                          tesoro_ganado, tesoro_gastado
                   FROM tickets WHERE id = ?""",
                (ticket_id,)
            )

            if not ticket_row:
                return None

            # Obtener líneas
            lines = self.db.fetch_all(
                "SELECT sku, nombre, cantidad, precio, iva FROM ticket_lines WHERE ticket_id = ?",
                (ticket_id,)
            )

            # Construir items
            items = []
            subtotal_calc = Decimal('0')
            iva_desglose = {}

            for line in lines:
                cantidad = int(float(line[2])) if line[2] else 0
                precio = Decimal(str(line[3])) if line[3] else Decimal('0')
                tipo_iva = int(float(line[4])) if line[4] else 21

                # Calcular base imponible (precio ya incluye IVA)
                total_linea = precio * cantidad
                base = total_linea / (1 + Decimal(tipo_iva) / 100)
                cuota_iva = total_linea - base

                subtotal_calc += base

                # Acumular IVA por tipo
                if tipo_iva not in iva_desglose:
                    iva_desglose[tipo_iva] = Decimal('0')
                iva_desglose[tipo_iva] += cuota_iva

                items.append({
                    'sku': line[0],
                    'nombre': line[1],
                    'cantidad': cantidad,
                    'pvp': float(precio),
                    'tipo_iva': tipo_iva
                })

            # Separar fecha y hora
            fecha_completa = ticket_row[2] or ''
            if ' ' in fecha_completa:
                fecha, hora = fecha_completa.split(' ', 1)
            else:
                fecha = fecha_completa
                hora = ''

            # Calcular entregado y cambio
            total = Decimal(str(ticket_row[6]))
            forma_pago = ticket_row[7]
            importe_efectivo = Decimal(str(ticket_row[8])) if ticket_row[8] else Decimal('0')
            importe_tarjeta = Decimal(str(ticket_row[9])) if ticket_row[9] else Decimal('0')

            if forma_pago and forma_pago.lower() == 'mixto':
                entregado = importe_efectivo + importe_tarjeta
                cambio = Decimal('0')
            elif forma_pago and forma_pago.lower() == 'tarjeta':
                entregado = total
                cambio = Decimal('0')
            else:  # Efectivo
                entregado = importe_efectivo if importe_efectivo > 0 else total
                cambio = entregado - total if entregado > total else Decimal('0')

            # Construir ticket_data
            ticket_data = {
                'num_ticket': ticket_row[1],
                'fecha': fecha,
                'hora': hora,
                'cajero': ticket_row[3],
                'subtotal': float(subtotal_calc),
                'iva_desglose': {k: float(v) for k, v in iva_desglose.items()},
                'total': float(total),
                'forma_pago': forma_pago,
                'entregado': float(entregado),
                'cambio': float(cambio),
                'importe_efectivo': float(importe_efectivo),
                'importe_tarjeta': float(importe_tarjeta),
            }

            # Cliente si existe
            cliente_data = None
            if ticket_row[5]:  # cliente_id
                cliente_row = self.db.fetch_one(
                    """SELECT c.id, c.nombre, c.tesoro_total, c.id_nivel,
                              n.nombre_nivel, n.grafismo_nivel, n.level
                       FROM clientes c
                       LEFT JOIN niveles_fidelidad n ON c.id_nivel = n.id
                       WHERE c.id = ?""",
                    (ticket_row[5],)
                )

                if cliente_row:
                    # Reconstruir tesoro_data
                    tesoro_gastado = float(ticket_row[11]) if ticket_row[11] else 0.0
                    tesoro_ganado = float(ticket_row[10]) if ticket_row[10] else 0.0
                    tesoro_total_actual = float(cliente_row[2]) if cliente_row[2] else 0.0
                    tesoro_antes = tesoro_total_actual - tesoro_ganado + tesoro_gastado
                    tesoro_acumulado = tesoro_antes - tesoro_gastado

                    cliente_data = {
                        'id': cliente_row[0],
                        'nombre': cliente_row[1],
                        'nivel': cliente_row[4],  # ✅ key correcta
                        'grafismo': cliente_row[5],  # ✅ key correcta
                        'level_num': cliente_row[6]  # ✅ key correcta
                    }

                    ticket_data['tesoro_data'] = {
                        'gastado': tesoro_gastado,  # ✅ key correcta
                        'antes': tesoro_antes,
                        'acumulado': tesoro_acumulado,  # ✅ key correcta
                        'ganado': tesoro_ganado,  # ✅ key correcta
                        'total': tesoro_total_actual  # ✅ key correcta
                    }

            # Generar ticket
            return self.ticket_generator.generate(self.config, ticket_data, items, cliente_data)

        except Exception:
            logging.exception(f'Error generando ticket desde ID {ticket_id}')
            return None
