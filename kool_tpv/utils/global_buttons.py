import customtkinter as ctk
import json
import os
from pathlib import Path
from PIL import Image
import logging

def create_global_close_button(parent, command=None):
    """
    Crea un botón de cerrar estandarizado usando la configuración de buttons_config.json
    """
    
    # Leer configuración desde JSON (OBLIGATORIO usar global_buttons["power"])
    btn_cfg = None
    try:
        kool_base = Path(__file__).resolve().parents[1]  # kool_tpv/
        cfg_file = kool_base / "config" / "buttons_config.json"
        if cfg_file.exists():
            with cfg_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
            global_buttons = data.get("global_buttons", [])
            for button in global_buttons:
                if str(button.get("id")).lower() == "power":
                    btn_cfg = button
                    break
    except Exception as e:
        logging.error(f"CRÍTICO: Error leyendo buttons_config.json: {e}")
        return None
    
    if not btn_cfg:
        logging.error("CRÍTICO: No se encontró configuración 'power' en global_buttons")
        return None
    
    # Usar EXACTAMENTE la configuración del JSON
    # Resolve numeric sizes (ensure ints)
    try:
        width = int(btn_cfg.get("width", 110))
    except Exception:
        width = 110
    try:
        height = int(btn_cfg.get("height", 110))
    except Exception:
        height = 110

    btn_kwargs = {
        "master": parent,
        "text": btn_cfg.get("text", ""),
        "fg_color": btn_cfg.get("color", "#FF0000"),
        "hover_color": btn_cfg.get("hover_color", "#00A4DF"),
        "width": width,
        "height": height,
        "corner_radius": int(btn_cfg.get("corner_radius", 18)),
        "command": command,
        "text_color": "white"
    }
    
    # Crear un contenedor fijo y poner el botón dentro para garantizar tamaño
    # Use the configured color for the container so the red plate matches the button
    try:
        container_bg = btn_cfg.get('color') or (parent.cget('fg_color') if hasattr(parent, 'cget') else 'transparent')
    except Exception:
        container_bg = (parent.cget('fg_color') if hasattr(parent, 'cget') else 'transparent')
    container = ctk.CTkFrame(parent, width=width, height=height, fg_color=container_bg)
    try:
        container.pack_propagate(False)
    except Exception:
        pass

    button = ctk.CTkButton(master=container, **{k: v for k, v in btn_kwargs.items() if k != 'master'})
    try:
        button.configure(width=width, height=height)
    except Exception:
        pass
    try:
        # Center the button inside the fixed container
        button.pack(expand=True)
    except Exception:
        try:
            button.place(relx=0.5, rely=0.5, anchor='center')
        except Exception:
            pass
    
    # Cargar imagen desde kool_tpv/assets/
    try:
        base_assets = kool_base / "assets"
        img_path = btn_cfg.get("image", "power.png")
        # Si img_path contiene "assets/", quitarlo (limpieza)
        img_name = img_path.replace("assets/", "") if isinstance(img_path, str) else img_path
        full_img_path = base_assets / img_name

        if full_img_path.exists():
            img = Image.open(full_img_path).convert("RGBA")
            try:
                max_w = max(8, int(width) - 16)
                max_h = max(8, int(height) - 16)
            except Exception:
                max_w, max_h = max(8, width - 16), max(8, height - 16)
            try:
                orig_w, orig_h = img.size
                ratio = min(max_w / orig_w, max_h / orig_h, 1.0)
                new_w = max(1, int(orig_w * ratio))
                new_h = max(1, int(orig_h * ratio))
                img_resized = img.resize((new_w, new_h), Image.LANCZOS)
                ctk_img = ctk.CTkImage(img_resized, size=(new_w, new_h))
                try:
                    button.configure(image=ctk_img, text="")
                except Exception:
                    pass
            except Exception:
                try:
                    # Fallback to previous behavior
                    size = (max(8, width - 16), max(8, height - 16))
                    ctk_img = ctk.CTkImage(img, size=size)
                    button.configure(image=ctk_img, text="")
                except Exception:
                    logging.exception(f"Error ajustando la imagen para power button")
        else:
            logging.error(f"CRÍTICO: Imagen no encontrada: {full_img_path}")
    except Exception as e:
        logging.error(f"CRÍTICO: Error cargando imagen: {e}")
    
    # Devolver un proxy ligero que mantiene compatibilidad con la API usada
    class _ButtonProxy:
        def __init__(self, frame, btn):
            self._frame = frame
            self._btn = btn

        # layout
        def pack(self, *a, **k):
            return self._frame.pack(*a, **k)

        def pack_forget(self):
            try:
                return self._frame.pack_forget()
            except Exception:
                pass

        def place(self, *a, **k):
            return self._frame.place(*a, **k)

        def place_forget(self):
            try:
                return self._frame.place_forget()
            except Exception:
                pass

        # configure proxy to inner button
        def configure(self, *a, **k):
            return self._btn.configure(*a, **k)

        # other common methods proxied
        def cget(self, key):
            try:
                return self._btn.cget(key)
            except Exception:
                try:
                    return self._frame.cget(key)
                except Exception:
                    return None

        def bind(self, *a, **k):
            try:
                return self._btn.bind(*a, **k)
            except Exception:
                return None

        def winfo_reqwidth(self):
            try:
                return self._frame.winfo_reqwidth()
            except Exception:
                try:
                    return self._btn.winfo_reqwidth()
                except Exception:
                    return width

        def winfo_reqheight(self):
            try:
                return self._frame.winfo_reqheight()
            except Exception:
                try:
                    return self._btn.winfo_reqheight()
                except Exception:
                    return height

        # expose inner button if needed
        @property
        def inner(self):
            return self._btn

    return _ButtonProxy(container, button)
