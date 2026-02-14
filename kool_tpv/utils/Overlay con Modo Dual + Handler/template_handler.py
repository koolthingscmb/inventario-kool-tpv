"""Handler para modo secundario - PLANTILLA REUTILIZABLE

Copia este archivo y adapta los métodos a tu lógica.
"""
import logging
from kool_tpv.modulos.tpv.ui.visor_negro import VisorNegro


class MiHandler:
    """Handler ligero para gestionar el modo2 en MiUI."""

    def __init__(self, parent):
        self.parent = parent  # Referencia a MiUI
        self.db = getattr(parent, 'db', None)

    def load_modo2(self, termino=''):
        """Cargar datos para modo2."""
        try:
            # TODO: Implementar tu lógica de carga
            # Ejemplo:
            # sql = "SELECT id, col_a, col_b, col_c FROM mi_tabla ORDER BY fecha DESC LIMIT 25"
            # rows = self.db.fetch_all(sql)
            # items = []
            # for r in rows:
            #     items.append({'col_a': r[0], 'col_b': r[1], ...})
            # return items

            return []
        except Exception:
            logging.exception('Error cargando modo2')
            return []

    def render_modo2(self, items):
        """Renderizar items en el tree del parent."""
        try:
            tree = getattr(self.parent, 'tree', None)
            if tree is None:
                return

            for item in items:
                try:
                    iid = str(item.get('id') or '')
                    vals = (
                        item.get('col_a'),
                        item.get('col_b'),
                        item.get('col_c')
                    )
                    tree.insert('', 'end', iid=iid, values=vals)
                except Exception:
                    logging.exception('Error insertando fila')
        except Exception:
            logging.exception('Error render_modo2')

    def configurar_modo2(self):
        """CLAVE: Configurar UI para modo2.

        Este método se ejecuta AL CAMBIAR a modo2.
        Aquí es donde CREAS Y MUESTRAS el VisorNegro.
        """
        try:
            parent = self.parent

            # 1. Cambiar título
            try:
                parent.title_text = "MODO 2"
                if hasattr(parent, 'header_label'):
                    parent.header_label.configure(text=parent.title_text)
            except Exception:
                pass

            # 2. Aplicar columnas de modo2
            try:
                parent._aplicar_config_columnas(parent.columns_config_modo2)
            except Exception:
                pass

            # 3. Ocultar botones de modo1
            for btn in ['btn_accion1', 'btn_cambiar_modo2']:
                if hasattr(parent, btn):
                    try:
                        getattr(parent, btn).pack_forget()
                    except Exception:
                        pass

            # 4. Mostrar botones de modo2
            if hasattr(parent, 'btn_imprimir'):
                try:
                    parent.btn_imprimir.pack(side="left", padx=5)
                except Exception:
                    pass

            # 5. CREAR Y MOSTRAR VISORNEGRO INMEDIATAMENTE
            try:
                view = getattr(parent, 'view', None)
                parent_widget = None

                if view is not None and getattr(view, 'cart_view', None) is not None:
                    parent_widget = view.cart_view
                else:
                    parent_widget = getattr(parent, 'overlay', None)

                if parent_widget is not None:
                    # Crear si no existe
                    if getattr(parent, '_visor_negro', None) is None:
                        try:
                            parent._visor_negro = VisorNegro(parent_widget)
                        except Exception:
                            logging.exception('Error creando VisorNegro')

                    # Configurar y mostrar
                    try:
                        parent._visor_negro.set_text('')
                        parent._visor_negro.set_text_color('#00FF00')
                        parent._visor_negro.set_font_size(13)
                        parent._visor_negro.show()
                    except Exception:
                        pass
            except Exception:
                logging.exception('Error creando VisorNegro')

        except Exception:
            logging.exception('Error configurando modo2')

    def on_imprimir(self):
        """Acción específica del modo2."""
        try:
            parent = self.parent
            sel = list(parent.tree.selection() or [])
            if not sel:
                logging.info('No hay selección para imprimir')
                return

            # TODO: Implementar lógica de impresión
            item_id = int(sel[0])
            logging.info(f'Imprimiendo item {item_id}')

        except Exception:
            logging.exception('Error en on_imprimir')
