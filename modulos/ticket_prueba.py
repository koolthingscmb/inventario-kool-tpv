def imprimir_ticket(carrito, total, efectivo_entregado=None):
    print("\n" + "="*50)
    print("          TICKET DE COMPRA")
    print("="*50)
    print("Producto                    Cantidad    Precio")
    print("-"*50)
    for item in carrito:
        nombre = item['nombre'][:25].ljust(25)
        cantidad = str(item['cantidad']).ljust(10)
        precio = f"{item['precio']:.2f}"
        print(f"{nombre} {cantidad} {precio}")
    print("-"*50)
    print(f"Total: {total:.2f}")
    if efectivo_entregado:
        cambio = efectivo_entregado - total
        print(f"Efectivo entregado: {efectivo_entregado:.2f}")
        print(f"Cambio: {cambio:.2f}")
    print("="*50)
    print("Gracias por su compra!")
    print("="*50 + "\n")