"""Clase base para overlays de Cierres.

Provee un contenedor limpio que hereda de
`SelectionOverlayTemplate` para que UIs concretas (CierreUI,
Histórico) puedan reutilizar el layout sin duplicar el constructor.
No contiene lógica ni botones adicionales — sólo delega al template.
"""
from kool_tpv.utils.templates.template_selection_overlay import SelectionOverlayTemplate


class CierreBaseUI(SelectionOverlayTemplate):
    """Clase base para centralizar el layout de Cierres e Históricos.

    Esta clase es intencionalmente mínima: actúa como pasarela hacia
    `SelectionOverlayTemplate` y no añade controles ni comportamiento.
    """

    def __init__(self, view_or_action_panel, db=None, on_selection_callback=None, ui_config: dict = None):
        super().__init__(view_or_action_panel, db=db, on_selection_callback=on_selection_callback, ui_config=ui_config)
