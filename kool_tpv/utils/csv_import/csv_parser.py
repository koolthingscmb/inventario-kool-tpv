"""Parser CSV flexible con detección automática de encoding y delimitador."""
import csv
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)


class CsvParser:
    """Parser CSV que detecta encoding y delimitador automáticamente."""

    # Mapeo de posibles nombres de columnas (case-insensitive) a nombres estándar
    COLUMN_MAPPINGS = {
        'ean': ['ean', 'codigo', 'código', 'codigo_barras', 'código_barras', 'barcode'],
        'nombre': ['nombre', 'producto', 'descripcion', 'descripción', 'articulo', 'artículo', 'item'],
        'cantidad': ['cantidad', 'uds', 'qty', 'quantity', 'unidades'],
        'coste': ['coste', 'precio', 'importe', 'price', 'cost', 'p_coste', 'p_costo'],
        'descuento': ['descuento', 'dto', 'discount', 'desc'],
        'tipo_iva': ['tipo_iva', 'iva', 'tipo_iva', 'vat', 'tax'],
    }

    def __init__(self):
        self.encoding = None
        self.delimiter = None
        self.headers = []
        self.mapped_headers = {}  # nombre_estandar -> nombre_original_csv
        self.provider_mapping = None  # Mapeo del proveedor desde BD
        self.skip_rows = 0

    def set_provider_mapping(self, mapping: Dict[str, Any]):
        """Establecer el mapeo de columnas desde el proveedor."""
        self.provider_mapping = mapping
        if mapping:
            # Extraer configuración técnica
            self.delimiter = mapping.get('separador', ';')
            self.encoding = mapping.get('encoding', 'utf-8')
            self.skip_rows = mapping.get('skip_rows', 0)
            logger.info(f'Mapeo proveedor cargado: sep={self.delimiter}, enc={self.encoding}, skip={self.skip_rows}')

    def parse_file(self, file_path: str) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        Parsea un archivo CSV y retorna las líneas de datos.

        Args:
            file_path: Ruta al archivo CSV

        Returns:
            Tuple (datos, errores):
                - datos: Lista de diccionarios con las líneas parseadas
                - errores: Lista de mensajes de error si los hay
        """
        path = Path(file_path)
        if not path.exists():
            return [], [f"Archivo no encontrado: {file_path}"]

        errors = []

        # Detectar encoding (solo si no viene del mapeo)
        if not self.encoding:
            try:
                self.encoding = self._detect_encoding(path)
            except Exception as e:
                logger.warning(f"Error detectando encoding: {e}")
                self.encoding = 'utf-8'

        # Detectar delimitador (solo si no viene del mapeo)
        if not self.delimiter:
            try:
                self.delimiter = self._detect_delimiter(path, self.encoding)
            except Exception as e:
                logger.warning(f"Error detectando delimitador: {e}")
                self.delimiter = ';'  # Default español

        # Leer CSV
        try:
            with open(path, 'r', encoding=self.encoding, newline='') as f:
                reader = csv.reader(f, delimiter=self.delimiter)
                rows = list(reader)
        except Exception as e:
            return [], [f"Error leyendo CSV: {e}"]

        if not rows:
            return [], ["CSV vacío o sin datos legibles"]

        # Saltar filas iniciales si es necesario
        start_row = self.skip_rows
        if start_row >= len(rows):
            return [], ["No hay datos después de saltar filas iniciales"]

        # Procesar headers
        self.headers = [h.strip().lower() for h in rows[start_row]]
        logger.info(f'Headers detectados en CSV: {self.headers}')

        # Usar mapeo del proveedor o autodetectar
        if self.provider_mapping:
            self.mapped_headers = self._map_headers_from_provider(self.headers)
            logger.info(f'Mapeo del proveedor aplicado: {self.mapped_headers}')
        else:
            self.mapped_headers = self._map_headers(self.headers)
            logger.info(f'Mapeo autodetectado: {self.mapped_headers}')

        # Validar columnas mínimas requeridas
        required = ['ean', 'cantidad']
        missing = [r for r in required if r not in self.mapped_headers]
        if missing:
            errors.append(f"Columnas requeridas no encontradas: {missing}. Headers detectados: {self.headers}")
            return [], errors

        # Parsear datos (empezar después de headers + filas a saltar)
        data = []
        for i, row in enumerate(rows[start_row + 1:], start=start_row + 2):
            if not row or all(not cell.strip() for cell in row):
                continue  # Saltar líneas vacías

            try:
                line_data = self._parse_row(row)
                if line_data:
                    data.append(line_data)
            except Exception as e:
                errors.append(f"Error en línea {i}: {e}")
                logger.warning(f"Error parseando línea {i}: {row}")

        logger.info(f"CSV parseado: {len(data)} líneas válidas, encoding={self.encoding}, delimiter={self.delimiter}")
        return data, errors

    def _detect_encoding(self, path: Path) -> str:
        """Detecta el encoding del archivo probando los más comunes."""
        encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'iso-8859-1', 'windows-1252']

        for enc in encodings:
            try:
                with open(path, 'r', encoding=enc) as f:
                    f.read(1024)
                    logger.debug(f"Encoding detectado: {enc}")
                    return enc
            except (UnicodeDecodeError, UnicodeError):
                continue

        return 'utf-8'  # Fallback

    def _detect_delimiter(self, path: Path, encoding: str) -> str:
        """Detecta el delimitador analizando la primera línea."""
        with open(path, 'r', encoding=encoding) as f:
            first_line = f.readline()

        # Contar ocurrencias
        semicolons = first_line.count(';')
        commas = first_line.count(',')
        tabs = first_line.count('\t')

        if semicolons > commas and semicolons > tabs:
            return ';'
        elif commas > semicolons and commas > tabs:
            return ','
        elif tabs > 0:
            return '\t'
        return ';'  # Default para España

    def _map_headers(self, headers: List[str]) -> Dict[str, str]:
        """Mapea los headers del CSV a nombres estándar (autodetección)."""
        mapped = {}
        header_set = set(headers)

        for standard_name, alternatives in self.COLUMN_MAPPINGS.items():
            for alt in alternatives:
                if alt in header_set:
                    mapped[standard_name] = alt
                    break

        return mapped

    def _map_headers_from_provider(self, headers: List[str]) -> Dict[str, str]:
        """Mapea headers usando configuración del proveedor."""
        mapped = {}
        if not self.provider_mapping:
            return mapped

        # Mapeo de nombres de campo en BD a nombres estándar del parser
        field_mapping = {
            'columna_ean': 'ean',
            'columna_nombre': 'nombre',
            'columna_cantidad': 'cantidad',
            'columna_precio': 'coste',  # PRECIO en CSV = coste para nosotros
            'columna_coste': 'coste',
            'columna_descuento': 'descuento',
            'columna_iva': 'tipo_iva',
            'columna_tipo_iva': 'tipo_iva',
            # Campos opcionales
            'columna_editorial': 'editorial',
            'columna_fabricante': 'fabricante',
            'columna_pvpr': 'pvpr',
        }

        header_set = set(headers)
        for config_key, standard_name in field_mapping.items():
            if config_key in self.provider_mapping:
                csv_column = self.provider_mapping[config_key].strip().lower()
                if csv_column in header_set:
                    mapped[standard_name] = csv_column
                    logger.debug(f'Mapeo proveedor: {standard_name} -> {csv_column}')

        return mapped

    def _parse_row(self, row: List[str]) -> Optional[Dict[str, Any]]:
        """Convierte una fila CSV en diccionario estandarizado."""
        if len(row) < len(self.headers):
            row.extend([''] * (len(self.headers) - len(row)))

        row_dict = dict(zip(self.headers, [cell.strip() for cell in row]))
        result = {}

        # Mapear a nombres estándar
        for standard, original in self.mapped_headers.items():
            result[standard] = row_dict.get(original, '')

        # Normalizar tipos de datos
        # Limpiar EAN: solo dígitos (eliminar caracteres corruptos como BOM o símbolos extra)
        ean_raw = str(result.get('ean', '')).strip()
        result['ean'] = ''.join(c for c in ean_raw if c.isdigit())
        result['nombre'] = str(result.get('nombre', '')).strip()

        # Cantidad (int)
        try:
            result['cantidad'] = int(float(str(result.get('cantidad', '0')).replace(',', '.')))
        except (ValueError, TypeError):
            result['cantidad'] = 0

        # Coste (float)
        try:
            coste_str = str(result.get('coste', '0')).replace(',', '.')
            result['coste'] = float(coste_str) if coste_str else 0.0
        except (ValueError, TypeError):
            result['coste'] = 0.0

        # Descuento (float, opcional)
        try:
            dto_str = str(result.get('descuento', '0')).replace(',', '.')
            result['descuento'] = float(dto_str) if dto_str else 0.0
        except (ValueError, TypeError):
            result['descuento'] = 0.0

        # Tipo IVA (int, default 21)
        try:
            iva_str = str(result.get('tipo_iva', '21')).replace('%', '')
            result['tipo_iva'] = int(float(iva_str)) if iva_str else 21
        except (ValueError, TypeError):
            result['tipo_iva'] = 21

        # Campos opcionales (editorial, fabricante, pvpr)
        result['editorial'] = str(result.get('editorial', '')).strip()
        result['fabricante'] = str(result.get('fabricante', '')).strip()

        # PVPR (float, opcional) - PVP recomendado
        try:
            pvpr_str = str(result.get('pvpr', '0')).replace(',', '.')
            result['pvpr'] = float(pvpr_str) if pvpr_str else 0.0
        except (ValueError, TypeError):
            result['pvpr'] = 0.0

        return result if result['ean'] else None

    def get_column_info(self) -> Dict[str, Any]:
        """Retorna información sobre las columnas detectadas."""
        return {
            'headers_raw': self.headers,
            'headers_mapped': self.mapped_headers,
            'encoding': self.encoding,
            'delimiter': self.delimiter,
        }
