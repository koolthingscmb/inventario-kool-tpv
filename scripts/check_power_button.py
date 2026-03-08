import sys
sys.path.insert(0, '/Volumes/ALMACEN/KOOL_THINGS/KOOL_TPV_V2')
print('Test: Verificando comando del botón power…')
try:
    import customtkinter as ctk
    ctk.set_appearance_mode('dark')
    root = ctk.CTk()
    root.withdraw()
except Exception as e:
    print('Error creando root CTk:', e)

try:
    from kool_tpv.modulos.almacen.almacen_view import AlmacenView
    av = AlmacenView(root, db=None)
except Exception as e:
    print('Error instanciando AlmacenView:', e)
    raise

if hasattr(av, 'power_button') and av.power_button:
    try:
        cmd = av.power_button.cget('command')
        print('Comando actual:', repr(cmd))
        try:
            name = getattr(cmd, '__name__', None)
        except Exception:
            name = None
        print('Nombre atributo __name__ del comando:', name)
        print('¿Es _on_power por referencia?:', cmd == av._on_power)
        print('Método _on_power real:', av._on_power)
    except Exception as e:
        print('Error inspeccionando command:', e)
else:
    print('ERROR: No hay power_button')

# cleanup
try:
    root.destroy()
except Exception:
    pass
