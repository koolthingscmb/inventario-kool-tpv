import customtkinter as ctk
import tkinter as tk
from typing import List, Dict, Any, Optional
from .base_dialog import BaseDialog
from kool_tpv.utils.factories.button_factory import ButtonFactory

class MetaobjectSelectDialog(BaseDialog):
    """Diálogo para selección múltiple de metaobjetos de Shopify."""
    
    def __init__(self, parent, tipo_meta: str, opciones: List[Dict[str, Any]], seleccionados_actuales: List[str]):
        self.tipo_meta = tipo_meta
        self.opciones = self._procesar_y_ordenar_opciones(opciones)
        self.seleccionados_actuales = set(seleccionados_actuales)
        self.checkboxes = {}
        
        titulo = f"SELECCIONAR {tipo_meta.upper()}"
        super().__init__(parent, tipo='info', titulo=titulo)
        
        self._crear_contenido_especifico()
        # Ajustar geometría si es necesario (BaseDialog ya hace un setup inicial)
        self.geometry("600x700")
        self._center_window(parent, 600, 700)

    def _procesar_y_ordenar_opciones(self, opciones):
        """Extrae la familia, formatea el nombre y ordena la lista."""
        import json
        procesadas = []
        for op in opciones:
            nombre = op.get('displayName', '')
            familia = ""
            
            # Intentar extraer campo 'familia' de los fields
            fields = op.get('fields', [])
            for f in fields:
                if f['key'] == 'familia' and f['value']:
                    try:
                        # Shopify suele devolver las listas de metaobjetos como JSON: ["Valor"]
                        val = json.loads(f['value'])
                        if isinstance(val, list) and len(val) > 0:
                            familia = str(val[0])
                        else:
                            familia = str(val)
                    except:
                        familia = str(f['value'])
                    break
            
            # Guardar datos para el renderizado
            display_text = f"{nombre.upper()}"
            if familia:
                display_text += f" ({familia})"
            
            procesadas.append({
                'id': op['id'],
                'nombre': nombre,
                'familia': familia or "Z_SIN_FAMILIA", # Para que los sin familia vayan al final
                'display_text': display_text
            })
            
        # Ordenar: primero por familia, luego por nombre
        return sorted(procesadas, key=lambda x: (x['familia'], x['nombre']))

    def _crear_contenido_especifico(self):
        # 1. Crear barra de título (Kool Style)
        # Nota: BaseDialog._crear_barra_titulo devuelve el content_frame
        content_frame = self._crear_barra_titulo(self, self.title())
        
        tipo_config = self.dialogs_colors.get(self.tipo, {})
        primary_color = tipo_config.get('primary', '#00A4DF')
        message_font = self._get_font('message')
        button_font = self._get_font('button')
        
        main_container = ctk.CTkFrame(content_frame, fg_color='transparent')
        main_container.pack(fill='both', expand=True, padx=20, pady=10)
        
        ctk.CTkLabel(
            main_container, text=f"SELECCIONA {self.tipo_meta.upper()}:", 
            font=self._get_font('title'), text_color=primary_color
        ).pack(pady=(5, 10))

        # 2. Área de scroll con checkboxes
        scroll_frame = ctk.CTkScrollableFrame(
            main_container, fg_color='transparent',
            scrollbar_button_color=primary_color
        )
        scroll_frame.pack(fill='both', expand=True, padx=5, pady=5)

        current_familia = None
        for op in self.opciones:
            # Añadir separador visual si cambia la familia
            familia_real = op['familia'] if op['familia'] != "Z_SIN_FAMILIA" else "OTRAS"
            if familia_real != current_familia:
                current_familia = familia_real
                lbl_fam = ctk.CTkLabel(
                    scroll_frame, text=f"--- {current_familia.upper()} ---", 
                    font=("Helvetica", 10, "bold"), text_color="#666"
                )
                lbl_fam.pack(pady=(10, 5), anchor="w", padx=10)

            i_id = op['id']
            i_text = op['display_text']
            
            var = tk.BooleanVar(value=i_id in self.seleccionados_actuales)
            cb = ctk.CTkCheckBox(
                scroll_frame, text=i_text, variable=var,
                font=message_font, fg_color=primary_color
            )
            cb.pack(pady=3, anchor="w", padx=20)
            self.checkboxes[i_id] = var

        # 3. Botones (Kool Style)
        # self._crear_botones devuelve el botón de aceptar si confirm=True
        self._crear_botones(content_frame, btn_text='CONFIRMAR SELECCIÓN', confirm=True)

    def _on_accept(self):
        """Al pulsar confirmar, guardamos resultado y cerramos."""
        self.result = [gid for gid, var in self.checkboxes.items() if var.get()]
        try:
            self.grab_release()
        except: pass
        self.destroy()

    def _on_cancel(self):
        """Al cancelar, devolvemos None."""
        self.result = None
        try:
            self.grab_release()
        except: pass
        self.destroy()

def show_metaobject_select_dialog(parent, tipo_meta: str, opciones: List[Dict[str, Any]], seleccionados_actuales: List[str]) -> Optional[List[str]]:
    """Función helper para mostrar el diálogo y esperar resultado."""
    dialog = MetaobjectSelectDialog(parent, tipo_meta, opciones, seleccionados_actuales)
    parent.wait_window(dialog)
    return dialog.result
