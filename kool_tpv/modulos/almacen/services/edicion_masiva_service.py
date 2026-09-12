"""Servicio de Edición Masiva de Productos.

Contiene la lógica de negocio para:
- Extracción de números de tomos/volúmenes mediante expresiones regulares.
- Generación de nombres propuestos basados en plantillas con variables ({num}, {sku}, {actual}, {id}).
- Edición masiva de PVP con operaciones (fijo, %, €) y redondeos comerciales.
- Búsqueda de lotes y aplicación transaccional en la base de datos.
"""
import re
import logging
from decimal import Decimal, ROUND_FLOOR, ROUND_CEILING
from typing import List, Dict, Any, Optional, Tuple

from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.almacen.producto_repository import ProductoRepository
from kool_tpv.base_datos.producto_service import ProductoService

logger = logging.getLogger(__name__)


class EdicionMasivaService:
    """Servicio para la edición masiva de nombres y PVP de productos."""

    # Operaciones disponibles para la edición masiva de PVP (clave -> etiqueta UI)
    OPERACIONES_PVP = {
        'fijo':      'PRECIO FIJO (€)',
        'subir_pct': 'SUBIR %',
        'bajar_pct': 'BAJAR %',
        'subir_eur': 'SUBIR €',
        'bajar_eur': 'BAJAR €',
    }

    # Opciones de redondeo comercial (siempre hacia arriba para no perder margen)
    REDONDEO_OPCIONES = {
        'ninguno': 'SIN REDONDEO',
        '95':      'TERMINAR EN .95',
        '99':      'TERMINAR EN .99',
        'entero':  'EURO ENTERO',
    }

    def __init__(self, db: Database):
        self.db = db
        self.repo = ProductoRepository(db)
        self.producto_service = ProductoService(db)

    @staticmethod
    def extraer_numero(nombre: str) -> Optional[int]:
        """Extrae el número de tomo o secuencia de un nombre de producto.
        
        Prioriza números precedidos de palabras clave (Tomo, Vol, #, Nº, No, Num, etc.),
        o si no hay palabras clave, extrae el último número aislado encontrado en el texto.
        
        Ejemplos:
            'OP 1' -> 1
            'One piece Vol. 2' -> 2
            'Manga #03' -> 3
            'Dragon Ball 3en1 Tomo 14' -> 14
            'Bleach 21' -> 21
            'Naruto 3 en 1 Vol. 5' -> 5
            'Akira' -> None
        """
        if not nombre:
            return None

        # 1. Buscar palabras clave explícitas con límites de palabra (\b)
        # Palabras: tomo, volumen, vol, num, numero, nº, no., n., #
        pattern_kw = r'\b(?:tomo|volumen|vol|num|numero|n[ºo\.]|#)\s*(\d+)'
        matches_kw = re.findall(pattern_kw, nombre, flags=re.IGNORECASE)
        if matches_kw:
            try:
                return int(matches_kw[-1])
            except ValueError:
                pass

        # 2. Si no hay palabra clave, buscar el último número aislado (\b\d+\b)
        all_numbers = re.findall(r'\b(\d+)\b', nombre)
        if all_numbers:
            try:
                return int(all_numbers[-1])
            except ValueError:
                pass

        return None

    def formatear_nombre(
        self,
        patron: str,
        producto: Dict[str, Any],
        rellenar_ceros: bool = False,
        digitos_ceros: int = 2
    ) -> str:
        """Aplica un patrón de plantilla a un producto concreto.
        
        Variables soportadas:
            {num}: Número detectado (con o sin ceros según rellenar_ceros).
            {sku}: SKU del producto.
            {actual}: Nombre actual del producto.
            {id}: ID del producto.
        """
        nombre_actual = str(producto.get('nombre') or '').strip()
        sku = str(producto.get('sku') or '').strip()
        pid = str(producto.get('id') or '').strip()

        num_int = self.extraer_numero(nombre_actual)

        if num_int is not None:
            if rellenar_ceros:
                num_str = f"{num_int:0{digitos_ceros}d}"
            else:
                num_str = str(num_int)
        else:
            num_str = ""

        # Reemplazar variables en el patrón
        resultado = patron
        resultado = resultado.replace("{num}", num_str)
        resultado = resultado.replace("{sku}", sku)
        resultado = resultado.replace("{actual}", nombre_actual)
        resultado = resultado.replace("{id}", pid)

        # Limpiar dobles espacios si {num} quedó vacío
        resultado = re.sub(r'\s+', ' ', resultado).strip()
        return resultado

    def generar_previsualizacion(
        self,
        productos: List[Dict[str, Any]],
        patron: str,
        rellenar_ceros: bool = False,
        digitos_ceros: int = 2
    ) -> List[Dict[str, Any]]:
        """Genera una lista de previsualización con el nombre propuesto para cada producto."""
        if not patron:
            patron = "{actual}"

        previsualizacion = []
        for p in productos:
            nombre_actual = str(p.get('nombre') or '').strip()
            num_detectado = self.extraer_numero(nombre_actual)
            nombre_propuesto = self.formatear_nombre(
                patron=patron,
                producto=p,
                rellenar_ceros=rellenar_ceros,
                digitos_ceros=digitos_ceros
            )

            previsualizacion.append({
                'id': p.get('id'),
                'sku': p.get('sku') or '',
                'nombre_actual': nombre_actual,
                'nombre_propuesto': nombre_propuesto,
                'num_detectado': num_detectado,
                'seleccionado': True, # Marcado por defecto para aplicar cambios
                '_raw': p
            })

        return previsualizacion

    def buscar_lote_productos(
        self,
        termino: str = "",
        categoria_id: Optional[int] = None,
        tipo_id: Optional[int] = None,
        estados: Optional[List[str]] = None,
        limit: int = 200
    ) -> List[Dict[str, Any]]:
        """Busca productos según los filtros para cargar en la herramienta de edición masiva."""
        try:
            return self.producto_service.buscar_productos_paginados(
                termino_busqueda=termino,
                categoria_id=categoria_id,
                tipo_id=tipo_id,
                estados=estados or ['activo', 'sin_stock'],
                limit=limit,
                offset=0
            )
        except Exception:
            logger.exception("Error buscando lote de productos en EdicionMasivaService")
            return []

    def get_productos_por_ids(self, ids: List[int]) -> List[Dict[str, Any]]:
        """Recarga productos concretos por ID desde la BD, en el orden dado.

        Usa `get_producto_completo` para incluir pvp/coste (Decimal en euros).
        Se usa tras guardar cambios para mostrar únicamente los productos
        modificados con sus datos actualizados, sin repetir la búsqueda original.
        """
        productos = []
        for pid in ids:
            try:
                row = self.producto_service.get_producto_completo(int(pid))
            except (ValueError, TypeError):
                row = None
            if row:
                productos.append(row)
        return productos

    def aplicar_cambios(
        self,
        cambios: List[Dict[str, Any]],
        usuario_id: Optional[int] = None
    ) -> int:
        """Aplica las modificaciones de nombre en base de datos de forma atómica.
        
        Args:
            cambios: Lista de dicts con 'id' y 'nombre_propuesto' (o 'nombre').
            usuario_id: ID del usuario para auditoría.

        Returns:
            int: Número de productos renombrados con éxito.
        """
        items_a_guardar = []
        for c in cambios:
            if not c.get('seleccionado', True):
                continue

            pid = c.get('id')
            nuevo_nombre = c.get('nombre_propuesto') or c.get('nombre')
            if pid and nuevo_nombre:
                items_a_guardar.append((pid, nuevo_nombre))

        if not items_a_guardar:
            return 0

        return self.repo.actualizar_nombres_masivo(items_a_guardar, usuario_id=usuario_id)

    # ------------------------------------------------------------------
    # Edición masiva de PVP
    # ------------------------------------------------------------------

    @staticmethod
    def _ceil_terminacion(valor: Decimal, terminacion: Decimal) -> Decimal:
        """Redondea un precio hacia arriba hasta la terminación dada (ej. .95)."""
        base = valor.quantize(Decimal('1'), rounding=ROUND_FLOOR)
        candidato = base + terminacion
        if candidato < valor:
            candidato = base + Decimal('1') + terminacion
        return candidato.quantize(Decimal('0.01'))

    def calcular_pvp_propuesto(
        self,
        pvp_actual: Any,
        operacion: str,
        valor: Any,
        redondeo: str = 'ninguno'
    ) -> Decimal:
        """Calcula el nuevo PVP para un producto según la operación y redondeo.

        Args:
            pvp_actual: PVP vigente (Decimal, euros).
            operacion: Clave de `OPERACIONES_PVP`.
            valor: Importe de la operación (€ o % según operación).
            redondeo: Clave de `REDONDEO_OPCIONES` (siempre hacia arriba).

        Returns:
            Decimal con el nuevo PVP (nunca negativo).
        """
        pvp = pvp_actual if isinstance(pvp_actual, Decimal) else Decimal(str(pvp_actual or '0'))
        v = Decimal(str(valor or '0'))

        if operacion == 'fijo':
            nuevo = v
        elif operacion == 'subir_pct':
            nuevo = pvp * (Decimal('1') + v / Decimal('100'))
        elif operacion == 'bajar_pct':
            nuevo = pvp * (Decimal('1') - v / Decimal('100'))
        elif operacion == 'subir_eur':
            nuevo = pvp + v
        elif operacion == 'bajar_eur':
            nuevo = pvp - v
        else:
            nuevo = pvp

        if nuevo < 0:
            nuevo = Decimal('0')

        if redondeo == '95':
            nuevo = self._ceil_terminacion(nuevo, Decimal('0.95'))
        elif redondeo == '99':
            nuevo = self._ceil_terminacion(nuevo, Decimal('0.99'))
        elif redondeo == 'entero':
            nuevo = nuevo.quantize(Decimal('1'), rounding=ROUND_CEILING)
        else:
            nuevo = nuevo.quantize(Decimal('0.01'))

        return nuevo

    def generar_previsualizacion_pvp(
        self,
        productos: List[Dict[str, Any]],
        operacion: str,
        valor: Any,
        redondeo: str = 'ninguno'
    ) -> List[Dict[str, Any]]:
        """Genera la previsualización de cambios de PVP para un lote de productos."""
        previsualizacion = []
        for p in productos:
            pvp_actual = p.get('pvp', Decimal('0.00'))
            if not isinstance(pvp_actual, Decimal):
                try:
                    pvp_actual = Decimal(str(pvp_actual or '0'))
                except Exception:
                    pvp_actual = Decimal('0.00')

            pvp_propuesto = self.calcular_pvp_propuesto(
                pvp_actual=pvp_actual,
                operacion=operacion,
                valor=valor,
                redondeo=redondeo
            )

            previsualizacion.append({
                'id': p.get('id'),
                'sku': p.get('sku') or '',
                'nombre_actual': str(p.get('nombre') or '').strip(),
                'pvp_actual': pvp_actual,
                'pvp_propuesto': pvp_propuesto,
                'seleccionado': True,
                '_raw': p
            })

        return previsualizacion

    def aplicar_cambios_pvp(
        self,
        cambios: List[Dict[str, Any]],
        usuario_id: Optional[int] = None
    ) -> int:
        """Aplica las modificaciones de PVP en base de datos de forma atómica.

        Args:
            cambios: Lista de dicts con 'id' y 'pvp_propuesto' (Decimal, euros).
            usuario_id: ID del usuario para auditoría.

        Returns:
            int: Número de productos con PVP actualizado.
        """
        items_a_guardar = []
        for c in cambios:
            if not c.get('seleccionado', True):
                continue
            pid = c.get('id')
            nuevo_pvp = c.get('pvp_propuesto')
            if pid and nuevo_pvp is not None:
                items_a_guardar.append((pid, nuevo_pvp))

        if not items_a_guardar:
            return 0

        return self.repo.actualizar_pvp_masivo(items_a_guardar, usuario_id=usuario_id)

