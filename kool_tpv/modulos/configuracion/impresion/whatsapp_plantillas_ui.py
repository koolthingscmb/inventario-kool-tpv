import logging
import json
import customtkinter as ctk
from typing import List, Dict

from kool_tpv.utils.templates.pagina_con_visor import PaginaConVisor
from kool_tpv.utils.config_loader import create_action_button, load_colors
from kool_tpv.utils.font_loader import get_font
from kool_tpv.base_datos.configuracion_repository import ConfiguracionRepository
from kool_tpv.utils.widgets.notificaciones import ToastWidget

class WhatsappPlantillasUI(PaginaConVisor):
    """Interfaz para gestionar plantillas de mensajes de WhatsApp."""
    
    def __init__(self, parent, db, module_name: str = 'config'):
        self.config_repo = ConfiguracionRepository(db)
        self.plantillas = []
        self.index_seleccionada = -1
        
        # Breadcrumb name para BaseModuleView auto-update
        self.breadcrumb_name = 'CONFIG / IMPRESIÓN / WASSAP'
        
        super().__init__(parent, db=db, module_name=module_name)
        
        # Forzar recarga de colores específicos si es necesario
        try:
            self.colors = load_colors(module_name)
        except Exception:
            pass
            
        self._cargar_plantillas()

    def _build_header(self):
        """Header con selector de plantilla."""
        header_content = ctk.CTkFrame(self.header, fg_color='transparent')
        header_content.pack(fill='x', padx=12, pady=12)

        ctk.CTkLabel(
            header_content,
            text='PLANTILLAS WHATSAPP:',
            font=get_font('label', module='config'),
            text_color=self.colors.get('text', '#FFFFFF')
        ).pack(side='left', padx=(0, 12))

        self.combo_plantilla = ctk.CTkComboBox(
            header_content,
            values=['Cargando...'],
            width=300,
            font=get_font('entry', module='config'),
            command=self._on_plantilla_change
        )
        self.combo_plantilla.pack(side='left')
        
        self.label_info = ctk.CTkLabel(
            header_content,
            text='(Selecciona o crea una nueva)',
            font=get_font('body', module='config'),
            text_color=self.colors.get('accent', '#00FFFF')
        )
        self.label_info.pack(side='left', padx=(20, 0))

    def _build_grid(self):
        """Formulario de edición en el área central."""
        # Limpiar grid_scroll
        for child in self.grid_scroll.winfo_children():
            try: child.destroy()
            except: pass

        bg = self.colors.get('background', '#000000')
        self.edit_frame = ctk.CTkFrame(self.grid_scroll, fg_color=bg)
        self.edit_frame.pack(fill='both', expand=True, padx=20, pady=20)

        # Nombre de la plantilla
        ctk.CTkLabel(
            self.edit_frame, 
            text='NOMBRE DE LA PLANTILLA:', 
            font=get_font('label', module='config'),
            text_color=self.colors.get('text', '#FFFFFF')
        ).pack(anchor='w', pady=(0, 6))
        
        self.e_nombre = ctk.CTkEntry(
            self.edit_frame, 
            width=500,
            height=40,
            font=get_font('entry', module='config'),
            fg_color=self.colors.get('bg_dark', '#0d0d0d'),
            border_color=self.colors.get('primary', '#00FF00')
        )
        self.e_nombre.pack(anchor='w', pady=(0, 20))

        # Texto del mensaje
        ctk.CTkLabel(
            self.edit_frame, 
            text='TEXTO DEL MENSAJE:', 
            font=get_font('label', module='config'),
            text_color=self.colors.get('text', '#FFFFFF')
        ).pack(anchor='w', pady=(0, 6))
        
        self.e_texto = ctk.CTkTextbox(
            self.edit_frame, 
            height=300,
            font=get_font('entry', module='config'),
            fg_color=self.colors.get('bg_dark', '#0d0d0d'),
            border_color=self.colors.get('primary', '#00FF00'),
            border_width=2
        )
        self.e_texto.pack(fill='both', expand=True, pady=(0, 12))
        self.e_texto.bind("<KeyRelease>", lambda e: self._update_preview())

        # Ayuda variables
        ayuda_box = ctk.CTkFrame(self.edit_frame, fg_color='transparent')
        ayuda_box.pack(fill='x')
        
        ctk.CTkLabel(
            ayuda_box, 
            text='Variables disponibles (se sustituirán automáticamente):', 
            font=get_font('label', module='config', size=12),
            text_color=self.colors.get('secondary', '#00FF00')
        ).pack(anchor='w')
        
        ctk.CTkLabel(
            ayuda_box, 
            text='{nombre} - Nombre del cliente\n{telefono} - Teléfono del cliente\n{email} - Email del cliente\n{productos} - Artículos del pedido', 
            font=get_font('body', module='config', size=11),
            text_color=self.colors.get('text_secondary', '#888888'),
            justify='left'
        ).pack(anchor='w', padx=10)

    def _build_footer(self):
        """Botones de acción."""
        # Frame para botones
        btns_frame = ctk.CTkFrame(self.footer, fg_color='transparent')
        btns_frame.pack(fill='x', pady=10)

        self.btn_guardar = create_action_button(btns_frame, 'guardar', self._on_guardar)
        self.btn_guardar.pack(side='left', padx=12)

        # Botón NUEVA con estilo consistente
        self.btn_nueva = ctk.CTkButton(
            btns_frame, 
            text='NUEVA PLANTILLA', 
            command=self._on_nueva,
            width=160,
            height=40,
            font=get_font('label', module='config'),
            fg_color=self.colors.get('secondary', '#32CD32'),
            hover_color=self.colors.get('primary', '#00FF00'),
            text_color='#000000'
        )
        self.btn_nueva.pack(side='left', padx=12)

        self.btn_eliminar = create_action_button(btns_frame, 'eliminar', self._on_eliminar)
        self.btn_eliminar.pack(side='left', padx=12)

    def _cargar_plantillas(self):
        """Carga plantillas desde BD configuracion."""
        try:
            val = self.config_repo.obtener_multiples(['whatsapp_plantillas']).get('whatsapp_plantillas')
            if val:
                try:
                    self.plantillas = json.loads(val)
                except:
                    self.plantillas = []
            else:
                self.plantillas = []
            
            nombres = [p['nombre'] for p in self.plantillas]
            if not nombres:
                nombres = ['(Sin plantillas)']
            
            self.combo_plantilla.configure(values=nombres)
            if self.plantillas:
                self.combo_plantilla.set(nombres[0])
                self._on_plantilla_change(nombres[0])
            else:
                self.combo_plantilla.set('(Sin plantillas)')
                self._on_nueva()
        except Exception:
            logger.exception('Error cargando plantillas whatsapp')

    def _on_plantilla_change(self, value):
        """Manejador cambio de selección en combo."""
        idx = next((i for i, p in enumerate(self.plantillas) if p['nombre'] == value), -1)
        if idx != -1:
            self.index_seleccionada = idx
            p = self.plantillas[idx]
            self.e_nombre.delete(0, 'end')
            self.e_nombre.insert(0, p['nombre'])
            self.e_texto.delete('1.0', 'end')
            self.e_texto.insert('1.0', p['texto'])
            self._update_preview()
            self.label_info.configure(text=f"Editando: {p['nombre']}")

    def _on_nueva(self):
        """Preparar formulario para nueva plantilla."""
        self.index_seleccionada = -1
        self.e_nombre.delete(0, 'end')
        self.e_texto.delete('1.0', 'end')
        self.combo_plantilla.set('NUEVA PLANTILLA...')
        self.update_visor('Escribe un mensaje para ver el preview...')
        self.label_info.configure(text="Creando nueva plantilla")
        self.e_nombre.focus_set()

    def _on_guardar(self):
        """Guardar plantilla actual."""
        nombre = self.e_nombre.get().strip()
        texto = self.e_texto.get('1.0', 'end').strip()
        
        if not nombre or not texto:
            ToastWidget.show(self.container, 'NOMBRE Y MENSAJE OBLIGATORIOS', tipo='warning')
            return

        nueva_p = {'nombre': nombre, 'texto': texto}
        
        if self.index_seleccionada == -1:
            # Comprobar si ya existe una con ese nombre
            if any(p['nombre'].upper() == nombre.upper() for p in self.plantillas):
                ToastWidget.show(self.container, 'YA EXISTE UNA PLANTILLA CON ESE NOMBRE', tipo='error')
                return
            self.plantillas.append(nueva_p)
        else:
            self.plantillas[self.index_seleccionada] = nueva_p
        
        try:
            self.config_repo.guardar_multiples({'whatsapp_plantillas': json.dumps(self.plantillas, ensure_ascii=False)})
            ToastWidget.show(self.container, 'PLANTILLA GUARDADA CORRECTAMENTE', tipo='success')
            self._cargar_plantillas()
            self.combo_plantilla.set(nombre)
        except Exception:
            logger.exception('Error guardando plantillas whatsapp')
            ToastWidget.show(self.container, 'ERROR AL GUARDAR', tipo='error')

    def _on_eliminar(self):
        """Eliminar plantilla seleccionada."""
        if self.index_seleccionada == -1:
            return
        
        nombre = self.plantillas[self.index_seleccionada]['nombre']
        
        # Confirmación simple por Toast (opcional, aquí directo)
        del self.plantillas[self.index_seleccionada]
        try:
            self.config_repo.guardar_multiples({'whatsapp_plantillas': json.dumps(self.plantillas, ensure_ascii=False)})
            ToastWidget.show(self.container, f'PLANTILLA "{nombre}" ELIMINADA', tipo='info')
            self._cargar_plantillas()
        except Exception:
            logger.exception('Error eliminando plantilla whatsapp')
            ToastWidget.show(self.container, 'ERROR AL ELIMINAR', tipo='error')

    def _update_preview(self):
        """Actualizar el visor con el texto formateado."""
        texto = self.e_texto.get('1.0', 'end').strip()
        if not texto:
            self.update_visor('Escribe un mensaje para ver el preview...')
            return
            
        # Mock de reemplazo para preview
        preview = texto.replace('{nombre}', 'JUAN PÉREZ')\
                      .replace('{telefono}', '600123456')\
                      .replace('{email}', 'juan.perez@ejemplo.com')\
                      .replace('{productos}', 'Camiseta Azul, Taza Personalizada y 2 Stickers')
        
        self.update_visor(preview)
