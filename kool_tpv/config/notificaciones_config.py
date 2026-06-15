"""Configuración global para widgets de notificación (Toast, Banner, etc.)."""

DEFAULT_CONFIG = {
    # ── Toast ───────────────────────────────────────────────────────────────
    'toast_posicion': 'bottom-right',      # bottom-right | bottom-left | top-right | top-left
    'toast_duracion_ms': 3000,             # 3 segundos por defecto
    'toast_ancho': 320,
    'toast_padding_x': 16,
    'toast_padding_y': 12,
    'toast_corner_radius': 8,
    'toast_offset_x': 16,                  # margen desde borde horizontal
    'toast_offset_y': 16,                  # margen desde borde vertical

    # Colores toast (fondo oscuro con texto claro)
    'toast_success_bg': '#2D7D46',
    'toast_info_bg': '#1F6AA5',
    'toast_warning_bg': '#B8870B',
    'toast_error_bg': '#C0392B',
    'toast_text_color': '#FFFFFF',

    # Animación
    'toast_animar_aparicion': True,
    'toast_animar_desaparicion': True,
    'toast_fade_step_ms': 20,
    'toast_max_opacity': 0.95,
}


def load_notificaciones_config() -> dict:
    """Carga configuración de notificaciones. Por ahora valores por defecto.
    Futuro: leer de archivo JSON o de ConfiguracionRepository."""
    return dict(DEFAULT_CONFIG)
