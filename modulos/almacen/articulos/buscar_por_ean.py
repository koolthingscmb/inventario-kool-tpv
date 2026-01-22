import sqlite3
import customtkinter as ctk

class BuscarPorEAN:
    def __init__(self, parent, controller):
        self.parent = parent
        self.controller = controller
        self.producto_id_encontrado = None

    def render(self):
        for w in self.parent.winfo_children():
            w.destroy()

        ctk.CTkLabel(self.parent, text="BUSCAR POR EAN / SKU", font=("Arial", 16, "bold"), text_color="white").pack(pady=(10, 6))

        frame = ctk.CTkFrame(self.parent, fg_color="transparent")
        frame.pack(pady=6)

        self.entry = ctk.CTkEntry(frame, width=400, placeholder_text="Escanea el artículo")
        self.entry.grid(row=0, column=0, padx=6, pady=6)
        self.entry.bind('<Return>', self._buscar)
        try:
            self.entry.focus()
        except Exception:
            pass

        self.btn_ir = ctk.CTkButton(frame, text="Ir al producto", width=160, state="disabled", command=self._ir_al_producto)
        self.btn_ir.grid(row=0, column=1, padx=6, pady=6)

        self.lbl_result = ctk.CTkLabel(self.parent, text="", font=("Arial", 14), text_color="gray")
        self.lbl_result.pack(pady=8)

        btn_back = ctk.CTkButton(self.parent, text="Volver", width=120, command=self.controller.mostrar_submenu_almacen)
        btn_back.pack(pady=8)

        # If we have a saved state on the controller, restore it
        try:
            estado = getattr(self.controller, 'ultima_buscar_por_ean_state', None)
            if estado and estado.get('codigo'):
                self.entry.delete(0, 'end')
                self.entry.insert(0, estado.get('codigo'))
                # run a search to show the previous result
                self._buscar()
                # once restored, clear the saved state (but keep active flag until UI logic consumes it)
                # do not clear ultima_buscar_por_ean_active here; UI starter will clear it
        except Exception:
            pass

    def _buscar(self, event=None):
        codigo = self.entry.get().strip()
        if not codigo:
            self.lbl_result.configure(text="Introduce un EAN o SKU", text_color="gray")
            self.btn_ir.configure(state="disabled")
            self.producto_id_encontrado = None
            return

        try:
            from database import connect
            conn = connect()
            cursor = conn.cursor()

            # Primero intentamos buscar en codigos_barras
            cursor.execute('SELECT producto_id FROM codigos_barras WHERE ean = ? LIMIT 1', (codigo,))
            row = cursor.fetchone()
            producto_id = None
            if row:
                producto_id = row[0]
            else:
                # Intentar buscar por SKU
                cursor.execute('SELECT id FROM productos WHERE sku = ? LIMIT 1', (codigo,))
                r2 = cursor.fetchone()
                if r2:
                    producto_id = r2[0]

            if producto_id:
                cursor.execute('SELECT nombre FROM productos WHERE id = ? LIMIT 1', (producto_id,))
                info = cursor.fetchone()
                nombre = info[0] if info else f'ID {producto_id}'
                self.lbl_result.configure(text=f'Encontrado: {nombre}', text_color="white")
                self.btn_ir.configure(state="normal")
                self.producto_id_encontrado = producto_id
                # If this search was triggered by Enter, go directly to the producto
                if event is not None:
                    try:
                        # save state so we can restore the buscar_por_ean screen when returning
                        self.controller.ultima_buscar_por_ean_state = {'codigo': codigo, 'producto_id': producto_id}
                        self.controller.ultima_buscar_por_ean_active = True
                    except Exception:
                        pass
                    try:
                        self.controller.mostrar_crear_producto(producto_id)
                        return
                    except Exception as e:
                        print(f"Error abriendo producto desde EAN: {e}")
            else:
                self.lbl_result.configure(text='No existe artículo', text_color="#ff3333")
                self.btn_ir.configure(state="disabled")
                self.producto_id_encontrado = None

        except Exception as e:
            self.lbl_result.configure(text=f'Error: {e}', text_color="#ff3333")
            self.btn_ir.configure(state="disabled")
            self.producto_id_encontrado = None
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def _ir_al_producto(self):
        if self.producto_id_encontrado:
            try:
                # Save state so returning can restore this buscar_por_ean screen
                try:
                    codigo = self.entry.get().strip()
                    self.controller.ultima_buscar_por_ean_state = {'codigo': codigo, 'producto_id': self.producto_id_encontrado}
                    self.controller.ultima_buscar_por_ean_active = True
                except Exception:
                    pass
                self.controller.mostrar_crear_producto(self.producto_id_encontrado)
            except Exception as e:
                print(f"Error al ir al producto: {e}")
