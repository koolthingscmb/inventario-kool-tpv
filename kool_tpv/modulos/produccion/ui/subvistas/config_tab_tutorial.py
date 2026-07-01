"""Tab TUTORIAL: guía paso a paso del taller de producción."""
import tkinter as tk
import customtkinter as ctk
from kool_tpv.modulos.produccion.ui.subvistas.config_helper import get_font


class ConfigTabTutorial:
    def __init__(self, parent, config, colors, km, layout_config):
        self.parent = parent
        self.config = config
        self._bg = colors.get("background", "#2c3e50")
        self.build()

    def build(self):
        c = tk.Frame(self.parent, bg=self._bg)
        c.pack(fill=tk.BOTH, expand=True)
        s = ctk.CTkScrollableFrame(c, fg_color=self._bg)
        s.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        tf = get_font(self.config, "title")
        bf = get_font(self.config, "entry")
        sf = (bf[0], bf[1] - 1, "normal")

        def _t(txt):
            tk.Label(s, text=txt, font=tf, fg="#FFD700", bg=self._bg, justify="left", anchor="w", wraplength=900).pack(fill="x", pady=(20, 6))
        def _b(txt):
            tk.Label(s, text=txt, font=bf, fg="#ecf0f1", bg=self._bg, justify="left", anchor="w", wraplength=900).pack(fill="x", pady=(0, 4))
        def _ul(txt):
            tk.Label(s, text=f"  - {txt}", font=sf, fg="#bdc3c7", bg=self._bg, justify="left", anchor="w", wraplength=880).pack(fill="x", padx=(16, 0), pady=(0, 2))
        def _w(txt):
            tk.Label(s, text=f"ATENCIÓN: {txt}", font=bf, fg="#e67e22", bg=self._bg, justify="left", anchor="w", wraplength=900).pack(fill="x", pady=(4, 4))
        def _ok(txt):
            tk.Label(s, text=f"OK: {txt}", font=bf, fg="#2ecc71", bg=self._bg, justify="left", anchor="w", wraplength=900).pack(fill="x", pady=(4, 4))
        def _sep():
            tk.Frame(s, height=1, bg="#34495e").pack(fill="x", pady=12)

        _t("TALLER DE PRODUCCIÓN — GUÍA COMPLETA")
        _b("Sigue los pasos en orden. Cada pestaña del taller corresponde a un paso.")
        _sep()

        _t("PASO 1 — CATÁLOGO (Colores y Tallas)")
        _b("Define los colores y tallas globales que usarás en producción.")
        _ul("COLORES: nombre y código HEX (ej: #000000).")
        _ul("TALLAS: nombre de la talla (ej: S, M, L, Única).")
        _w("Colores y tallas son globales: se comparten entre todos los tipos.")
        _sep()

        _t("PASO 2 — MATRIZ (Tipo → Color → Talla)")
        _b("Define qué combinaciones de color y talla existen para cada tipo y variante.")
        _ul("Selecciona un TIPO y luego una VARIANTE para ver su stock.")
        _ul("La matriz se rellena SOLA al importar un albarán de proveedor.")
        _w("Si un tipo no tiene marcados 'Requiere Talla' o 'Requiere Color' en su ficha de ALMACÉN, no aparecerá aquí.")
        _sep()

        _t("PASO 3 — MENÚ (Agrupación y Orden)")
        _b("Configura cómo se ven los botones en el flujo de producción.")
        _ul("Crea los MENÚS (carpetas) y dales el nombre que verás en los chips del taller.")
        _ul("Asocia los Tipos del sistema con cada menú y elige en qué orden aparecen.")
        _ul("Recuerda: solo puedes asociar tipos que ya existan en el sistema.")
        _sep()

        _t("PASO 4 — VARIANTES (Modelos)")
        _b("Crea y asigna los modelos o variantes específicas a cada tipo producible.")
        _ul("Ejemplo: Tipo 'Camiseta' -> 'Camiseta Hombre', 'Camiseta Mujer', 'Oversized'.")
        _ul("Asigna costes base y métodos de producción específicos por modelo.")
        _sep()

        _t("PASO 5 — EXTRAS (Costes Adicionales)")
        _b("Añade suplementos de coste a la producción por características especiales.")
        _ul("Ejemplo: Suplemento de +2€ para tallas grandes como 3XL, 4XL o 5XL.")
        _sep()

        _t("PASO 6 — PRODUCTOS TPV (Vinculación)")
        _b("Une tu producción con el stock real de la tienda.")
        _ul("1. Selecciona TIPO y VARIANTE a la izquierda.")
        _ul("2. Busca el producto del TPV a la derecha y haz DOBLE CLIC.")
        _ok("Al terminar una orden de producción, el stock del TPV subirá automáticamente.")
