import customtkinter as ctk
import tkinter as tk
from typing import List, Dict, Any, Optional, Union
from .base_dialog import BaseDialog
from kool_tpv.utils.factories.button_factory import ButtonFactory

class ShopifyReferenceSelectDialog(BaseDialog):
    """Diálogo genérico para selección de referencias de Shopify (Metaobjetos, Colecciones, etc).
    
    Muestra los elementos en un grid de 3 columnas con buscador integrado.
    """
    
    def __init__(self, parent, titulo: str, opciones: List[Dict[str, Any]], 
                 seleccion_actual: Optional[Union[str, List[str]]] = None, 
                 multi_select: bool = True,
                 agrupar_por_familia: bool = True):
        """
        Args:
            opciones: Lista de dicts con {'id': str, 'text': str, 'family': str}
            seleccion_actual: GID o lista de GIDs seleccionados.
        """
        self.titulo_ui = titulo
        self.multi_select = multi_select
        self.agrupar = agrupar_por_familia
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
        self.geometry("900x750") # Ancho para el grid de 3 columnas
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

        # 1. Buscador
        search_frame = ctk.CTkFrame(main_container, fg_color='transparent')
        search_frame.pack(fill='x', pady=(0, 15))
        
        ctk.CTkLabel(search_frame, text="BUSCAR:", font=self._get_font('message')).pack(side="left", padx=10)
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self._on_search_change)
        
        self.search_entry = ctk.CTkEntry(
            search_frame, textvariable=self.search_var, 
            placeholder_text="Escribe para filtrar la lista...",
            height=35, font=self._get_font('message')
        )
        self.search_entry.pack(side="left", fill="x", expand=True, padx=10)
        
        # 2. Área de scroll con Grid
        self.scroll_frame = ctk.CTkScrollableFrame(
            main_container, fg_color='transparent',
            scrollbar_button_color=primary_color
        )
        self.scroll_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Configurar 3 columnas iguales
        for i in range(3):
            self.scroll_frame.columnconfigure(i, weight=1)

        self._render_lista()

        # 3. Botones
        self._crear_botones(content_frame, btn_text='CONFIRMAR SELECCIÓN', confirm=True)

    def _render_lista(self):
        """Dibuja la lista (filtrada o no) en un grid de 3 columnas."""
        for child in self.scroll_frame.winfo_children():
            child.destroy()
            
        filtro = self.search_var.get().lower().strip()
        message_font = self._get_font('message')
        primary_color = self.dialogs_colors.get(self.tipo, {}).get('primary', '#00A4DF')
        
        current_familia = None
        fila_actual = 0
        col_actual = 0
        
        opciones_a_dibujar = [o for o in self.opciones_mostradas if not filtro or filtro in o['text'].lower()]
        
        if not opciones_a_dibujar:
            ctk.CTkLabel(self.scroll_frame, text="Sin resultados", font=message_font, text_color="#666").grid(row=0, column=0, columnspan=3, pady=20)
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
                    lbl_fam.grid(row=fila_actual, column=0, columnspan=3, pady=(15, 5), sticky="w", padx=10)
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
            if col_actual >= 3:
                col_actual = 0
                fila_actual += 1
        
        if col_actual > 0: fila_actual += 1
        ctk.CTkLabel(self.scroll_frame, text="", height=1).grid(row=fila_actual, column=0)

    def _on_search_change(self, *args):
        self._render_lista()

    def _toggle_selection(self, item_id: str, is_selected: bool):
        if is_selected: self.seleccionados.add(item_id)
        else: self.seleccionados.discard(item_id)

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

def show_reference_select_dialog(parent, titulo: str, opciones: List[Dict[str, Any]], 
                                seleccion_actual: Union[str, List[str], None], 
                                multi_select: bool = False,
                                agrupar: bool = False) -> Union[str, List[str], None]:
    """Nueva función para cualquier referencia de Shopify (ej: Colecciones)."""
    dialog = ShopifyReferenceSelectDialog(parent, titulo, opciones, seleccion_actual, 
                                        multi_select=multi_select, agrupar_por_familia=agrupar)
    parent.wait_window(dialog)
    return dialog.result
