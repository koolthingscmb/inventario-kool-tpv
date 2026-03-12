import sys
from pathlib import Path
import tkinter as tk

# Ensure workspace root is on sys.path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

print('Starting unsaved check test')
root = tk.Tk()
root.withdraw()
from kool_tpv.utils.templates.base_module_view import BaseModuleView
import kool_tpv.utils.custom_dialog as custom_dialog

def mock_warning(parent, title, msg, confirm=False):
    print('MOCK_SHOW_WARNING_CALLED', title, msg, 'confirm=', confirm)
    return False

custom_dialog.show_warning = mock_warning

view = BaseModuleView(root, config_section='almacen')

# Create a mock widget child with has_unsaved_changes True
mock = tk.Frame(view.central_area)

def has_unsaved_changes():
    print('mock.has_unsaved_changes called')
    return True

mock.has_unsaved_changes = has_unsaved_changes
mock.pack()

print('children before check:', [type(c).__name__ for c in view.central_area.winfo_children()])
res = view._check_unsaved_changes()
print('check result:', res)

# Try to change central content
new = tk.Frame(view.central_area)
view.set_central_content(new)
print('children after set_central_content (name, manager):', [(type(c).__name__, c.winfo_manager()) for c in view.central_area.winfo_children()])

root.destroy()
print('done')
