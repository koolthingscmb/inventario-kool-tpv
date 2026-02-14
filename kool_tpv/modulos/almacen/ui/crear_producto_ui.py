"""CrearProductoUI: Interfaz estilo "Terminal Pro" para altas de producto.

Cumple la especificación visual: fondo #1a1a1a, tipografías monoespaciadas,
texto verde neón y organización en pestañas para evitar scroll.
"""
from typing import Dict
import logging

import customtkinter as ctk


class CrearProductoUI:
    def __init__(self, parent):
        self.parent = parent
        self.container = ctk.CTkFrame(self.parent, fg_color="#1a1a1a")

        # Cabecera estilo terminal
        self.lbl_titulo = ctk.CTkLabel(
            self.container,
            text="> NUEVO_PRODUCTO_SISTEMA",
            font=("Courier New", 22, "bold"),
            text_color="#00FF00",
        )
        self.lbl_titulo.pack(anchor="w", padx=16, pady=(16, 8))

        # Tabview con estilo oscuro/terminal
        self.tabview = ctk.CTkTabview(
            self.container,
            width=900,
            height=420,
            segmented_button_fg_color="#2b2b2b",
            segmented_button_selected_color="#00FF00",
            segmented_button_selected_hover_color="#00FF00",
            text_color="#00FF00",
        )
        self.tabview.pack(fill="both", expand=False, padx=16, pady=(6, 12))

        # Añadir pestañas
        self.tab_general = self.tabview.add("[01] GENERAL")
        self.tab_precios = self.tabview.add("[02] PRECIOS/IVA")
        self.tab_stock = self.tabview.add("[03] STOCK/WEB")

        # Estilo común para labels/entries
        lbl_font = ("Courier New", 14)
        entry_kwargs = {
            "fg_color": "#000000",
            "text_color": "#00FF00",
            "border_width": 2,
            "border_color": "#00FF00",
            "corner_radius": 4,
        }

        # --- TAB GENERAL ---
        try:
            # Nombre
            l_nombre = ctk.CTkLabel(self.tab_general, text="Nombre:", text_color="#00FF00", font=lbl_font)
            l_nombre.grid(row=0, column=0, sticky="w", padx=8, pady=(12, 6))
            self.e_nombre = ctk.CTkEntry(self.tab_general, placeholder_text="Nombre del producto", **entry_kwargs)
            self.e_nombre.grid(row=0, column=1, sticky="ew", padx=8, pady=(12, 6))

            # Nombre botón (alias/button label)
            l_nombre_btn = ctk.CTkLabel(self.tab_general, text="Nombre Botón:", text_color="#00FF00", font=lbl_font)
            l_nombre_btn.grid(row=1, column=0, sticky="w", padx=8, pady=6)
            self.e_nombre_btn = ctk.CTkEntry(self.tab_general, placeholder_text="Texto del botón", **entry_kwargs)
            self.e_nombre_btn.grid(row=1, column=1, sticky="ew", padx=8, pady=6)

            # SKU
            l_sku = ctk.CTkLabel(self.tab_general, text="SKU:", text_color="#00FF00", font=lbl_font)
            l_sku.grid(row=2, column=0, sticky="w", padx=8, pady=6)
            self.e_sku = ctk.CTkEntry(self.tab_general, placeholder_text="SKU", **entry_kwargs)
            self.e_sku.grid(row=2, column=1, sticky="ew", padx=8, pady=6)

            # Categoría
            l_cat = ctk.CTkLabel(self.tab_general, text="Categoría:", text_color="#00FF00", font=lbl_font)
            l_cat.grid(row=3, column=0, sticky="w", padx=8, pady=6)
            self.e_categoria = ctk.CTkEntry(self.tab_general, placeholder_text="Categoría", **entry_kwargs)
            self.e_categoria.grid(row=3, column=1, sticky="ew", padx=8, pady=6)

            # Tipo
            l_tipo = ctk.CTkLabel(self.tab_general, text="Tipo:", text_color="#00FF00", font=lbl_font)
            l_tipo.grid(row=4, column=0, sticky="w", padx=8, pady=6)
            self.e_tipo = ctk.CTkEntry(self.tab_general, placeholder_text="Tipo", **entry_kwargs)
            self.e_tipo.grid(row=4, column=1, sticky="ew", padx=8, pady=6)

            # Proveedor
            l_prov = ctk.CTkLabel(self.tab_general, text="Proveedor:", text_color="#00FF00", font=lbl_font)
            l_prov.grid(row=5, column=0, sticky="w", padx=8, pady=6)
            self.e_proveedor = ctk.CTkEntry(self.tab_general, placeholder_text="Proveedor", **entry_kwargs)
            self.e_proveedor.grid(row=5, column=1, sticky="ew", padx=8, pady=6)

            self.tab_general.grid_columnconfigure(1, weight=1)
        except Exception:
            logging.exception("Error creando campos en TAB GENERAL CrearProductoUI")

        # --- TAB PRECIOS/IVA ---
        try:
            l_pvp = ctk.CTkLabel(self.tab_precios, text="PVP:", text_color="#00FF00", font=lbl_font)
            l_pvp.grid(row=0, column=0, sticky="w", padx=8, pady=(12, 6))
            self.e_pvp = ctk.CTkEntry(self.tab_precios, placeholder_text="0.00", **entry_kwargs)
            self.e_pvp.grid(row=0, column=1, sticky="ew", padx=8, pady=(12, 6))

            l_coste = ctk.CTkLabel(self.tab_precios, text="Coste:", text_color="#00FF00", font=lbl_font)
            l_coste.grid(row=1, column=0, sticky="w", padx=8, pady=6)
            self.e_coste = ctk.CTkEntry(self.tab_precios, placeholder_text="0.00", **entry_kwargs)
            self.e_coste.grid(row=1, column=1, sticky="ew", padx=8, pady=6)

            l_iva = ctk.CTkLabel(self.tab_precios, text="Tipo IVA:", text_color="#00FF00", font=lbl_font)
            l_iva.grid(row=2, column=0, sticky="w", padx=8, pady=6)
            self.e_iva = ctk.CTkEntry(self.tab_precios, placeholder_text="21%", **entry_kwargs)
            self.e_iva.grid(row=2, column=1, sticky="ew", padx=8, pady=6)

            l_pvp_var = ctk.CTkLabel(self.tab_precios, text="PVP Variable:", text_color="#00FF00", font=lbl_font)
            l_pvp_var.grid(row=3, column=0, sticky="w", padx=8, pady=6)
            self.e_pvp_var = ctk.CTkEntry(self.tab_precios, placeholder_text="Sí/No", **entry_kwargs)
            self.e_pvp_var.grid(row=3, column=1, sticky="ew", padx=8, pady=6)

            self.tab_precios.grid_columnconfigure(1, weight=1)
        except Exception:
            logging.exception("Error creando campos en TAB PRECIOS CrearProductoUI")

        # --- TAB STOCK/WEB ---
        try:
            l_stock = ctk.CTkLabel(self.tab_stock, text="Stock Actual:", text_color="#00FF00", font=lbl_font)
            l_stock.grid(row=0, column=0, sticky="w", padx=8, pady=(12, 6))
            self.e_stock = ctk.CTkEntry(self.tab_stock, placeholder_text="0", **entry_kwargs)
            self.e_stock.grid(row=0, column=1, sticky="ew", padx=8, pady=(12, 6))

            l_stock_min = ctk.CTkLabel(self.tab_stock, text="Stock Mínimo:", text_color="#00FF00", font=lbl_font)
            l_stock_min.grid(row=1, column=0, sticky="w", padx=8, pady=6)
            self.e_stock_min = ctk.CTkEntry(self.tab_stock, placeholder_text="0", **entry_kwargs)
            self.e_stock_min.grid(row=1, column=1, sticky="ew", padx=8, pady=6)

            l_seo = ctk.CTkLabel(self.tab_stock, text="Título SEO:", text_color="#00FF00", font=lbl_font)
            l_seo.grid(row=2, column=0, sticky="w", padx=8, pady=6)
            self.e_seo = ctk.CTkEntry(self.tab_stock, placeholder_text="Título para SEO", **entry_kwargs)
            self.e_seo.grid(row=2, column=1, sticky="ew", padx=8, pady=6)

            l_tags = ctk.CTkLabel(self.tab_stock, text="Etiquetas:", text_color="#00FF00", font=lbl_font)
            l_tags.grid(row=3, column=0, sticky="w", padx=8, pady=6)
            self.e_tags = ctk.CTkEntry(self.tab_stock, placeholder_text="tag1, tag2", **entry_kwargs)
            self.e_tags.grid(row=3, column=1, sticky="ew", padx=8, pady=6)

            self.tab_stock.grid_columnconfigure(1, weight=1)
        except Exception:
            logging.exception("Error creando campos en TAB STOCK CrearProductoUI")

        # Botonera inferior
        try:
            self.btn_frame = ctk.CTkFrame(self.container, fg_color="transparent")
            self.btn_frame.pack(side="bottom", fill="x", padx=16, pady=12)

            self.btn_cancel = ctk.CTkButton(
                self.btn_frame,
                text="CANCELAR",
                fg_color="#e74c3c",
                text_color="white",
                command=self._on_cancel,
            )
            self.btn_cancel.pack(side="right", padx=8)

            self.btn_save = ctk.CTkButton(
                self.btn_frame,
                text="EJECUTAR_GUARDADO",
                fg_color="#2ecc71",
                text_color="black",
                command=self._on_save,
            )
            self.btn_save.pack(side="right", padx=8)
        except Exception:
            logging.exception("Error creando botonera CrearProductoUI")

    def get_widget(self):
        return self.container

    def _on_save(self):
        try:
            data = self.get_data()
            logging.info("Guardar producto (UI): %s", data)
        except Exception:
            logging.exception("Error en _on_save CrearProductoUI")

    def _on_cancel(self):
        try:
            # limpiar campos
            for e in [
                getattr(self, 'e_nombre', None),
                getattr(self, 'e_nombre_btn', None),
                getattr(self, 'e_sku', None),
                getattr(self, 'e_categoria', None),
                getattr(self, 'e_tipo', None),
                getattr(self, 'e_proveedor', None),
                getattr(self, 'e_pvp', None),
                getattr(self, 'e_coste', None),
                getattr(self, 'e_iva', None),
                getattr(self, 'e_pvp_var', None),
                getattr(self, 'e_stock', None),
                getattr(self, 'e_stock_min', None),
                getattr(self, 'e_seo', None),
                getattr(self, 'e_tags', None),
            ]:
                try:
                    if e is not None:
                        e.delete(0, 'end')
                except Exception:
                    pass
        except Exception:
            logging.exception("Error en _on_cancel CrearProductoUI")

    def get_data(self) -> Dict[str, str]:
        try:
            return {
                'nombre': (self.e_nombre.get() or '').strip(),
                'nombre_boton': (self.e_nombre_btn.get() or '').strip(),
                'sku': (self.e_sku.get() or '').strip(),
                'categoria': (self.e_categoria.get() or '').strip(),
                'tipo': (self.e_tipo.get() or '').strip(),
                'proveedor': (self.e_proveedor.get() or '').strip(),
                'pvp': (self.e_pvp.get() or '').strip(),
                'coste': (self.e_coste.get() or '').strip(),
                'iva': (self.e_iva.get() or '').strip(),
                'pvp_variable': (self.e_pvp_var.get() or '').strip(),
                'stock': (self.e_stock.get() or '').strip(),
                'stock_min': (self.e_stock_min.get() or '').strip(),
                'seo': (self.e_seo.get() or '').strip(),
                'tags': (self.e_tags.get() or '').strip(),
            }
        except Exception:
            logging.exception("Error obteniendo datos CrearProductoUI")
            return {}

