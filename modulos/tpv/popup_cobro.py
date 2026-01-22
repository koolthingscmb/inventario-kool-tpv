import customtkinter as ctk

class VentanaCobro(ctk.CTkToplevel):
    def __init__(self, parent, total_a_pagar, on_cobro_realizado):
        super().__init__(parent)
        self.on_cobro_realizado = on_cobro_realizado
        self.total = total_a_pagar

        self.title("COBRAR EN EFECTIVO")
        self.geometry("400x500")
        
        # Esto hace que la ventana sea "MODAL" (no puedes tocar la de atrás hasta cerrar esta)
        self.transient(parent)
        self.grab_set()

        # Diseño
        self.configurar_ui()

    def configurar_ui(self):
        # Título
        ctk.CTkLabel(self, text="TOTAL A PAGAR", font=("Arial", 14)).pack(pady=(20,5))
        ctk.CTkLabel(self, text=f"{self.total:.2f} €", font=("Arial", 40, "bold"), text_color="#2CC985").pack(pady=5)

        # Entrada
        ctk.CTkLabel(self, text="Entregado por cliente:", font=("Arial", 14)).pack(pady=(30,5))
        
        # Evento: Al soltar una tecla (<KeyRelease>), recalculamos el cambio
        self.entry_entregado = ctk.CTkEntry(self, font=("Arial", 20), justify="center")
        self.entry_entregado.pack(pady=5, padx=50)
        self.entry_entregado.bind("<KeyRelease>", self.calcular_cambio)
        self.entry_entregado.focus() # Pone el cursor directamente para escribir

        # Etiqueta Cambio
        self.lbl_cambio = ctk.CTkLabel(self, text="CAMBIO: 0.00 €", font=("Arial", 24, "bold"), text_color="orange")
        self.lbl_cambio.pack(pady=30)

        # Botón Finalizar (Desactivado al principio)
        self.btn_finalizar = ctk.CTkButton(self, text="✅ FINALIZAR E IMPRIMIR", height=60, 
                                           fg_color="green", hover_color="darkgreen", font=("Arial", 16, "bold"),
                                           state="disabled", 
                                           command=self.finalizar)
        self.btn_finalizar.pack(side="bottom", fill="x", padx=20, pady=20)

    def calcular_cambio(self, event):
        try:
            # Reemplazamos coma por punto por si acaso
            texto = self.entry_entregado.get().replace(',', '.')
            if not texto: return
            
            entregado = float(texto)
            cambio = entregado - self.total
            
            if cambio >= -0.01: # Usamos -0.01 para evitar errores de redondeo
                self.lbl_cambio.configure(text=f"CAMBIO: {cambio:.2f} €", text_color="white")
                self.btn_finalizar.configure(state="normal") # Activamos botón
            else:
                faltante = abs(cambio)
                self.lbl_cambio.configure(text=f"FALTA: {faltante:.2f} €", text_color="#FF5555")
                self.btn_finalizar.configure(state="disabled")

        except ValueError:
            pass # Si escriben letras no hacemos nada

    def finalizar(self):
        try:
            entregado = float(self.entry_entregado.get().replace(',', '.'))
            cambio = entregado - self.total
            print("Cobro validado.")
            self.on_cobro_realizado(entregado, cambio)
            self.destroy()
        except:
            pass