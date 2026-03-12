import importlib, sys, traceback

try:
    m = importlib.import_module('kool_tpv.modulos.tpv.ui.stock_ui')
    print('IMPORT_OK', getattr(m, 'StockUI', None))
except Exception:
    traceback.print_exc()
    sys.exit(1)
