"""
ScaleManager - Gestor de escala/densidad de interfaz.

Lee 'ui_density' de la BD y aplica factores de escala a spacing, fonts y tamaños.
Actúa como puente entre la config de BD y los widgets.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ScaleManager:
    """Gestiona factores de escala según la densidad de interfaz configurada."""

    # Factores por modo de densidad
    DENSITY_FACTORS = {
        'normal': {
            'spacing_scale': 1.0,
            'font_scale': 1.0,
            'button_scale': 1.0,
            'width_scale': 1.0,
            'height_scale': 1.0,
        },
        'compact': {
            'spacing_scale': 0.6,
            'font_scale': 0.875,  # fonts ~2 puntos menos en promedio
            'button_scale': 0.75,
            'width_scale': 0.75,
            'height_scale': 0.85,
        },
        'touch': {
            'spacing_scale': 1.3,
            'font_scale': 1.125,  # fonts ~2 puntos más
            'button_scale': 1.2,
            'width_scale': 1.1,
            'height_scale': 1.15,
        }
    }

    def __init__(self, db=None):
        self.db = db
        self._density = 'normal'
        self._factors = self.DENSITY_FACTORS['normal']
        self._load_from_db()

    def _load_from_db(self) -> None:
        """Cargar ui_density desde la base de datos."""
        if not self.db:
            return
        try:
            row = self.db.fetch_one("SELECT valor FROM configuracion WHERE clave = 'ui_density'")
            if row and row[0] and row[0] in self.DENSITY_FACTORS:
                self._density = row[0]
                self._factors = self.DENSITY_FACTORS[self._density]
                logger.info(f"ScaleManager: densidad='{self._density}' cargada desde BD")
            else:
                logger.info("ScaleManager: usando densidad default 'normal'")
        except Exception:
            logger.exception("ScaleManager: error cargando ui_density desde BD")

    @property
    def density(self) -> str:
        return self._density

    def get_spacing(self, base_value: int) -> int:
        """Obtener valor de spacing escalado."""
        return int(base_value * self._factors['spacing_scale'])

    def get_font_size(self, base_size: int) -> int:
        """Obtener tamaño de fuente escalado."""
        return max(8, int(base_size * self._factors['font_scale']))

    def get_button_size(self, base_size: int) -> int:
        """Obtener tamaño de botón escalado."""
        return max(20, int(base_size * self._factors['button_scale']))

    def get_width(self, base_width: int) -> int:
        """Obtener ancho escalado."""
        return max(100, int(base_width * self._factors['width_scale']))

    def get_height(self, base_height: int) -> int:
        """Obtener alto escalado."""
        return max(20, int(base_height * self._factors['height_scale']))

    def scale_dict(self, config_dict: dict, keys_to_scale: list) -> dict:
        """Escalar valores específicos de un diccionario de config."""
        result = config_dict.copy()
        for key in keys_to_scale:
            if key in result and isinstance(result[key], (int, float)):
                if 'width' in key.lower():
                    result[key] = self.get_width(result[key])
                elif 'height' in key.lower() or 'size' in key.lower():
                    result[key] = self.get_height(result[key])
                elif 'spacing' in key.lower() or 'pad' in key.lower():
                    result[key] = self.get_spacing(result[key])
        return result


# Singleton instance para acceso global
_scale_manager_instance: Optional[ScaleManager] = None


def get_scale_manager(db=None) -> ScaleManager:
    """Obtener instancia singleton del ScaleManager."""
    global _scale_manager_instance
    if _scale_manager_instance is None and db is not None:
        _scale_manager_instance = ScaleManager(db)
    return _scale_manager_instance


def reset_scale_manager() -> None:
    """Resetear instancia (útil para tests o recarga)."""
    global _scale_manager_instance
    _scale_manager_instance = None
