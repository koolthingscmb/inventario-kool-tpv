"""
Base UI for Tickets overlay.

Follow the "Overlay con Modo Dual + Handler" guide.
Placeholder file — no implementation yet.
"""
from kool_tpv.utils.templates.template_selection_overlay import SelectionOverlayTemplate


class TicketsBaseUI(SelectionOverlayTemplate):
	"""Base UI for Tickets overlays.

	Minimal subclass of `SelectionOverlayTemplate` to keep layout
	consistent with other overlays (cierres, stock). No logic here —
	just a placeholder for future implementation.
	"""

	def __init__(self, view_or_action_panel, db=None, on_selection_callback=None, ui_config: dict = None):
		super().__init__(view_or_action_panel, db=db, on_selection_callback=on_selection_callback, ui_config=ui_config)

