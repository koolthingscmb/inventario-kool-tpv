"""Helpers compartidos para las tabs de configuración UI."""
import tkinter as tk
from tkinter import colorchooser
from typing import Any, Callable, Optional, Tuple

import customtkinter as ctk


BASE_CONFIG_DIR = "/Volumes/ALMACEN/KOOL_THINGS/KOOL_TPV_V2/kool_tpv/config"


def get_font_config(config: dict, key: str = "default") -> Tuple[str, int, str]:
    """Devuelve una tupla (familia, tamaño, peso) para tkinter fonts."""
    font_cfg = config.get("font_config", {})
    token = font_cfg.get(key, {})
    if not token:
        token = font_cfg.get("default", {})
    family = token.get("family", "Helvetica")
    size = token.get("size", 14)
    weight = token.get("weight", "normal")
    return (family, size, weight)


def get_color_config(config: dict, key: str, fallback: str = "#000000") -> str:
    """Busca un color en colors_config o design_tokens."""
    for source in ("colors_config", "design_tokens"):
        src = config.get(source, {})
        if isinstance(src, dict):
            value = src.get(key)
            if value is not None:
                return value
    return fallback


def section_title(parent, text: str, bg: str = "#2c3e50", fg: str = "#ecf0f1") -> tk.Label:
    """Crea un título de sección con separación vertical."""
    return tk.Label(
        parent, text=text,
        font=("Helvetica", 14, "bold"),
        fg=fg, bg=bg, justify="left", anchor="w"
    )


def preview_box(parent, width: int = 200, height: int = 60,
                bg: str = "#ffffff", text: str = "Vista previa") -> tk.Label:
    """Crea un cuadro de previsualización con borde."""
    box = tk.Label(
        parent, text=text, width=width, height=height,
        bg=bg, fg="#000000", font=("Helvetica", 12, "bold"),
        relief="solid", bd=1
    )
    return box


def input_color(parent, label: str, value: str = "#ffffff",
                on_change: Optional[Callable[[str], None]] = None,
                bg: str = "#2c3e50", fg: str = "#ecf0f1") -> tk.Frame:
    """Crea un selector de color con label y botón de color picker."""
    container = tk.Frame(parent, bg=bg)

    tk.Label(container, text=label, font=("Helvetica", 12), fg=fg, bg=bg).pack(side="left", padx=(0, 8))

    preview = tk.Label(container, width=4, height=2, bg=value, relief="solid", bd=1)
    preview.pack(side="left", padx=(0, 8))

    var = tk.StringVar(value=value)

    def _choose():
        color = colorchooser.askcolor(initialcolor=var.get())[1]
        if color:
            var.set(color)
            preview.configure(bg=color)
            if on_change:
                on_change(color)

    ctk.CTkButton(container, text="Elegir", width=70, command=_choose).pack(side="left")
    return container


def input_number(parent, label: str, value: int = 0, min_val: int = 0, max_val: int = 9999,
                 on_change: Optional[Callable[[int], None]] = None,
                 bg: str = "#2c3e50", fg: str = "#ecf0f1") -> tk.Frame:
    """Crea un entry numérico validado junto a un label."""
    container = tk.Frame(parent, bg=bg)
    tk.Label(container, text=label, font=("Helvetica", 12), fg=fg, bg=bg).pack(side="left", padx=(0, 8))

    var = tk.StringVar(value=str(value))
    entry = ctk.CTkEntry(container, textvariable=var, width=80, justify="right")
    entry.pack(side="left")

    def _validate(*_):
        raw = var.get()
        if raw.isdigit():
            num = int(raw)
            if num < min_val:
                num = min_val
            elif num > max_val:
                num = max_val
            if str(num) != raw:
                var.set(str(num))
            if on_change:
                on_change(num)
        else:
            var.set(str(min_val))

    entry.bind("<FocusOut>", _validate)
    entry.bind("<Return>", _validate)
    return container


def input_text(parent, label: str, value: str = "", max_length: int = 0,
               on_change: Optional[Callable[[str], None]] = None,
               bg: str = "#2c3e50", fg: str = "#ecf0f1") -> tk.Frame:
    """Crea un entry de texto con validación opcional de longitud."""
    container = tk.Frame(parent, bg=bg)
    tk.Label(container, text=label, font=("Helvetica", 12), fg=fg, bg=bg).pack(side="left", padx=(0, 8))

    var = tk.StringVar(value=value)
    entry = ctk.CTkEntry(container, textvariable=var, width=160)
    entry.pack(side="left", fill="x", expand=True)

    def _validate(*_):
        text = var.get()
        if max_length and len(text) > max_length:
            text = text[:max_length]
            var.set(text)
        if on_change:
            on_change(text)

    entry.bind("<FocusOut>", _validate)
    entry.bind("<Return>", _validate)
    return container
