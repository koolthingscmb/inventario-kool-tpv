import sys
sys.path.insert(0, '/Volumes/ALMACEN/KOOL_THINGS/KOOL_TPV_V2')
print('Test (monkeypatch): Verificando comando del botón power…')
# Monkeypatch customtkinter to avoid GUI creation
import customtkinter as real_ctk
class DummyWidget:
    def __init__(self, *a, **k):
        self._props = {}
    def pack(self, *a, **k): pass
    def pack_forget(self): pass
    def destroy(self): pass
    def winfo_toplevel(self): return self
    def winfo_children(self): return []
    def winfo_exists(self): return True
    def cget(self, name):
        return self._props.get(name)
    def configure(self, **kw):
        self._props.update(kw)

class DummyButton(DummyWidget):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        # capture command arg if provided in kwargs
        if 'command' in k:
            self._props['command'] = k['command']

class DummyCTk(DummyWidget):
    pass

# apply monkeypatch
real_ctk.CTkFrame = DummyWidget
real_ctk.CTkLabel = DummyWidget
real_ctk.CTkButton = DummyButton
real_ctk.CTk = DummyCTk
real_ctk.CTkImage = lambda *a, **k: None

# Also monkeypatch PIL Image open used in global_buttons (optional)

# Now import almacen view
try:
    from kool_tpv.modulos.almacen.almacen_view import AlmacenView
    root = real_ctk.CTk()
    av = AlmacenView(root, db=None)
except Exception as e:
    print('Error instanciando AlmacenView:', e)
    raise

if hasattr(av, 'power_button') and av.power_button:
    try:
        cmd = av.power_button.cget('command')
        print('Comando actual:', repr(cmd))
        name = getattr(cmd, '__name__', None)
        print('Nombre atributo __name__ del comando:', name)
        print('¿Es _on_power por referencia?:', cmd == av._on_power)
        print('Método _on_power real:', av._on_power)
    except Exception as e:
        print('Error inspeccionando command:', e)
else:
    print('ERROR: No hay power_button')
