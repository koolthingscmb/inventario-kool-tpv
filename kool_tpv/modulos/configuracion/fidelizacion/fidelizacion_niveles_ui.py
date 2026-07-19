import logging
import os
import shutil
from pathlib import Path
import customtkinter as ctk
from kool_tpv.utils.config_loader import load_colors, create_action_button
from kool_tpv.utils.font_loader import get_font
from kool_tpv.utils.widgets.virtual_nav_list import VirtualNavList
from kool_tpv.base_datos.niveles_service import NivelesService
from kool_tpv.base_datos.money_adapter import prepare_for_db, read_from_db
from kool_tpv.utils.widgets.notificaciones import ToastWidget
from kool_tpv.modulos.almacen.producto_repository import ProductoRepository


class FidelizacionNivelesUI:
    def __init__(self, parent, db, module_name='config', keyboard_manager=None):
        self.parent = parent
        self.db = db
        self.module_name = module_name
        self.keyboard_manager = keyboard_manager
        self.service = NivelesService(db)
        self.producto_repo = ProductoRepository(db)

        try:
            self.colors = load_colors(module_name)
        except Exception:
            logging.exception('Error cargando colores en FidelizacionNivelesUI')
            self.colors = {}

        bg = self.colors.get('background', '#000000')
        self.container = ctk.CTkFrame(parent, fg_color=bg)

        # Estado
        self.selected_nivel = None
        self.modo_edicion = False  # True si estamos editando, False si creando nuevo
        self.selected_producto_sku = None  # SKU del producto seleccionado cuando tipo='Artículo'
        self.lore_textboxes = []  # Lista de CTTextbox widgets para lores

        # Body frame: split horizontal (left_panel 25% | right_panel 75%)
        body_frame = ctk.CTkFrame(self.container, fg_color='transparent')
        body_frame.pack(fill='both', expand=True, padx=20, pady=20)

        # --- Panel IZQUIERDO: nav_list de niveles existentes (25%)
        left_panel = ctk.CTkFrame(body_frame, fg_color=self.colors.get('bg_dark', '#1a1a1a'), width=300)
        left_panel.pack(side='left', fill='y', padx=(0, 6))
        left_panel.pack_propagate(False)

        self.nav_list = VirtualNavList(
            left_panel,
            columns=[
                ('level', 60, 'Lvl'),
                ('nombre_nivel', 120, 'Nombre'),
                ('tesoro_minimo', 80, 'Puntos')
            ],
            on_select=self._on_nivel_select,
            module_name=module_name,
            keyboard_manager=self.keyboard_manager
        )
        self.nav_list.pack(fill='both', expand=True, padx=6, pady=6)

        # --- Panel DERECHO: formulario en grid 8 columnas
        right_panel = ctk.CTkFrame(body_frame, fg_color='transparent')
        right_panel.pack(side='left', fill='both', expand=True)

        self.header_frame = ctk.CTkFrame(right_panel, fg_color=bg)
        self.header_frame.pack(fill='x')

        for c in range(8):
            self.header_frame.grid_columnconfigure(c, weight=1)

        entry_kw = {
            'fg_color': bg,
            'text_color': self.colors.get('text', '#FFFFFF'),
            'border_width': 2,
            'border_color': self.colors.get('border', self.colors.get('primary')),
            'font': get_font('entry', module=module_name)
        }

        # Fila 0: LEVEL | NOMBRE LEVEL | GRAFISMO (badge buttons)
        ctk.CTkLabel(
            self.header_frame,
            text='Level:',
            font=get_font('label', module=module_name),
            text_color=self.colors.get('text')
        ).grid(row=0, column=0, sticky='w', padx=6, pady=6)

        self.entry_level = ctk.CTkEntry(self.header_frame, width=80, **entry_kw)
        self.entry_level.grid(row=0, column=1, sticky='ew', padx=6, pady=6)

        ctk.CTkLabel(
            self.header_frame,
            text='Nombre Level:',
            font=get_font('label', module=module_name),
            text_color=self.colors.get('text')
        ).grid(row=0, column=2, sticky='w', padx=6, pady=6)

        self.entry_nombre = ctk.CTkEntry(self.header_frame, **entry_kw)
        self.entry_nombre.grid(row=0, column=3, columnspan=3, sticky='ew', padx=6, pady=6)

        # Badge frame
        badge_frame = ctk.CTkFrame(self.header_frame, fg_color='transparent')
        badge_frame.grid(row=0, column=6, columnspan=2, sticky='ew', padx=6, pady=6)

        self.entry_grafismo = ctk.CTkEntry(badge_frame, width=120, **entry_kw)
        self.entry_grafismo.pack(side='left', padx=(0, 4))
        self.entry_grafismo.configure(state='disabled')

        self.btn_subir_badge = ctk.CTkButton(
            badge_frame,
            text='📁',
            width=36,
            height=32,
            fg_color=self.colors.get('primary', '#FF9800'),
            hover_color=self.colors.get('primary_hover', '#F57C00'),
            command=self._subir_badge
        )
        self.btn_subir_badge.pack(side='left', padx=2)

        self.btn_limpiar_badge = ctk.CTkButton(
            badge_frame,
            text='🗑️',
            width=36,
            height=32,
            fg_color='#e74c3c',
            hover_color='#c0392b',
            command=self._limpiar_badge
        )
        self.btn_limpiar_badge.pack(side='left', padx=2)

        self.badge_preview = ctk.CTkLabel(
            badge_frame,
            text='',
            width=80,
            height=24,
            fg_color='#FFFFFF',
            corner_radius=4
        )
        self.badge_preview.pack(side='left', padx=(6, 0))

        # Fila 1: PUNTOS MÍNIMOS | TIPO RECOMPENSA | DETALLE
        ctk.CTkLabel(
            self.header_frame,
            text='Puntos mínimos:',
            font=get_font('label', module=module_name),
            text_color=self.colors.get('text')
        ).grid(row=1, column=0, sticky='w', padx=6, pady=6)

        self.entry_puntos = ctk.CTkEntry(self.header_frame, width=120, **entry_kw)
        self.entry_puntos.grid(row=1, column=1, sticky='ew', padx=6, pady=6)

        ctk.CTkLabel(
            self.header_frame,
            text='Tipo Recompensa:',
            font=get_font('label', module=module_name),
            text_color=self.colors.get('text')
        ).grid(row=1, column=2, sticky='w', padx=6, pady=6)

        self.combo_tipo_recompensa = ctk.CTkComboBox(
            self.header_frame,
            values=['', 'Descuento', 'Artículo'],
            fg_color=bg,
            button_color=self.colors.get('primary', '#FF9800'),
            border_color=self.colors.get('border', self.colors.get('primary')),
            text_color=self.colors.get('text'),
            font=get_font('entry', module=module_name),
            command=self._on_tipo_recompensa_change
        )
        self.combo_tipo_recompensa.grid(row=1, column=3, columnspan=2, sticky='ew', padx=6, pady=6)
        self.combo_tipo_recompensa.set('')

        ctk.CTkLabel(
            self.header_frame,
            text='Detalle:',
            font=get_font('label', module=module_name),
            text_color=self.colors.get('text')
        ).grid(row=1, column=5, sticky='w', padx=6, pady=6)

        self.entry_detalle = ctk.CTkEntry(self.header_frame, **entry_kw)
        self.entry_detalle.grid(row=1, column=6, columnspan=2, sticky='ew', padx=6, pady=6)

        # Fila 2: Buscador de productos (solo visible si Tipo = Artículo)
        self.producto_search_frame = ctk.CTkFrame(self.header_frame, fg_color='transparent')
        self.producto_search_frame.grid(row=2, column=0, columnspan=8, sticky='ew', padx=6, pady=6)

        self.entry_producto_search = ctk.CTkEntry(
            self.producto_search_frame,
            placeholder_text='Buscar producto (Enter)...',
            **entry_kw
        )
        self.entry_producto_search.pack(side='left', fill='x', expand=True, padx=(0, 6))
        self.entry_producto_search.bind('<Return>', self._on_producto_search)

        # Fila 3: NavList de productos (5 filas, solo visible si Tipo = Artículo)
        self.producto_list_frame = ctk.CTkFrame(self.header_frame, fg_color='transparent')
        self.producto_list_frame.grid(row=3, column=0, columnspan=8, sticky='ew', padx=6, pady=(0, 6))

        from kool_tpv.base_datos.producto_service import ProductoService
        self.producto_service = ProductoService(self.db)

        self.producto_nav_list = VirtualNavList(
            self.producto_list_frame,
            columns=[
                ('sku', 100, 'SKU'),
                ('nombre', 300, 'Nombre'),
                ('pvp', 80, 'PVP')
            ],
            on_select=self._on_producto_select,
            module_name=module_name,
            keyboard_manager=self.keyboard_manager
        )
        self.producto_nav_list.pack(fill='x', padx=6)
        self.producto_nav_list.configure(height=120)  # ~5 filas

        # Ocultar inicialmente
        self.producto_search_frame.grid_remove()
        self.producto_list_frame.grid_remove()

        # Fila 4+: Textboxes de Lore dinámicos
        self.lore_frame = ctk.CTkFrame(self.header_frame, fg_color='transparent')
        self.lore_frame.grid(row=4, column=0, columnspan=8, sticky='ew', padx=6, pady=6)

        ctk.CTkLabel(
            self.lore_frame,
            text='Lores de aventura:',
            font=get_font('label', module=module_name),
            text_color=self.colors.get('text')
        ).pack(anchor='w', padx=6, pady=(0, 6))

        # Frame para textboxes + botón +
        self.lore_textboxes_frame = ctk.CTkFrame(self.lore_frame, fg_color='transparent')
        self.lore_textboxes_frame.pack(fill='x')

        self.btn_add_lore = ctk.CTkButton(
            self.lore_frame,
            text='+ Añadir Lore',
            fg_color=self.colors.get('primary', '#FF9800'),
            hover_color=self.colors.get('primary_hover', '#F57C00'),
            command=self._on_add_lore
        )
        self.btn_add_lore.pack(anchor='e', padx=6, pady=6)

        # Footer: botones Guardar, Nuevo Nivel, Eliminar
        self.footer = ctk.CTkFrame(self.container, fg_color='transparent')
        self.footer.pack(side='bottom', fill='x', padx=12, pady=12)

        btn_guardar = create_action_button(self.footer, 'guardar', self._on_guardar)
        btn_guardar.pack(side='left', padx=8)

        btn_nuevo = create_action_button(self.footer, 'nuevo_nivel', self._on_nuevo_nivel)
        btn_nuevo.pack(side='left', padx=8)

        btn_eliminar = create_action_button(self.footer, 'eliminar', self._on_eliminar)
        btn_eliminar.pack(side='left', padx=8)

        # Cargar niveles
        self._load_niveles()

    def get_widget(self):
        return self.container

    def _load_niveles(self):
        """Cargar niveles desde BD."""
        try:
            niveles = self.service.get_all_niveles()

            items = [
                {
                    'id': nivel['id'],
                    'level': str(nivel['level']),
                    'nombre_nivel': nivel['nombre_nivel'],
                    'grafismo_nivel': nivel['grafismo_nivel'],
                    'tesoro_minimo': str(read_from_db(nivel['tesoro_minimo'])),
                    'tipo_recompensa': nivel['tipo_recompensa'],
                    'detalle_recompensa': nivel['detalle_recompensa']
                }
                for nivel in niveles
            ]
            self.nav_list.set_items(items)

        except Exception:
            logging.exception('Error cargando niveles')

    def _on_nivel_select(self, data):
        """Cargar nivel seleccionado en formulario."""
        # data viene del nav_list, pero necesitamos todos los campos de BD
        nivel_id = data.get('id')
        if not nivel_id:
            return

        # Cargar nivel completo desde BD
        nivel_completo = self.service.get_nivel(nivel_id)
        if not nivel_completo:
            return

        self.selected_nivel = nivel_completo
        self.modo_edicion = True

        try:
            self.entry_level.delete(0, 'end')
            self.entry_level.insert(0, str(nivel_completo.get('level', '')))

            self.entry_nombre.delete(0, 'end')
            self.entry_nombre.insert(0, nivel_completo.get('nombre_nivel', ''))

            self.entry_grafismo.configure(state='normal')
            self.entry_grafismo.delete(0, 'end')
            self.entry_grafismo.insert(0, nivel_completo.get('grafismo_nivel', ''))
            self.entry_grafismo.configure(state='disabled')
            self._actualizar_preview_badge(nivel_completo.get('grafismo_nivel', ''))

            self.entry_puntos.delete(0, 'end')
            self.entry_puntos.insert(0, str(read_from_db(nivel_completo.get('tesoro_minimo', 0))))

            tipo_rec = nivel_completo.get('tipo_recompensa', '')
            self.combo_tipo_recompensa.set(tipo_rec if tipo_rec else '')

            # Limpiar entry_detalle antes de cargar cualquier dato
            self.entry_detalle.configure(state='normal')
            self.entry_detalle.delete(0, 'end')

            # Cargar producto_sku y nombre del producto
            self.selected_producto_sku = nivel_completo.get('producto_sku') or None
            self.entry_producto_search.delete(0, 'end')
            if self.selected_producto_sku:
                producto = self.producto_repo.get_by_sku(self.selected_producto_sku)
                nombre_producto = producto.get('nombre', '') if producto else ''
                self.entry_detalle.insert(0, nombre_producto)
            else:
                self.entry_detalle.insert(0, nivel_completo.get('detalle_recompensa', ''))

            # Llamar a _on_tipo_recompensa_change DESPUÉS de cargar los datos
            self._on_tipo_recompensa_change(tipo_rec)

            # Cargar lores (split por |||)
            lore_text = nivel_completo.get('lore_recompensa', '')
            self._clear_lore_textboxes()
            if lore_text:
                lores = lore_text.split('|||')
                for lore in lores:
                    if lore.strip():
                        self._on_add_lore()
                        if self.lore_textboxes:
                            self.lore_textboxes[-1].delete('1.0', 'end')
                            self.lore_textboxes[-1].insert('1.0', lore.strip())

        except Exception:
            logging.exception('Error cargando nivel en formulario')

    def _on_nuevo_nivel(self):
        """Preparar formulario para crear nuevo nivel."""
        self.modo_edicion = False
        self.selected_nivel = None
        self.selected_producto_sku = None

        # Calcular siguiente level disponible
        siguiente_level = self._calcular_siguiente_level()

        # Limpiar entries
        self.entry_level.delete(0, 'end')
        self.entry_level.insert(0, str(siguiente_level))

        self.entry_nombre.delete(0, 'end')
        self.entry_grafismo.configure(state='normal')
        self.entry_grafismo.delete(0, 'end')
        self.entry_grafismo.configure(state='disabled')
        self._actualizar_preview_badge('')
        self.entry_puntos.delete(0, 'end')
        self.combo_tipo_recompensa.set('')
        self.entry_detalle.configure(state='normal')
        self.entry_detalle.delete(0, 'end')
        self._on_tipo_recompensa_change('')
        self._clear_lore_textboxes()

    def _calcular_siguiente_level(self):
        """Calcular próximo número de level disponible."""
        return self.service.get_next_level()

    def _on_guardar(self):
        """Guardar nivel (INSERT si nuevo, UPDATE si edición)."""
        # Validar campos obligatorios
        level = self.entry_level.get().strip()
        nombre = self.entry_nombre.get().strip()
        grafismo = self.entry_grafismo.get().strip()
        puntos = self.entry_puntos.get().strip()

        if not level or not nombre or not grafismo or not puntos:
            ToastWidget.show(
                self.container,
                'LEVEL, NOMBRE, GRAFISMO Y PUNTOS MÍNIMOS SON OBLIGATORIOS',
                tipo='error'
            )
            return

        # Validar que level y puntos sean numéricos
        try:
            level_num = int(level)
            puntos = puntos.replace(',', '.')
            puntos_num = float(puntos)
        except ValueError:
            ToastWidget.show(self.container, 'LEVEL DEBE SER ENTERO Y PUNTOS NUMÉRICO', tipo='error')
            return

        # Preparar datos
        tipo_rec = self.combo_tipo_recompensa.get().strip()
        detalle_rec = self.entry_detalle.get().strip()

        # Concatenar lores con |||
        lores = []
        for tb in self.lore_textboxes:
            lore_text = tb.get('1.0', 'end-1c').strip()
            if lore_text:
                lores.append(lore_text)
        lore_recompensa = '|||'.join(lores) if lores else None

        data = {
            'level': level_num,
            'nombre_nivel': nombre,
            'grafismo_nivel': grafismo,
            'tesoro_minimo': prepare_for_db(puntos_num),  # euros → céntimos enteros
            'tipo_recompensa': tipo_rec if tipo_rec else None,
            'detalle_recompensa': detalle_rec if detalle_rec else None,
            'producto_sku': self.selected_producto_sku if tipo_rec == 'Artículo' else None,
            'lore_recompensa': lore_recompensa
        }

        # Guardar o actualizar
        if self.modo_edicion and self.selected_nivel:
            ok = self.service.update_nivel(self.selected_nivel['id'], data)
            accion = 'actualizado'
        else:
            ok = self.service.save_nivel(data)
            accion = 'creado'

        if ok:
            self._load_niveles()
            self._on_nuevo_nivel()

            ToastWidget.show(self.parent, f'Nivel {accion}', tipo='success')
        else:
            ToastWidget.show(self.container, 'NO SE PUDO GUARDAR', tipo='error')

    def _on_eliminar(self):
        """Eliminar nivel seleccionado (con confirmación)."""
        if not self.selected_nivel:
            ToastWidget.show(self.container, 'SELECCIONA UN NIVEL PRIMERO', tipo='warning')
            return

        from kool_tpv.utils.custom_dialog import show_warning

        def _confirmar_eliminar():
            ok = self.service.delete_nivel(self.selected_nivel['id'])

            if ok:
                self._load_niveles()
                self._on_nuevo_nivel()

                ToastWidget.show(self.parent, 'Nivel eliminado', tipo='success')
            else:
                ToastWidget.show(self.container, 'NO SE PUDO ELIMINAR', tipo='error')

        show_warning(
            self.container,
            'Confirmar eliminación',
            f'¿Eliminar nivel {self.selected_nivel.get("level")} - {self.selected_nivel.get("nombre_nivel")}?',
            callback=_confirmar_eliminar
        )

    def _subir_badge(self):
        """Abrir diálogo para subir un badge y copiarlo a assets/badges."""
        from tkinter import filedialog
        
        level = self.entry_level.get().strip()
        if not level:
            ToastWidget.show(self.container, 'PRIMERO ASIGNA UN NÚMERO DE NIVEL', tipo='warning')
            return

        file_types = [('Imágenes PNG', '*.png')]
        file_path = filedialog.askopenfilename(title="Seleccionar Badge (48x48 PNG)", filetypes=file_types)
        
        if not file_path:
            return

        try:
            # Ruta relativa robusta a assets/badges
            dest_dir = Path(__file__).resolve().parent.parent.parent.parent / "assets" / "badges"
            dest_dir.mkdir(parents=True, exist_ok=True)

            ext = os.path.splitext(file_path)[1].lower()
            dest_filename = f"badge_level_{level}{ext}"
            dest_path = dest_dir / dest_filename

            # Copiar archivo
            shutil.copy2(file_path, dest_path)

            # Actualizar entry
            self.entry_grafismo.configure(state='normal')
            self.entry_grafismo.delete(0, 'end')
            self.entry_grafismo.insert(0, dest_filename)
            self.entry_grafismo.configure(state='disabled')
            self._actualizar_preview_badge(dest_filename)

            ToastWidget.show(self.container, f'BADGE GUARDADO: {dest_filename}', tipo='success')

        except Exception:
            logging.exception("Error subiendo badge")
            ToastWidget.show(self.container, 'NO SE PUDO SUBIR EL BADGE', tipo='error')

    def _limpiar_badge(self):
        """Limpiar el badge seleccionado."""
        self.entry_grafismo.configure(state='normal')
        self.entry_grafismo.delete(0, 'end')
        self.entry_grafismo.configure(state='disabled')
        self._actualizar_preview_badge('')

    def _actualizar_preview_badge(self, filename):
        """Actualizar la imagen de preview del badge."""
        if not filename:
            self.badge_preview.configure(image='')
            return
        try:
            badge_dir = Path(__file__).resolve().parent.parent.parent.parent / "assets" / "badges"
            img_path = badge_dir / filename
            if img_path.exists():
                from PIL import Image
                pil_img = Image.open(img_path)
                ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(120, 19))
                self.badge_preview.configure(image=ctk_img)
            else:
                self.badge_preview.configure(image='')
        except Exception:
            logging.exception('Error cargando preview de badge')
            self.badge_preview.configure(image='')

    def _on_tipo_recompensa_change(self, value):
        """Manejar cambio en combo Tipo Recompensa."""
        if value == 'Artículo':
            self.producto_search_frame.grid()
            self.producto_list_frame.grid()
            self.entry_detalle.configure(state='disabled')
        else:
            self.producto_search_frame.grid_remove()
            self.producto_list_frame.grid_remove()
            self.entry_detalle.configure(state='normal')
            self.selected_producto_sku = None

    def _on_producto_search(self, event):
        """Buscar productos al pulsar Enter."""
        termino = self.entry_producto_search.get().strip()
        try:
            productos = self.producto_service.buscar_productos_paginados(termino, limit=50, offset=0)
            items = [
                {
                    'sku': p.get('sku', ''),
                    'nombre': p.get('nombre', ''),
                    'pvp': str(p.get('pvp', '0.00')),
                    '_sku': p.get('sku', '')
                }
                for p in productos
            ]
            self.producto_nav_list.set_items(items)
        except Exception:
            logging.exception('Error buscando productos')
            self.producto_nav_list.set_items([])

    def _on_producto_select(self, data):
        """Seleccionar producto de la lista."""
        sku = data.get('_sku') or data.get('sku', '')
        nombre = data.get('nombre', '')
        if sku:
            self.selected_producto_sku = sku
            self.entry_detalle.configure(state='normal')
            self.entry_detalle.delete(0, 'end')
            self.entry_detalle.insert(0, nombre)
            self.entry_detalle.configure(state='disabled')

    def _on_add_lore(self):
        """Añadir un nuevo textbox de lore."""
        lore_row = ctk.CTkFrame(self.lore_textboxes_frame, fg_color='transparent')
        lore_row.pack(fill='x', pady=2)

        lore_tb = ctk.CTkTextbox(
            lore_row,
            height=60,
            fg_color=self.colors.get('background', '#000000'),
            text_color=self.colors.get('text', '#FFFFFF'),
            border_color=self.colors.get('border', self.colors.get('primary')),
            border_width=2,
            font=get_font('entry', module=self.module_name)
        )
        lore_tb.pack(side='left', fill='x', expand=True, padx=(0, 6))

        btn_remove = ctk.CTkButton(
            lore_row,
            text='−',
            width=30,
            height=30,
            fg_color='#e74c3c',
            hover_color='#c0392b',
            command=lambda: self._remove_lore(lore_row, lore_tb)
        )
        btn_remove.pack(side='left')

        self.lore_textboxes.append(lore_tb)

    def _remove_lore(self, row_widget, textbox_widget):
        """Eliminar un textbox de lore."""
        row_widget.destroy()
        if textbox_widget in self.lore_textboxes:
            self.lore_textboxes.remove(textbox_widget)

    def _clear_lore_textboxes(self):
        """Eliminar todos los textboxes de lore."""
        for tb in self.lore_textboxes[:]:
            tb.master.destroy()
        self.lore_textboxes.clear()
