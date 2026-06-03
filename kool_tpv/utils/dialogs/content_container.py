"""
Helper para construir contenedores de contenido con alineación configurable.
"""
import customtkinter as ctk


def create_dialog_content_container(main_frame, geometry_cfg):
    """Construye el contenedor de contenido según alineación configurada.

    Soporta:
    - content_align_x: left|center
    - content_align_y: top|center
    """
    try:
        align_x = str(geometry_cfg.get('content_align_x', 'left')).lower()
        align_y = str(geometry_cfg.get('content_align_y', 'top')).lower()
    except Exception:
        align_x = 'left'
        align_y = 'top'

    use_centering = (align_x == 'center') or (align_y == 'center')
    if not use_centering:
        return main_frame

    anchor_frame = ctk.CTkFrame(main_frame, fg_color='transparent')
    anchor_frame.pack(fill='both', expand=True)

    # Grid 3x3 para poder centrar en eje X/Y sin posicionamiento absoluto.
    anchor_frame.grid_rowconfigure(0, weight=1)
    anchor_frame.grid_rowconfigure(1, weight=0)
    anchor_frame.grid_rowconfigure(2, weight=1)
    anchor_frame.grid_columnconfigure(0, weight=1)
    anchor_frame.grid_columnconfigure(1, weight=0)
    anchor_frame.grid_columnconfigure(2, weight=1)

    row = 1 if align_y == 'center' else 0
    col = 1 if align_x == 'center' else 0

    content_frame = ctk.CTkFrame(anchor_frame, fg_color='transparent')
    content_frame.grid(row=row, column=col)
    return content_frame
