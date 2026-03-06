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
    btn_kwargs = {
        "master": parent,
        "text": btn_cfg.get("text", ""),
        "fg_color": btn_cfg.get("color", "#FF0000"),
        "hover_color": btn_cfg.get("hover_color", "#00A4DF"),
        "width": int(btn_cfg.get("width", 110)),
        "height": int(btn_cfg.get("height", 110)),
        "corner_radius": int(btn_cfg.get("corner_radius", 18)),
        "command": command,
        "text_color": "white"
    }
    
    # Crear botón
    button = ctk.CTkButton(**btn_kwargs)
    
    # Cargar imagen desde kool_tpv/assets/
    try:
        base_assets = kool_base / "assets"
        img_path = btn_cfg.get("image", "power.png")
        # Si img_path contiene "assets/", quitarlo (limpieza)
        img_name = img_path.replace("assets/", "") if isinstance(img_path, str) else img_path
        full_img_path = base_assets / img_name

        if full_img_path.exists():
            img = Image.open(full_img_path).convert("RGBA")
            size = (btn_kwargs["width"] - 16, btn_kwargs["height"] - 16)
            ctk_img = ctk.CTkImage(img, size=size)
            button.configure(image=ctk_img, text="")
        else:
            logging.error(f"CRÍTICO: Imagen no encontrada: {full_img_path}")
    except Exception as e:
        logging.error(f"CRÍTICO: Error cargando imagen: {e}")
    
    # No colocar aquí: dejar que el llamador decida (pack/place)
    return button
