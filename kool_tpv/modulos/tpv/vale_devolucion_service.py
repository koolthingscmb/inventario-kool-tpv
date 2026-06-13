"""Servicio de vales de devolución — guarda/carga/lista/elimina JSONs locales."""
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

VALES_DIR = Path(__file__).resolve().parents[3] / 'kool_tpv' / 'borradores'


class ValeDevolucionService:
    """Gestiona vales de devolución en archivos JSON locales."""

    def __init__(self):
        VALES_DIR.mkdir(parents=True, exist_ok=True)

    def _iter_vale_files(self):
        """Itera sobre todos los archivos de vale activos (antiguos y nuevos formato)."""
        for f in VALES_DIR.glob('vale_*.json'):
            yield f
        for f in VALES_DIR.glob('Vale*.json'):
            if f.name.startswith('USADO_'):
                continue
            yield f

    def _find_file_by_id(self, vale_id: str) -> Path | None:
        """Encuentra el archivo de vale por su UUID."""
        for f in self._iter_vale_files():
            try:
                data = json.loads(f.read_text(encoding='utf-8'))
                if data.get('id') == vale_id:
                    return f
            except Exception:
                continue
        return None

    def _siguiente_numero(self) -> int:
        """Cuenta vales existentes y devuelve el siguiente número secuencial."""
        count = 0
        for f in self._iter_vale_files():
            count += 1
        return count + 1

    # ------------------------------------------------------------------
    def guardar(
        self,
        importe_cents: int,
        num_ticket_devolucion: str,
        cliente_id: int | None = None,
        cliente_nombre: str | None = None,
    ) -> Path:
        """Genera un nuevo vale de devolución y lo guarda como JSON.

        Args:
            importe_cents: importe total de la devolución (positivo, en céntimos).
            num_ticket_devolucion: número de ticket de la devolución origen.
            cliente_id: id del cliente (None si es venta anónima).
            cliente_nombre: nombre del cliente (None si es anónima).

        Returns:
            Path del archivo guardado.
        """
        vale_id = str(uuid.uuid4())
        ts = datetime.now().isoformat()
        dia_mes = datetime.now().strftime('%d%m')
        n = self._siguiente_numero()
        filename = f'Vale{n}_{importe_cents}_{dia_mes}.json'
        path = VALES_DIR / filename

        data = {
            'id': vale_id,
            'fecha': ts,
            'importe_cents': int(importe_cents),
            'cliente_id': cliente_id,
            'cliente_nombre': cliente_nombre or '',
            'num_ticket_devolucion': str(num_ticket_devolucion),
            'usado': False,
            'num_ticket_venta_uso': None,
            'timestamp': ts,
        }

        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding='utf-8',
        )
        logger.info(f'Vale guardado: {path} ({importe_cents} céntimos)')
        return path

    # ------------------------------------------------------------------
    def listar(self) -> list[dict]:
        """Devuelve todos los vales ordenados del más reciente al más antiguo.

        Returns:
            Lista de dicts con todos los campos del vale más 'path'.
        """
        result = []
        for f in sorted(self._iter_vale_files(), reverse=True):
            try:
                data = json.loads(f.read_text(encoding='utf-8'))
                data['path'] = str(f)
                result.append(data)
            except Exception:
                logger.warning(f'Vale corrupto ignorado: {f}')
        return result

    # ------------------------------------------------------------------
    def listar_activos(self) -> list[dict]:
        """Devuelve solo los vales NO usados."""
        return [v for v in self.listar() if not v.get('usado', False)]

    # ------------------------------------------------------------------
    def listar_todos(self) -> list[dict]:
        """Devuelve todos los vales (activos + usados), del más reciente al más antiguo."""
        result = []
        for f in sorted(VALES_DIR.glob('*.json'), reverse=True):
            try:
                data = json.loads(f.read_text(encoding='utf-8'))
                data['path'] = str(f)
                result.append(data)
            except Exception:
                logger.warning(f'Vale corrupto ignorado: {f}')
        return result

    # ------------------------------------------------------------------
    def eliminar_por_path(self, path_str: str) -> bool:
        """Elimina un vale por su path de archivo (usado o no)."""
        try:
            p = Path(path_str)
            if p.exists():
                p.unlink()
                logger.info(f'Vale eliminado por path: {path_str}')
                return True
            return False
        except Exception:
            logger.warning(f'No se pudo eliminar vale por path: {path_str}')
            return False

    # ------------------------------------------------------------------
    def marcar_usado(self, vale_id: str, num_ticket_venta_uso: str) -> bool:
        """Marca un vale como usado, renombra el archivo a USADO_ y guarda el ticket de venta asociado.

        Args:
            vale_id: UUID del vale.
            num_ticket_venta_uso: número de ticket de la venta donde se aplicó.

        Returns:
            True si se actualizó correctamente, False en caso contrario.
        """
        try:
            path = self._find_file_by_id(vale_id)
            if not path or not path.exists():
                logger.warning(f'Vale no encontrado: {vale_id}')
                return False

            data = json.loads(path.read_text(encoding='utf-8'))
            data['usado'] = True
            data['num_ticket_venta_uso'] = str(num_ticket_venta_uso)
            data['fecha_uso'] = datetime.now().isoformat()

            # Renombrar a USADO_{nombre_original}
            nuevo_nombre = f'USADO_{path.name}'
            nuevo_path = path.with_name(nuevo_nombre)
            nuevo_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding='utf-8',
            )
            path.unlink()
            logger.info(f'Vale {vale_id} marcado como usado en venta {num_ticket_venta_uso} (renombrado a {nuevo_nombre})')
            return True
        except Exception:
            logger.exception(f'Error marcando vale {vale_id} como usado')
            return False

    # ------------------------------------------------------------------
    def eliminar(self, vale_id: str) -> bool:
        """Elimina el archivo de vale.

        Args:
            vale_id: UUID del vale.

        Returns:
            True si se eliminó, False si no existía o falló.
        """
        try:
            path = self._find_file_by_id(vale_id)
            if not path or not path.exists():
                return False
            path.unlink()
            logger.info(f'Vale eliminado: {vale_id}')
            return True
        except Exception:
            logger.warning(f'No se pudo eliminar vale: {vale_id}')
            return False

    # ------------------------------------------------------------------
    def hay_vales_activos(self) -> bool:
        """Devuelve True si existe al menos un vale no usado."""
        return any(
            not json.loads(f.read_text(encoding='utf-8')).get('usado', False)
            for f in self._iter_vale_files()
        )

    # ------------------------------------------------------------------
    def obtener_por_id(self, vale_id: str) -> dict | None:
        """Carga un vale por su UUID.

        Returns:
            Dict con los datos del vale (incluye 'path') o None.
        """
        try:
            path = self._find_file_by_id(vale_id)
            if not path or not path.exists():
                return None
            data = json.loads(path.read_text(encoding='utf-8'))
            data['path'] = str(path)
            return data
        except Exception:
            logger.warning(f'Error cargando vale {vale_id}')
            return None
