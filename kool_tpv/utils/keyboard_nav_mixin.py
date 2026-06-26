"""
KeyboardNavigableMixin - Navegación por teclado (Tab/Shift+Tab/Enter) para widgets.

Uso:
    class MyView(CTkFrame, KeyboardNavigableMixin):
        def __init__(self, parent):
            CTkFrame.__init__(self, parent)
            KeyboardNavigableMixin.__init__(self)
            
            # Crear botones...
            self._navigable_buttons = [(btn1, cmd1), (btn2, cmd2), ...]
            self._setup_keyboard_navigation()
"""
from pathlib import Path
import json


def _load_keyboard_nav_config():
    """Cargar configuración de navegación por teclado desde layout_config.json."""
    try:
        # Desde utils/ subir a kool_tpv/ y entrar en config/
        config_path = Path(__file__).resolve().parents[1] / "config" / "layout_config.json"
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config.get("global", {}).get("keyboard_navigation", {})
    except Exception:
        return {}


# Configuración cacheada al importar el módulo
_KEYBOARD_NAV_CONFIG = _load_keyboard_nav_config()


class KeyboardNavigableMixin:
    """
    Mixin para añadir navegación por teclado a cualquier widget contenedor.
    
    Requiere que la clase tenga:
        - self._navigable_buttons: lista de tuplas (widget, callback)
        - Acceso a winfo_toplevel() para bindings
    """

    def __init_keyboard_mixin__(self):
        """Inicializar el mixin. LLAMAR explícitamente en __init__ de la clase."""
        self._nav_focused_index = -1
        self._nav_toplevel = None
        self._navigable_buttons = []  # [(widget, callback), ...]

    def _setup_keyboard_navigation(self):
        """Configurar bindings para navegación Tab/Shift+Tab y Enter.
        
        Requiere que self._navigable_buttons esté poblado.
        Usa toplevel para bindings (subvistas únicas visibles).
        """
        if not self._navigable_buttons:
            return

        # Obtener ventana toplevel para bindings
        try:
            self._nav_toplevel = self.winfo_toplevel()
        except Exception:
            self._nav_toplevel = self

        self._bind_nav_events(self._nav_toplevel)

    def _bind_nav_events(self, target):
        """Aplicar bindings de navegación a un target."""
        target.bind("<Tab>", self._on_nav_tab_next)
        target.bind("<Shift-Tab>", self._on_nav_tab_prev)
        target.bind("<Return>", self._on_nav_enter)
        target.bind("<KP_Enter>", self._on_nav_enter)

        # Cleanup al destruir
        self.bind("<Destroy>", self._on_nav_destroy)

    def _on_nav_destroy(self, event=None):
        """Limpiar bindings al destruir."""
        try:
            if self._nav_toplevel:
                self._nav_toplevel.unbind("<Tab>")
                self._nav_toplevel.unbind("<Shift-Tab>")
                self._nav_toplevel.unbind("<Return>")
                self._nav_toplevel.unbind("<KP_Enter>")
        except Exception:
            pass

    def _focus_nav_widget(self, index):
        """Aplicar foco visual a un widget por índice."""
        if not self._navigable_buttons:
            return

        # Validar índice (circular)
        if index < 0:
            index = len(self._navigable_buttons) - 1
        elif index >= len(self._navigable_buttons):
            index = 0

        # Quitar foco del anterior - restaurar borde original
        if 0 <= self._nav_focused_index < len(self._navigable_buttons):
            prev_widget, _ = self._navigable_buttons[self._nav_focused_index]
            self._restore_original_border(prev_widget)

        # Aplicar foco al nuevo
        self._nav_focused_index = index
        widget, _ = self._navigable_buttons[index]
        self._apply_focus_border(widget)

    def _restore_original_border(self, widget):
        """Restaurar el borde original de un widget."""
        try:
            normal_width = _KEYBOARD_NAV_CONFIG.get("normal_border_width", 2)
            original_color = getattr(widget, '_original_border_color', None)
            if original_color:
                widget.configure(border_width=normal_width, border_color=original_color)
            else:
                widget.configure(border_width=normal_width)
        except Exception:
            pass

    def _apply_focus_border(self, widget):
        """Aplicar borde de foco a un widget."""
        try:
            # Guardar color original si no está guardado
            if not hasattr(widget, '_original_border_color'):
                try:
                    widget._original_border_color = widget.cget("border_color") if hasattr(widget, "cget") else None
                except Exception:
                    widget._original_border_color = None

            focus_color = _KEYBOARD_NAV_CONFIG.get("focus_border_color", "#FFD700")
            focus_width = _KEYBOARD_NAV_CONFIG.get("focus_border_width", 3)
            widget.configure(border_width=focus_width, border_color=focus_color)
            widget.focus_set()
        except Exception:
            pass

    def _on_nav_tab_next(self, event):
        """Mover foco al siguiente widget."""
        if self._nav_focused_index < 0:
            self._focus_nav_widget(0)
        else:
            self._focus_nav_widget(self._nav_focused_index + 1)
        return "break"

    def _on_nav_tab_prev(self, event):
        """Mover foco al widget anterior."""
        if self._nav_focused_index < 0:
            self._focus_nav_widget(len(self._navigable_buttons) - 1)
        else:
            self._focus_nav_widget(self._nav_focused_index - 1)
        return "break"

    def _on_nav_enter(self, event):
        """Activar el widget que tiene el foco navegable."""
        # Si el BarcodeService tiene caracteres pendientes, no consumir el Enter
        # (es el terminador del escáner, debe llegar a bind_all)
        barcode_svc = getattr(self._nav_toplevel, '_barcode_service', None) if self._nav_toplevel else None
        if barcode_svc and barcode_svc._buffer:
            return

        if not (0 <= self._nav_focused_index < len(self._navigable_buttons)):
            return # No bloquear el Enter si no hay un botón seleccionado por navegación

        # Verificar que el foco real está dentro del widget navegable activo.
        # CTkButton es un contenedor compuesto: focus_get() devuelve un widget
        # hijo interno (canvas/entry), no el CTkButton en sí. Por eso usamos
        # winfo_containing o comprobamos descendencia en lugar de igualdad directa.
        current_focus = self._nav_toplevel.focus_get() if self._nav_toplevel else None
        if current_focus is None:
            return "break"

        widget, callback = self._navigable_buttons[self._nav_focused_index]

        # Comprobar si current_focus ES el widget o un descendiente suyo
        def _is_descendant(child, ancestor):
            try:
                w = child
                while w is not None:
                    if w == ancestor:
                        return True
                    w = w.master
            except Exception:
                pass
            return False

        if _is_descendant(current_focus, widget) and callable(callback):
            callback()
            return "break" # Solo bloquear si realmente hemos ejecutado una acción
        return # Dejar pasar el evento si no es para nosotros

    def clear_keyboard_navigation(self):
        """Limpiar estado de navegación. Útil al destruir o reconstruir widgets."""
        self._on_nav_destroy()
        self._nav_focused_index = -1
        self._navigable_buttons = []
