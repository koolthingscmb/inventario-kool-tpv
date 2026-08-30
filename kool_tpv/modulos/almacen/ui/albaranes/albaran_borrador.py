"""Servicio de borradores de albarán - guarda/carga/lista/elimina JSONs locales."""
import json
import logging
from datetime import datetime
from decimal import Decimal
from kool_tpv.paths import BORRADORES_DIR

logger = logging.getLogger(__name__)

# BORRADORES_DIR importado desde paths.py


class _DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        return super().default(obj)


class AlbaranBorradorService:
    """Gestiona borradores de albaranes CSV en archivos JSON locales."""

    def __init__(self):
        BORRADORES_DIR.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    def guardar(self, cabecera: dict, productos_data: dict, csv_path: str, paso: str) -> Path:
        """Serializa el estado actual y lo guarda en un JSON.

        Args:
            cabecera: dict con num_albaran, fecha, proveedor_id, proveedor_nombre
            productos_data: dict EAN -> datos del producto (puede estar vacío)
            csv_path: ruta al archivo CSV original
            paso: 'preview' | 'completar_productos' | 'vista_previa'

        Returns:
            Path del archivo guardado
        """
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        num = cabecera.get('num_albaran', 'X')
        filename = f'albaran_{num}_{ts}.json'
        path = BORRADORES_DIR / filename

        data = {
            'version': 1,
            'timestamp': datetime.now().isoformat(),
            'paso': paso,
            'csv_path': str(csv_path) if csv_path else '',
            'cabecera': cabecera,
            'productos_data': {
                ean: {k: str(v) if isinstance(v, Decimal) else v for k, v in prod.items()}
                for ean, prod in (productos_data or {}).items()
            }
        }

        path.write_text(json.dumps(data, cls=_DecimalEncoder, ensure_ascii=False, indent=2), encoding='utf-8')
        logger.info(f'Borrador guardado: {path}')
        return path

    def listar(self) -> list:
        """Devuelve lista de borradores ordenados del más reciente al más antiguo.

        Returns:
            Lista de dicts con {path, timestamp, num_albaran, proveedor_nombre, paso}
        """
        result = []
        for f in sorted(BORRADORES_DIR.glob('albaran_*.json'), reverse=True):
            try:
                data = json.loads(f.read_text(encoding='utf-8'))
                result.append({
                    'path': f,
                    'timestamp': data.get('timestamp', ''),
                    'num_albaran': data.get('cabecera', {}).get('num_albaran', '?'),
                    'proveedor_nombre': data.get('cabecera', {}).get('proveedor_nombre', '?'),
                    'paso': data.get('paso', '?'),
                })
            except Exception:
                logger.warning(f'Borrador corrupto ignorado: {f}')
        return result

    def cargar(self, path) -> dict:
        """Carga un borrador desde un archivo JSON.

        Returns:
            dict con claves: cabecera, productos_data, csv_path, paso
        """
        path = Path(path)
        data = json.loads(path.read_text(encoding='utf-8'))

        # Restaurar Decimal en productos_data donde corresponda
        campos_decimal = {'pvp', 'coste'}
        productos = {}
        for ean, prod in data.get('productos_data', {}).items():
            restored = {}
            for k, v in prod.items():
                if k in campos_decimal and v is not None:
                    try:
                        restored[k] = Decimal(str(v))
                    except Exception:
                        restored[k] = v
                else:
                    restored[k] = v
            productos[ean] = restored

        return {
            'cabecera': data.get('cabecera', {}),
            'productos_data': productos,
            'csv_path': data.get('csv_path', ''),
            'paso': data.get('paso', 'preview'),
        }

    def eliminar(self, path) -> None:
        """Elimina el archivo de borrador."""
        try:
            Path(path).unlink(missing_ok=True)
            logger.info(f'Borrador eliminado: {path}')
        except Exception:
            logger.warning(f'No se pudo eliminar borrador: {path}')

    def hay_borradores(self) -> bool:
        """Devuelve True si existe al menos un borrador."""
        return any(BORRADORES_DIR.glob('albaran_*.json'))

    def mas_reciente(self) -> dict | None:
        """Devuelve el borrador más reciente o None si no hay ninguno."""
        borradores = self.listar()
        return borradores[0] if borradores else None
