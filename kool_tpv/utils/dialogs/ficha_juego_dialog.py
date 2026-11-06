"""Diálogo FICHA JUEGO: formulario para rellenar un metaobjeto de Shopify.

Los campos llegan de la definición leída en vivo
(`obtener_campos_definicion_metaobjeto`): cada uno se pinta según su tipo —
`boolean` -> casilla; el resto -> entrada de texto. Nada va a fuego: cambiar
la definición en Shopify cambia el formulario solo.

Devuelve `self.result` = {clave: valor} solo con lo rellenado, o None si se
cancela. El servicio es quien traduce eso a la llamada metaobjectCreate.
"""
import logging
import tkinter as tk
from typing import Any, Dict, List, Optional

import customtkinter as ctk

from kool_tpv.utils.dialogs.base_dialog import BaseDialog

logger = logging.getLogger(__name__)


class FichaJuegoDialog(BaseDialog):
    """Formulario dinámico para los campos de un metaobjeto de Shopify."""

    def __init__(self, parent, campos: List[Dict[str, Any]],
                 valores: Optional[Dict[str, Any]] = None):
        """
        Args:
            campos: fieldDefinitions del metaobjeto
                [{'key','name','type':{'name'},'required'}, ...]
            valores: {'clave': valor} ya guardado en el producto (preselección).
        """
        self.campos = campos or []
        self.valores = valores or {}
        self._widgets: Dict[str, tuple] = {}

        super().__init__(parent, tipo='info', titulo='FICHA JUEGO')

        self._crear_contenido_especifico()
        self.geometry("460x" + str(120 + 56 * len(self.campos)))
        self._center_window(parent, 460, 120 + 56 * len(self.campos))

    def _crear_contenido_especifico(self):
        content_frame = self._crear_barra_titulo(self, 'FICHA JUEGO')
        tipo_config = self.dialogs_colors.get(self.tipo, {})
        txt_color = tipo_config.get('text', '#FFFFFF')

        cuerpo = ctk.CTkFrame(content_frame, fg_color='transparent')
        cuerpo.pack(fill='both', expand=True, padx=20, pady=(0, 10))
        cuerpo.columnconfigure(1, weight=1)

        for i, campo in enumerate(self.campos):
            clave = campo.get('key') or ''
            nombre = (campo.get('name') or clave).upper()
            tipo = ((campo.get('type') or {}).get('name') or '')
            valor = self.valores.get(clave)

            ctk.CTkLabel(cuerpo, text=f'{nombre}:', text_color=txt_color,
                         font=('Helvetica', 12)).grid(
                row=i, column=0, sticky='w', padx=(0, 10), pady=7)

            if tipo == 'boolean':
                var = tk.BooleanVar(value=str(valor).lower() == 'true')
                w = ctk.CTkCheckBox(cuerpo, text='', variable=var, width=24)
                self._widgets[clave] = ('bool', var)
            else:
                w = ctk.CTkEntry(cuerpo, font=('Helvetica', 12), width=230)
                w.insert(0, str(valor or ''))
                self._widgets[clave] = ('entry', w)
            w.grid(row=i, column=1, sticky='ew', pady=7)

        self._crear_botones(content_frame, btn_text='ACEPTAR', confirm=True)

    def _on_accept(self):
        """Junta {clave: valor} solo con lo rellenado (bool solo si SÍ)."""
        datos = {}
        for clave, (kind, w) in self._widgets.items():
            if kind == 'bool':
                if w.get():
                    datos[clave] = 'true'
            else:
                val = w.get().strip()
                if val:
                    datos[clave] = val
        self.result = datos
        self.destroy()

    def _on_cancel(self):
        self.result = None
        self.destroy()


def show_ficha_juego_dialog(parent, campos: List[Dict[str, Any]],
                            valores: Optional[Dict[str, Any]] = None
                            ) -> Optional[Dict[str, Any]]:
    """Abre el formulario. Devuelve {clave: valor} o None (cancelado)."""
    dlg = FichaJuegoDialog(parent, campos=campos, valores=valores)
    parent.wait_window(dlg)
    return dlg.result
