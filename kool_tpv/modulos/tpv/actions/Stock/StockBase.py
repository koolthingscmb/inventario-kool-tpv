"""StockBaseUI: clase base ligera para las UIs de stock.

Provee un punto de extensión donde centralizar comportamiento común
en el futuro sin forzar cambios inmediatos en `stock_ui.py`.

Diseño: hereda de `SelectionOverlayTemplate` y expone el mismo
constructor para que las subclases actuales (StockUI) sigan funcionando
sin modificar su lógica interna.
"""
from kool_tpv.utils.templates.template_selection_overlay import SelectionOverlayTemplate


class StockBaseUI(SelectionOverlayTemplate):
	"""Clase base ligera para overlays de stock.

	Actualmente actúa como pasarela que reproduce la API de
	`SelectionOverlayTemplate`. Más funcionalidad común (paginación,
	helpers de render, etc.) se puede extraer aquí posteriormente.
	"""

	def __init__(self, view_or_action_panel, db=None, on_selection_callback=None, ui_config: dict = None):
		# Simplemente delegar al constructor de la plantilla
		super().__init__(view_or_action_panel, db=db, on_selection_callback=on_selection_callback, ui_config=ui_config)
