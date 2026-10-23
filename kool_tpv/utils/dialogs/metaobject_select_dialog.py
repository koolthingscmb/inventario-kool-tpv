import customtkinter as ctk
import tkinter as tk
from typing import List, Dict, Any, Optional, Union
from .base_dialog import BaseDialog
from kool_tpv.utils.factories.button_factory import ButtonFactory

class ShopifyReferenceSelectDialog(BaseDialog):
    """Diálogo genérico para selección de referencias de Shopify (Metaobjetos, Colecciones, etc).
    
    Muestra los elementos en un grid de 4 columnas.
    """
    
    def __init__(self, parent, titulo: str, opciones: List[Dict[str, Any]],
                 seleccion_actual: Optional[Union[str, List[str]]] = None,
                 multi_select: bool = True,
                 agrupar_por_familia: bool = True,
                 familias_unicas: Optional[set] = None,
                 columnas: int = 4):
        """
        Args:
            opciones: Lista de dicts con {'id': str, 'text': str, 'family': str}
            seleccion_actual: GID o lista de GIDs seleccionados.
            familias_unicas: familias donde solo puede marcarse una opción
                (marcar una desmarca la anterior).
            columnas: nº de columnas del grid (1 = una opción por fila,
                para textos largos).
        """
        self.titulo_ui = titulo
        self.multi_select = multi_select
        self.agrupar = agrupar_por_familia
        self.familias_unicas = familias_unicas or set()
        self.columnas = max(1, columnas)
        self._familia_por_id = {op['id']: op.get('family') for op in opciones}
        self.opciones_originales = opciones
        self.opciones_mostradas = self._ordenar_opciones(opciones)
        
        # Estado de selección
        if multi_select:
            self.seleccionados = set(seleccion_actual or [])
            self.checkboxes = {}
        else:
            if isinstance(seleccion_actual, list) and seleccion_actual:
                self.seleccionado_id = seleccion_actual[0]
            else:
                self.seleccionado_id = seleccion_actual if isinstance(seleccion_actual, str) else None
            self.radio_var = tk.StringVar(value=self.seleccionado_id or "")

        super().__init__(parent, tipo='info', titulo=titulo.upper())
        
        self._crear_contenido_especifico()
        self.geometry("900x750") # Ancho para el grid de 4 columnas
        self._center_window(parent, 900, 750)

    def _ordenar_opciones(self, opciones):
        """Ordena las opciones por familia y luego por texto."""
        return sorted(opciones, key=lambda x: (x.get('family', 'Z_SIN_FAMILIA') or 'Z_SIN_FAMILIA', x.get('text', '').lower()))

    def _crear_contenido_especifico(self):
        content_frame = self._crear_barra_titulo(self, self.title())
        
        tipo_config = self.dialogs_colors.get(self.tipo, {})
        primary_color = tipo_config.get('primary', '#00A4DF')
        
        main_container = ctk.CTkFrame(content_frame, fg_color='transparent')
        main_container.pack(fill='both', expand=True, padx=20, pady=10)

        # Área de scroll con Grid
        self.scroll_frame = ctk.CTkScrollableFrame(
            main_container, fg_color='transparent',
            scrollbar_button_color=primary_color
        )
        self.scroll_frame.pack(fill='both', expand=True, padx=5, pady=5)

        # Configurar las columnas iguales
        for i in range(self.columnas):
            self.scroll_frame.columnconfigure(i, weight=1)

        self._render_lista()

        # Botones
        self._crear_botones(content_frame, btn_text='CONFIRMAR SELECCIÓN', confirm=True)

    def _render_lista(self):
        """Dibuja la lista en un grid de N columnas."""
        for child in self.scroll_frame.winfo_children():
            child.destroy()

        message_font = self._get_font('message')
        primary_color = self.dialogs_colors.get(self.tipo, {}).get('primary', '#00A4DF')

        current_familia = None
        fila_actual = 0
        col_actual = 0

        opciones_a_dibujar = self.opciones_mostradas

        if not opciones_a_dibujar:
            ctk.CTkLabel(self.scroll_frame, text="Sin resultados", font=message_font, text_color="#666").grid(row=0, column=0, columnspan=self.columnas, pady=20)
            return

        for op in opciones_a_dibujar:
            if self.agrupar:
                familia_real = op.get('family') or "OTRAS"
                if familia_real != current_familia:
                    if col_actual > 0:
                        fila_actual += 1
                        col_actual = 0
                    current_familia = familia_real
                    lbl_fam = ctk.CTkLabel(
                        self.scroll_frame, text=f"--- {current_familia.upper()} ---",
                        font=("Helvetica", 10, "bold"), text_color="#666"
                    )
                    lbl_fam.grid(row=fila_actual, column=0, columnspan=self.columnas, pady=(15, 5), sticky="w", padx=10)
                    fila_actual += 1

            i_id = op['id']
            i_text = op['text'].upper()
            
            if self.multi_select:
                var = tk.BooleanVar(value=i_id in self.seleccionados)
                cb = ctk.CTkCheckBox(
                    self.scroll_frame, text=i_text, variable=var,
                    font=message_font, fg_color=primary_color,
                    command=lambda i=i_id, v=var: self._toggle_selection(i, v.get())
                )
                cb.grid(row=fila_actual, column=col_actual, sticky="w", padx=15, pady=4)
                self.checkboxes[i_id] = var
            else:
                rb = ctk.CTkRadioButton(
                    self.scroll_frame, text=i_text, variable=self.radio_var, value=i_id,
                    font=message_font, fg_color=primary_color,
                    command=lambda i=i_id: self._on_radio_select(i)
                )
                rb.grid(row=fila_actual, column=col_actual, sticky="w", padx=15, pady=4)

            col_actual += 1
            if col_actual >= self.columnas:
                col_actual = 0
                fila_actual += 1

        if col_actual > 0: fila_actual += 1
        ctk.CTkLabel(self.scroll_frame, text="", height=1).grid(row=fila_actual, column=0)

    def _toggle_selection(self, item_id: str, is_selected: bool):
        if is_selected:
            familia = self._familia_por_id.get(item_id)
            if familia and familia in self.familias_unicas:
                # selección única dentro del grupo: desmarcar el resto
                for otro_id, var in self.checkboxes.items():
                    if otro_id != item_id and self._familia_por_id.get(otro_id) == familia and var.get():
                        var.set(False)
                        self.seleccionados.discard(otro_id)
            self.seleccionados.add(item_id)
        else:
            self.seleccionados.discard(item_id)

    def _on_radio_select(self, item_id: str):
        self.seleccionado_id = item_id

    def _on_accept(self):
        if self.multi_select: self.result = list(self.seleccionados)
        else: self.result = self.radio_var.get() or None
        self.destroy()

    def _on_cancel(self):
        self.result = None
        self.destroy()

def show_metaobject_select_dialog(parent, tipo_meta: str, opciones: List[Dict[str, Any]], seleccionados_actuales: List[str]) -> Optional[List[str]]:
    """Mantiene compatibilidad con el selector de Mecánicas de juegos de mesa."""
    import json
    opciones_genericas = []
    for op in opciones:
        nombre = op.get('displayName', '')
        familia = ""
        for f in op.get('fields', []):
            if f['key'] == 'familia' and f['value']:
                try:
                    val = json.loads(f['value'])
                    familia = str(val[0]) if isinstance(val, list) and val else str(val)
                except: familia = str(f['value'])
                break
        opciones_genericas.append({'id': op['id'], 'text': nombre, 'family': familia})
    
    dialog = ShopifyReferenceSelectDialog(parent, f"SELECCIONAR {tipo_meta}", opciones_genericas, 
                                        seleccionados_actuales, multi_select=True, agrupar_por_familia=True)
    parent.wait_window(dialog)
    return dialog.result

def show_metacampos_agrupados_dialog(parent, titulo: str, grupos: List[Dict[str, Any]],
                                     seleccion_actual: Dict[str, List[str]]) -> Optional[Dict[str, List[str]]]:
    """Un diálogo para varios metacampos a la vez, cada uno como grupo.

    Args:
        grupos: [{'titulo': str, 'unico': bool,
                  'opciones': [{'id': str, 'text': str}]}]
        seleccion_actual: {titulo_grupo: [ids marcados]}
    Devuelve {titulo_grupo: [ids elegidos]} o None si se cancela.
    """
    opciones = []
    unicas = set()
    for g in grupos:
        if g.get('unico'):
            unicas.add(g['titulo'])
        for op in g.get('opciones', []):
            opciones.append({'id': op['id'], 'text': op['text'], 'family': g['titulo']})

    planos = [i for ids in (seleccion_actual or {}).values() for i in ids]
    dialog = ShopifyReferenceSelectDialog(
        parent, titulo, opciones, planos,
        multi_select=True, agrupar_por_familia=True, familias_unicas=unicas)
    parent.wait_window(dialog)
    if dialog.result is None:
        return None

    familia_por_id = {op['id']: op['family'] for op in opciones}
    resultado: Dict[str, List[str]] = {}
    for gid in dialog.result:
        resultado.setdefault(familia_por_id.get(gid, ''), []).append(gid)
    return resultado


def show_reference_select_dialog(parent, titulo: str, opciones: List[Dict[str, Any]],
                                seleccion_actual: Union[str, List[str], None],
                                multi_select: bool = False,
                                agrupar: bool = False,
                                columnas: int = 4) -> Union[str, List[str], None]:
    """Nueva función para cualquier referencia de Shopify (ej: Colecciones)."""
    dialog = ShopifyReferenceSelectDialog(parent, titulo, opciones, seleccion_actual,
                                        multi_select=multi_select, agrupar_por_familia=agrupar,
                                        columnas=columnas)
    parent.wait_window(dialog)
    return dialog.result
