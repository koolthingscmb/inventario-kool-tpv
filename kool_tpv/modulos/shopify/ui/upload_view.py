"""Subvista SUBIDA (pantalla única con interruptor NUEVO / EDITAR).

Transitoria: reúne SubidaNuevoView y SubidaEditarView bajo un interruptor de modo hasta que el menú
lateral abra cada una por separado.
"""
import logging
import tkinter as tk

import customtkinter as ctk

from .subida.subida_nuevo_view import SubidaNuevoView
from .subida.subida_editar_view import SubidaEditarView

logger = logging.getLogger(__name__)


class ShopifyUploadView(SubidaEditarView, SubidaNuevoView):
    """Vista de subida/edición de camisetas a Shopify con selector de modo."""

    _modo = "NUEVO"
    TEXTO_BOTON = "SUBIR A SHOPIFY"

    def _vista_modo(self):
        return SubidaEditarView if self._modo == "EDITAR" else SubidaNuevoView

    def _construir_selector_modo(self, scroll):
        modo_frame = tk.Frame(scroll, bg=self._bg)
        modo_frame.pack(fill="x", padx=10, pady=(0, 10))
        self._btn_nuevo = self._modo_btn(modo_frame, "NUEVO PRODUCTO", "NUEVO")
        self._btn_editar = self._modo_btn(modo_frame, "EDITAR EXISTENTE", "EDITAR")

    def _finalizar_build(self):
        self._set_modo("NUEVO")
        self._seleccionar_tipo_por_defecto()

    def _opciones_combo_variante(self, tipo_id):
        return self._vista_modo()._opciones_combo_variante(self, tipo_id)

    def _filtrar_variantes_cajas(self, variantes):
        return self._vista_modo()._filtrar_variantes_cajas(self, variantes)

    def _variante_seleccionada(self) -> str:
        return self._vista_modo()._variante_seleccionada(self)

    def _despachar_subida(self, base):
        return self._vista_modo()._despachar_subida(self, base)

    def _tras_subida_correcta(self):
        return self._vista_modo()._tras_subida_correcta(self)

    def _modo_btn(self, parent, text, modo):
        b = ctk.CTkButton(parent, text=text, width=180, height=36,
                          command=lambda: self._set_modo(modo))
        b.pack(side="left", padx=(0, 8))
        return b

    def _set_modo(self, modo):
        self._modo = modo
        for btn, m in ((self._btn_nuevo, "NUEVO"), (self._btn_editar, "EDITAR")):
            btn.configure(fg_color=self._primary if m == modo else self._secondary,
                          text_color="#000" if m == modo else "#FFF")
        
        # UI del campo variante según modo
        if hasattr(self, '_variante_combo'):
            if modo == "EDITAR":
                self._variante_combo.entry.configure(state="normal")
            else:
                self._variante_combo.entry.configure(state="disabled")

        if modo == "EDITAR":
            self._edit_frame.pack(fill="x", padx=10, pady=5, after=self._content.winfo_children()[1])
            self._btn_upload.configure(text="ACTUALIZAR PRODUCTO")
        else:
            self._edit_frame.pack_forget()
            self._edit_product = None
            self._btn_upload.configure(text="SUBIR A SHOPIFY")
            self._limpiar_formulario()
