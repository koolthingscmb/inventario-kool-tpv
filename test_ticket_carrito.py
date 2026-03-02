"""
Test visual del widget TicketCarrito
Muestra datos fake para validar diseño y funcionalidad
"""
import customtkinter as ctk
from datetime import datetime
from kool_tpv.utils.widgets.ticket_carrito import TicketCarrito
from kool_tpv.utils.keyboard_manager import KeyboardManager


class MockCarritoService:
    """Mock del CarritoService para testing."""

    def __init__(self):
        self.items = []
        self._add_test_items()

    def _add_test_items(self):
        """Añadir items de prueba con los 4 tipos de línea."""
        # Item normal 1
        self.items.append({
            "id": 1,
            "nombre": "Camiseta Basic",
            "cantidad": 2,
            "pvp": 19.99,
            "total": 39.98,
            "line_tipo": "normal"
        })

        # Item normal 2
        self.items.append({
            "id": 2,
            "nombre": "Pantalón Vaquero",
            "cantidad": 1,
            "pvp": 45.00,
            "total": 45.00,
            "line_tipo": "normal"
        })

        # Descuento
        self.items.append({
            "id": 3,
            "nombre": "DESCUENTO 10%",
            "cantidad": 1,
            "pvp": -8.50,
            "total": -8.50,
            "line_tipo": "descuento"
        })

        # Item tesoro
        self.items.append({
            "id": 4,
            "nombre": "CANJE TESORO",
            "cantidad": 1,
            "pvp": 0.00,
            "total": 0.00,
            "line_tipo": "tesoro"
        })

        # Item normal 3
        self.items.append({
            "id": 5,
            "nombre": "Zapatillas Running",
            "cantidad": 1,
            "pvp": 89.90,
            "total": 89.90,
            "line_tipo": "normal"
        })

    def get_items(self):
        """Devolver lista de items."""
        return self.items

    def get_resumen_financiero(self):
        """Devolver resumen con desglose de IVA."""
        subtotal = sum(item["total"] for item in self.items if item["line_tipo"] != "tesoro")

        # Desglose IVA fake (21% y 10%)
        base_21 = 120.38
        iva_21 = base_21 * 0.21

        base_10 = 45.00
        iva_10 = base_10 * 0.10

        total = subtotal + iva_21 + iva_10

        return {
            "subtotal": subtotal,
            "total": total,
            "desglose_iva": [
                {"tipo": 21, "base": base_21, "iva": iva_21},
                {"tipo": 10, "base": base_10, "iva": iva_10}
            ]
        }

    def add_item(self, item_data):
        """Añadir item o incrementar cantidad si ya existe."""
        try:
            item_id = item_data.get("id")

            # Buscar si ya existe
            for item in self.items:
                if item.get("id") == item_id:
                    # Ya existe: incrementar cantidad
                    item["cantidad"] += 1
                    item["total"] = item["pvp"] * item["cantidad"]
                    print(f"Mock: +1 unidad a {item.get('nombre')} (nueva qty: {item['cantidad']})")
                    return

            # No existe: añadir nuevo (normalmente no pasa en el test)
            self.items.append(item_data)
            print(f"Mock: item añadido {item_data.get('nombre')}")

        except Exception as e:
            print(f"Mock: error en add_item: {e}")

    def update_cantidad(self, idx, qty):
        """Actualizar cantidad (mock)."""
        if 0 <= idx < len(self.items):
            self.items[idx]["cantidad"] = qty
            self.items[idx]["total"] = self.items[idx]["pvp"] * qty
            print(f"Mock: cantidad actualizada a {qty}")

    def remove_item(self, idx):
        """Eliminar item (mock)."""
        if 0 <= idx < len(self.items):
            removed = self.items.pop(idx)
            print(f"Mock: item eliminado: {removed.get('nombre')}")


class TestApp(ctk.CTk):
    """Aplicación de test para TicketCarrito."""

    def __init__(self):
        super().__init__()

        self.title("Test: Ticket Carrito + Payment Controllers")
        self.geometry("800x900")

        ctk.set_appearance_mode("dark")

        # Layout: ticket a la izquierda, controles a la derecha
        main_container = ctk.CTkFrame(self, fg_color="transparent")
        main_container.pack(fill="both", expand=True, padx=10, pady=10)

        # Column 1: Ticket
        ticket_col = ctk.CTkFrame(main_container, fg_color="transparent")
        ticket_col.pack(side="left", fill="both", expand=True)

        # Mock del servicio
        self.mock_service = MockCarritoService()

        # KeyboardManager global (simula app real)
        self.keyboard_manager = KeyboardManager(self)

        # Crear widget
        self.ticket = TicketCarrito(
            parent=ticket_col,
            carrito_service=self.mock_service,
            keyboard_manager=self.keyboard_manager
        )
        self.ticket.pack(fill="both", expand=True)

        # Actualizar datos iniciales
        self.ticket.update_cajero("Juan Pérez")

        # Cliente de prueba
        self.ticket.update_cliente({
            "nombre": "María García - Lv 5 (VIP)",
            "tesoro_total": 1250
        })

        # Refrescar carrito
        self.ticket.update_carrito()

        # Iniciar reloj
        self._update_clock()

        # Column 2: Panel de controles
        controls_col = ctk.CTkFrame(main_container, fg_color="#2a2a2a", width=250)
        controls_col.pack(side="right", fill="y", padx=(10, 0))
        controls_col.pack_propagate(False)

        self._create_controls(controls_col)

    def _create_controls(self, parent):
        """Crear panel de controles."""
        title = ctk.CTkLabel(
            parent,
            text="PAYMENT CONTROLLERS",
            font=("Courier New", 16, "bold"),
            text_color="#00FF00"
        )
        title.pack(pady=(20, 10))

        # Botones para activar cada forma de pago
        btn_efectivo = ctk.CTkButton(
            parent,
            text="EFECTIVO",
            command=self._activar_efectivo,
            fg_color="#2ecc71",
            hover_color="#27ae60",
            width=200,
            height=40
        )
        btn_efectivo.pack(pady=8)

        btn_tarjeta = ctk.CTkButton(
            parent,
            text="TARJETA",
            command=self._activar_tarjeta,
            fg_color="#3498db",
            hover_color="#2980b9",
            width=200,
            height=40
        )
        btn_tarjeta.pack(pady=8)

        btn_web = ctk.CTkButton(
            parent,
            text="WEB",
            command=self._activar_web,
            fg_color="#88B04B",
            hover_color="#6a8e3a",
            width=200,
            height=40
        )
        btn_web.pack(pady=8)

        btn_multi = ctk.CTkButton(
            parent,
            text="MULTI $",
            command=self._activar_multi,
            fg_color="#9b59b6",
            hover_color="#8e44ad",
            width=200,
            height=40
        )
        btn_multi.pack(pady=8)

        # Separador
        separator = ctk.CTkFrame(parent, height=2, fg_color="#555555")
        separator.pack(fill="x", pady=20, padx=20)

        # Botón desactivar
        btn_desactivar = ctk.CTkButton(
            parent,
            text="DESACTIVAR PAGO",
            command=self._desactivar_pago,
            fg_color="#e74c3c",
            hover_color="#c0392b",
            width=200,
            height=40
        )
        btn_desactivar.pack(pady=8)

        # Label para mostrar resultado
        self.result_label = ctk.CTkLabel(
            parent,
            text="",
            font=("Courier New", 12),
            text_color="#00FF00",
            wraplength=220
        )
        self.result_label.pack(pady=(20, 0), padx=10)

    def _activar_efectivo(self):
        """Activar pago efectivo."""
        self.ticket.activar_pago_efectivo(on_finalizar=self._on_pago_finalizado)
        self.result_label.configure(text="⚡ Efectivo activado")

    def _activar_tarjeta(self):
        """Activar pago tarjeta."""
        self.ticket.activar_pago_tarjeta(on_finalizar=self._on_pago_finalizado)
        self.result_label.configure(text="⚡ Tarjeta activada")

    def _activar_web(self):
        """Activar pago web."""
        self.ticket.activar_pago_web(on_finalizar=self._on_pago_finalizado)
        self.result_label.configure(text="⚡ Web activada")

    def _activar_multi(self):
        """Activar pago multi."""
        self.ticket.activar_pago_multi(on_finalizar=self._on_pago_finalizado)
        self.result_label.configure(text="⚡ Multi activado")

    def _desactivar_pago(self):
        """Desactivar forma de pago."""
        self.ticket.desactivar_pago()
        self.result_label.configure(text="✓ Pago desactivado")

    def _on_pago_finalizado(self, data: dict):
        """Callback cuando se finaliza el pago."""
        tipo = data.get("tipo_pago", "?")
        total = data.get("total", 0.0)

        mensaje = f"✓ VENTA FINALIZADA\n\nTipo: {tipo}\nTotal: {total:.2f}€"

        if tipo == "Efectivo":
            cambio = data.get("cambio", 0.0)
            mensaje += f"\nCambio: {cambio:.2f}€"

        if tipo == "Multi":
            efectivo = data.get("efectivo", 0.0)
            tarjeta = data.get("tarjeta", 0.0)
            mensaje += f"\nEfectivo: {efectivo:.2f}€\nTarjeta: {tarjeta:.2f}€"

        self.result_label.configure(text=mensaje)

        # Log en consola
        print("=" * 50)
        print("PAGO FINALIZADO:")
        for k, v in data.items():
            print(f"  {k}: {v}")
        print("=" * 50)

    def _update_clock(self):
        """Actualizar hora en tiempo real."""
        from datetime import datetime
        now = datetime.now()
        hora_str = now.strftime("%H:%M:%S - %d/%m/%Y")
        self.ticket.update_hora(hora_str)

        # Re-programar cada segundo
        self.after(1000, self._update_clock)


if __name__ == "__main__":
    app = TestApp()
    app.mainloop()
