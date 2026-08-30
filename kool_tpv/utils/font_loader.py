"""Font loader utility.

Reads `kool_tpv/config/font_config.json` and provides helpers to
construct font tuples compatible with CustomTkinter widgets.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from kool_tpv.paths import get_resource_path


_FONT_CONFIG: Optional[Dict[str, Any]] = None


def reload_font_cache() -> None:
    """Invalidar cache de font_config para forzar recarga desde disco."""
    global _FONT_CONFIG
    _FONT_CONFIG = None


def _get_config_path() -> Path:
    return get_resource_path("kool_tpv", "config", "font_config.json")


def load_font_config() -> Dict[str, Any]:
    """Load and cache font_config.json.

    Returns default dict on error.
    """
    global _FONT_CONFIG
    if _FONT_CONFIG is not None:
        return _FONT_CONFIG

    p = _get_config_path()
    try:
        if p.exists():
            with p.open('r', encoding='utf-8') as fh:
                _FONT_CONFIG = json.load(fh)
                return _FONT_CONFIG
        else:
            logging.warning('font_config.json not found at %s', p)
    except Exception:
        logging.exception('Error loading font_config.json')

    # defaults
    _FONT_CONFIG = {
        'default': {'family': 'Courier New', 'size': 16, 'weight': 'normal', 'fallback': []},
        'label': {'size': 14},
        'entry': {'size': 18},
        'title': {'size': 22, 'weight': 'bold'},
        'breadcrumb': {'size': 20, 'weight': 'bold'},
        'scale': {'global_factor': 1.0}
    }
    return _FONT_CONFIG


def _merge_category(module: Optional[str], category: str) -> Dict[str, Any]:
    cfg = load_font_config()
    base = dict(cfg.get('default', {}))
    cat = cfg.get(category, {}) or {}
    base.update(cat)
    if module:
        mods = cfg.get('modules', {}) or {}
        mod_cfg = mods.get(module, {}) or {}
        cat_mod = mod_cfg.get(category, {}) or {}
        base.update(cat_mod)
    return base


def get_font(category: str = 'default', module: Optional[str] = None, size: Optional[int] = None, weight: Optional[str] = None, scale: Optional[float] = None) -> Tuple[str, int, str]:
    """Return a font tuple (family, size, weight) for CTk widgets.

    - `category`: one of keys in font_config (label, entry, title, ...)
    - `module`: optional module-specific overrides (e.g. 'config')
    - `size` / `weight`: optional overrides
    - `scale`: override global scale factor
    """
    merged = _merge_category(module, category)
    family = merged.get('family', 'Courier New')
    cfg_size = merged.get('size', 16)
    cfg_weight = merged.get('weight', 'normal')

    cfg_scale = None
    try:
        cfg = load_font_config()
        cfg_scale = float(cfg.get('scale', {}).get('global_factor', 1.0))
    except Exception:
        cfg_scale = 1.0

    if scale is None:
        scale = cfg_scale or 1.0

    final_size = int((size if size is not None else cfg_size) * float(scale))
    final_weight = weight if weight is not None else cfg_weight

    # CustomTkinter expects a font tuple (family, size, 'bold') or similar
    return (family, final_size, final_weight)


def get_size(category: str = 'default', module: Optional[str] = None, scale: Optional[float] = None) -> int:
    """Convenience to get computed size only."""
    return get_font(category=category, module=module, size=None, weight=None, scale=scale)[1]
