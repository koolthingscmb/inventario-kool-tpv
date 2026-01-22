import time
import subprocess
import tkinter as tk
from tkinter import scrolledtext

def preview_ticket(parent, texto, modo='ventana'):
    """
    Mostrar una vista previa del ticket.
    modo: 'ventana' | 'archivo' | 'terminal'
    parent: widget padre (puede ser la ventana principal) o None
    texto: string con el contenido del ticket
    """
    if modo == 'terminal':
        print("\n--- TICKET ---\n")
        print(texto)
        print("\n--- FIN TICKET ---\n")
        return

    if modo == 'archivo':
        path = f"/tmp/ticket_{int(time.time())}.txt"
        with open(path, "w", encoding="utf-8") as f:
            f.write(texto)
        try:
            subprocess.run(["open", path])
        except Exception:
            pass
        return

    # modo 'ventana' (por defecto)
    try:
        top = tk.Toplevel(parent) if parent is not None else tk.Tk()
        top.title("Vista previa - Ticket")
        top.geometry("640x480")
        txt = scrolledtext.ScrolledText(top, wrap="none", font=("Courier", 10))
        txt.insert("1.0", texto)
        txt.configure(state="disabled")
        txt.pack(expand=True, fill="both")

        def guardar():
            p = f"/tmp/ticket_{int(time.time())}.txt"
            with open(p, "w", encoding="utf-8") as f:
                f.write(txt.get("1.0", "end"))
            try:
                subprocess.run(["open", p])
            except Exception:
                pass

        btn = tk.Button(top, text="Guardar y abrir", command=guardar)
        btn.pack(side="bottom", pady=6)
        return top
    except Exception:
        # Fallback: imprimir en terminal
        print(texto)
        return None
