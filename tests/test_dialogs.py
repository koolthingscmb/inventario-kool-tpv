import customtkinter as ctk
from kool_tpv.utils.custom_dialog import show_error, show_warning, show_info, show_password_dialog

root = ctk.CTk()
root.geometry("800x600")

def test_all():
    show_info(root, "Info Test", "Este es un diálogo de información")
    show_warning(root, "Warning Test", "Advertencia de prueba", confirm=True)
    show_error(root, "Error Test", "Error de prueba")
    pwd = show_password_dialog(root)
    print(f"Password ingresado: {pwd}")

btn = ctk.CTkButton(root, text="Probar Diálogos", command=test_all)
btn.pack(pady=50)

root.mainloop()
