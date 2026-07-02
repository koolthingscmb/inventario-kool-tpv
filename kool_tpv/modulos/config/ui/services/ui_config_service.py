"""Servicio centralizado para gestionar archivos JSON de configuración UI."""
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional


class UIConfigService:
    """Gestiona lectura/escritura de config UI desde JSON. Sin BD."""

    CONFIG_DIR = Path("/Volumes/ALMACEN/KOOL_THINGS/KOOL_TPV_V2/kool_tpv/config")
    BACKUP_DIR = CONFIG_DIR / "backups"

    def __init__(self, config_dir: Optional[str] = None):
        self.config_dir = Path(config_dir) if config_dir else self.CONFIG_DIR
        self.backup_dir = self.config_dir / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self._observers: Dict[str, List[Callable]] = {}

    def _ruta(self, nombre: str) -> Path:
        if not nombre.endswith(".json"):
            nombre = f"{nombre}.json"
        return self.config_dir / nombre

    def cargar_json(self, nombre: str) -> dict:
        ruta = self._ruta(nombre)
        if not ruta.exists():
            return {}
        with open(ruta, "r", encoding="utf-8") as f:
            return json.load(f)

    def guardar_json(self, nombre: str, datos: dict) -> bool:
        try:
            self.crear_backup(nombre)
            ruta = self._ruta(nombre)
            with open(ruta, "w", encoding="utf-8") as f:
                json.dump(datos, f, indent=2, ensure_ascii=False)
            return True
        except Exception:
            return False

    def crear_backup(self, nombre: str) -> Optional[Path]:
        ruta = self._ruta(nombre)
        if not ruta.exists():
            return None
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{ruta.stem}_{timestamp}.backup"
        backup_path = self.backup_dir / backup_name
        shutil.copy2(ruta, backup_path)
        return backup_path

    def listar_backups(self, nombre: str) -> List[Path]:
        stem = Path(nombre).stem
        backups = [
            p for p in self.backup_dir.iterdir()
            if p.is_file() and p.name.startswith(f"{stem}_") and p.name.endswith(".backup")
        ]
        backups.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return backups

    def restaurar_backup(self, nombre: str, backup_path: Optional[str] = None) -> bool:
        ruta = self._ruta(nombre)
        if backup_path:
            origen = Path(backup_path)
        else:
            backups = self.listar_backups(nombre)
            if not backups:
                return False
            origen = backups[0]
        if not origen.exists():
            return False
        self.crear_backup(nombre)
        shutil.copy2(origen, ruta)
        return True

    def listar_json_disponibles(self) -> List[str]:
        if not self.config_dir.exists():
            return []
        return sorted([
            p.stem for p in self.config_dir.iterdir()
            if p.is_file() and p.suffix == ".json"
        ])

    def aplicar_cambio(self, nombre: str, datos: dict) -> bool:
        ok = self.guardar_json(nombre, datos)
        if ok:
            self._hot_reload(nombre)
            self._notificar(nombre, datos)
        return ok

    def _hot_reload(self, nombre: str) -> None:
        """Invalidar caches globales para que la app recargue config desde disco."""
        stem = Path(nombre).stem
        try:
            from kool_tpv.utils.config_loader import reload_config_cache
            reload_config_cache(stem)
        except Exception:
            pass
        try:
            from kool_tpv.utils.font_loader import reload_font_cache
            if stem == 'font_config':
                reload_font_cache()
        except Exception:
            pass

    def registrar_observer(self, nombre: str, callback: Callable[[dict], None]) -> None:
        nombre = Path(nombre).stem
        if nombre not in self._observers:
            self._observers[nombre] = []
        if callback not in self._observers[nombre]:
            self._observers[nombre].append(callback)

    def eliminar_observer(self, nombre: str, callback: Callable[[dict], None]) -> None:
        nombre = Path(nombre).stem
        if nombre in self._observers:
            self._observers[nombre] = [
                cb for cb in self._observers[nombre] if cb is not callback
            ]

    def _notificar(self, nombre: str, datos: dict) -> None:
        nombre = Path(nombre).stem
        for cb in self._observers.get(nombre, []):
            try:
                cb(datos)
            except Exception:
                pass
