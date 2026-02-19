"""Compat layer for Actions/Stock package.

Export main public symbols to preserve old import paths after moving/renaming files.
"""
from .stock_ui import StockUI
from .StockBase import StockBaseUI

__all__ = ["StockUI", "StockBaseUI"]
