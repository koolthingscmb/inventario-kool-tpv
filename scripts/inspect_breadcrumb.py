import traceback, sys
from pathlib import Path
# Ensure project root is on sys.path so `kool_tpv` package is importable
proj_root = Path(__file__).resolve().parents[1]
if str(proj_root) not in sys.path:
    sys.path.insert(0, str(proj_root))
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

class MockAuth:
    def validate_admin_password(self, pw):
        return True


def main():
    out = []
    try:
        root = ctk.CTk()
        root.withdraw()
        cv = ConfigView(root, MockDB())

        out.append('INITIAL_BREADCRUMB_CALLBACKS')
        for k, v in (getattr(cv, 'breadcrumb_callbacks', {}) or {}).items():
            out.append(f"{k}: {repr(v)} callable={callable(v)}")

        # Simulate successful auth and open Reset without interactive dialog
        cv.auth_service = MockAuth()
        try:
            cv.show_reset()
        except Exception:
            out.append('show_reset RAISED:')
            out.append(traceback.format_exc())

        out.append('AFTER_SHOW_RESET_BREADCRUMB_CALLBACKS')
        for k, v in (getattr(cv, 'breadcrumb_callbacks', {}) or {}).items():
            out.append(f"{k}: {repr(v)} callable={callable(v)}")

        out.append('BREADCRUMB_PARTS')
        br = getattr(cv, 'breadcrumb', None)
        if br is None:
            out.append('breadcrumb missing')
        else:
            for part in getattr(br, 'parts', []):
                out.append(repr(part))

        try:
            root.destroy()
        except Exception:
            pass
    except Exception:
        out.append('EXCEPTION')
        out.append(traceback.format_exc())

    out_path = Path(__file__).resolve().parents[0] / 'inspect_breadcrumb_out.txt'
    out_path.write_text('\n'.join(out), encoding='utf-8')
    print('WROTE', out_path)

if __name__ == '__main__':
    main()
