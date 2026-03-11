import json, traceback,sys
from pathlib import Path
try:
    import customtkinter as ctk
    from kool_tpv.modulos.configuracion.config_view import ConfigView
except Exception:
    traceback.print_exc()
    sys.exit(2)

class MockDB:
    def fetch_all(self, *a, **k):
        return []
    def fetch_one(self, *a, **k):
        return None


def main():
    try:
        root = ctk.CTk()
        root.withdraw()
        cv = ConfigView(root, MockDB())
        children = list(cv._menu_frame.winfo_children())
        out_lines = []
        out_lines.append(f'MENU_CHILD_COUNT {len(children)}')
        for i,child in enumerate(children,1):
            try:
                text = child.cget('text') if hasattr(child, 'cget') else str(child)
            except Exception:
                text = repr(child)
            try:
                cmd = child.cget('command')
            except Exception:
                cmd = None
            out_lines.append(f"{i} TEXT-> {text} CMD-> {repr(cmd)}")

        # Check buttons_menu.json
        base = Path(__file__).resolve().parents[1]
        cfg_file = base / 'kool_tpv' / 'config' / 'buttons_menu.json'
        if cfg_file.exists():
            cfg = json.loads(cfg_file.read_text(encoding='utf-8'))
            btns = cfg.get('config', {}).get('buttons', [])
            for b in btns:
                action = b.get('action')
                label = b.get('label') or b.get('text')
                has = hasattr(cv, action)
                out_lines.append(f'JSON BUTTON {label} action={action} has_attr={has}')
        else:
            out_lines.append(f'buttons_menu.json not found at {cfg_file}')

        # Write results to file to avoid terminal rendering issues
        out_path = Path(__file__).resolve().parents[1] / 'inspect_bindings_out.txt'
        out_path.write_text('\n'.join(out_lines), encoding='utf-8')
        print('WROTE', out_path)

        try:
            root.destroy()
        except Exception:
            pass
    except Exception:
        traceback.print_exc()
        sys.exit(2)

if __name__ == '__main__':
    main()
