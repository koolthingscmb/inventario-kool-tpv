"""Validador CSV específico para albaranes, con detección de productos existentes."""
import logging
from dataclasses import dataclass, field
from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple

from kool_tpv.base_datos.producto_service import ProductoService
from kool_tpv.base_datos.money_adapter import calcular_descuento_porcentaje, calcular_importe_con_descuento, prepare_for_db
from kool_tpv.utils.csv_import.albaran_csv_formulas import aplicar_formulas

logger = logging.getLogger(__name__)


@dataclass
class CsvAlbaranLine:
    """Representa una línea del CSV parseada y validada.

    Todos los campos monetarios (coste, descuento, importe) están en CÉNTIMOS (int)
    para consistencia con la base de datos.
    """
    ean: str
    nombre: str
    cantidad: int
    coste_cents: int  # Coste unitario neto en céntimos
    tipo_iva: int
    # Campos opcionales
    editorial: str = ''
    fabricante: str = ''
    pvpr_cents: int = 0  # PVP recomendado en céntimos
    existe_en_bd: bool = False
    producto_id: Optional[int] = None
    errores: List[str] = field(default_factory=list)

    @property
    def importe_cents(self) -> int:
        """Importe de la línea en céntimos (coste neto × cantidad)."""
        return self.coste_cents * self.cantidad


@dataclass
class CsvImportResult:
    """Resultado completo del análisis de un CSV de albarán."""
    lineas: List[CsvAlbaranLine] = field(default_factory=list)
    productos_existentes: List[CsvAlbaranLine] = field(default_factory=list)
    productos_nuevos: List[CsvAlbaranLine] = field(default_factory=list)
    errores_parseo: List[str] = field(default_factory=list)
    totales: Dict[str, Decimal] = field(default_factory=dict)

    def calcular_totales(self) -> Dict[str, Decimal]:
        """Calcula los totales del albarán."""
        total_neto = Decimal('0.0')
        total_iva_4 = Decimal('0.0')
        total_iva_10 = Decimal('0.0')
        total_iva_21 = Decimal('0.0')

        for linea in self.lineas:
            importe = Decimal(str(linea.importe))
            total_neto += importe

            iva_aplicable = Decimal(str(linea.tipo_iva)) / Decimal('100')
            importe_iva = importe * iva_aplicable

            if linea.tipo_iva == 4:
                total_iva_4 += importe_iva
            elif linea.tipo_iva == 10:
                total_iva_10 += importe_iva
            elif linea.tipo_iva == 21:
                total_iva_21 += importe_iva

        total = total_neto + total_iva_4 + total_iva_10 + total_iva_21

        self.totales = {
            'total_neto': total_neto,
            'total_iva_4': total_iva_4,
            'total_iva_10': total_iva_10,
            'total_iva_21': total_iva_21,
            'total': total,
        }
        return self.totales


class AlbaranCsvValidator:
    """Valida líneas de CSV contra la base de datos de productos."""

    def __init__(self, db):
        self.db = db
        self.producto_service = ProductoService(db)

    def validar_datos(self, datos_csv: List[Dict[str, Any]], mapeo: Dict[str, Any] = None) -> CsvImportResult:
        """
        Valida los datos parseados del CSV y clasifica productos existentes vs nuevos.

        Args:
            datos_csv: Lista de diccionarios del parser

        Returns:
            CsvImportResult con líneas clasificadas y validadas
        """
        resultado = CsvImportResult()

        for i, fila in enumerate(datos_csv, start=2):
            # Aplicar fórmulas del proveedor si hay mapeo con flags activas
            if mapeo:
                fila = aplicar_formulas(fila, mapeo)

            # Leer valores del CSV (en euros)
            coste_euros = Decimal(str(fila.get('coste', 0.0)))
            dto_porcentaje = fila.get('descuento', 0)  # Porcentaje (ej: 30 para 30%)
            tipo_iva = fila.get('tipo_iva', 21)

            # Campos opcionales
            editorial = fila.get('editorial', '')
            fabricante = fila.get('fabricante', '')
            pvpr_euros = Decimal(str(fila.get('pvpr', 0.0)))
            pvpr_cents = prepare_for_db(pvpr_euros)

            # Convertir a céntimos (coste ya es neto)
            coste_cents = prepare_for_db(coste_euros)

            # Crear objeto línea con valores en céntimos
            linea = CsvAlbaranLine(
                ean=fila.get('ean', ''),
                nombre=fila.get('nombre', ''),
                cantidad=fila.get('cantidad', 0),
                coste_cents=coste_cents,
                tipo_iva=tipo_iva,
                editorial=editorial,
                fabricante=fabricante,
                pvpr_cents=pvpr_cents,
            )

            # Validaciones básicas
            if not linea.ean:
                linea.errores.append("EAN vacío")
            if linea.cantidad <= 0:
                linea.errores.append(f"Cantidad inválida: {linea.cantidad}")
            if linea.coste_cents < 0:
                linea.errores.append(f"Coste negativo: {linea.coste_cents}")

            # Buscar producto en BD por EAN
            try:
                producto = self._buscar_producto_por_ean(linea.ean)
                if producto:
                    linea.existe_en_bd = True
                    linea.producto_id = producto.get('id')
                    # Si no viene nombre en CSV, usar el de la BD
                    if not linea.nombre and producto.get('nombre'):
                        linea.nombre = producto['nombre']
                    resultado.productos_existentes.append(linea)
                else:
                    linea.existe_en_bd = False
                    resultado.productos_nuevos.append(linea)
            except Exception as e:
                logger.warning(f"Error buscando producto EAN {linea.ean}: {e}")
                linea.existe_en_bd = False
                resultado.productos_nuevos.append(linea)

            resultado.lineas.append(linea)

        # Calcular totales
        resultado.calcular_totales()

        logger.info(
            f"Validación CSV: {len(resultado.productos_existentes)} existentes, "
            f"{len(resultado.productos_nuevos)} nuevos, "
            f"{len([l for l in resultado.lineas if l.errores])} con errores"
        )

        return resultado

    def _buscar_producto_por_ean(self, ean: str) -> Optional[Dict[str, Any]]:
        """Busca un producto por su código EAN."""
        try:
            # Usar el mismo método que AlbaranService para consistencia
            query = """
                SELECT p.id, p.nombre, p.tipo_iva
                FROM productos p
                INNER JOIN codigos_barras cb ON cb.producto_id = p.id
                WHERE cb.ean = ?
                LIMIT 1
            """
            row = self.db.fetch_one(query, (ean,))
            if row:
                return {
                    'id': row[0],
                    'nombre': row[1],
                    'tipo_iva': int(row[2] or 21)
                }
            return None
        except Exception as e:
            logger.warning(f"Error en query EAN {ean}: {e}")
            return None

    def validar_para_guardado(self, resultado: CsvImportResult) -> Tuple[bool, List[str]]:
        """
        Valida si el resultado está listo para guardar como albarán.

        Returns:
            (es_valido, lista_errores)
        """
        errores = []

        if not resultado.lineas:
            errores.append("No hay líneas para importar")
            return False, errores

        # Verificar que no haya errores críticos
        lineas_con_errores = [l for l in resultado.lineas if l.errores]
        if lineas_con_errores:
            errores.append(f"Hay {len(lineas_con_errores)} líneas con errores que deben corregirse")

        # Verificar cantidades válidas
        cantidad_invalida = [l for l in resultado.lineas if l.cantidad <= 0]
        if cantidad_invalida:
            errores.append(f"{len(cantidad_invalida)} líneas tienen cantidad inválida")

        # Verificar que todos los EAN tengan nombre (para nuevos o existentes)
        sin_nombre = [l for l in resultado.lineas if not l.nombre]
        if sin_nombre:
            errores.append(f"{len(sin_nombre)} líneas no tienen nombre de producto")

        es_valido = len(errores) == 0
        return es_valido, errores
