from __future__ import annotations
from typing import Optional
from pathlib import Path
from datetime import datetime
import logging


class EscPosRenderer:
    """Convertidor básico de texto plano a secuencias ESC/POS.

    Esta clase ofrece la funcionalidad mínima para transformar el texto
    que ya genera `VentaTicketGenerator` en bytes listos para enviar a
    una impresora térmica ESC/POS.

    Nota: diseñado para extenderse (logo, códigos QR, estilos), pero
    implementa únicamente lo mínimo pedido ahora.
    """

    def __init__(self, encoding: str = "cp858", debug_dump: bool = False, dump_directory: Optional[Path] = None) -> None:
        self.logger = logging.getLogger(__name__)
        self.encoding = encoding
        # Control bytes
        self.ESC = b"\x1b"
        self.GS = b"\x1d"
        # Debug dump options
        self.debug_dump = bool(debug_dump)
        if dump_directory is None:
            self.dump_directory: Optional[Path] = None
        else:
            self.dump_directory = Path(dump_directory)

    def render_text_ticket(self, text: str, cut: bool = True, logo_path: Optional[Path] = None, qr_data: Optional[str] = None) -> bytes:
        """Renderiza `text` a bytes ESC/POS.

        Args:
            text: ticket en texto plano (puede contener múltiples líneas).
            cut: si True, añade comando de corte parcial al final.

        Returns:
            bytes listos para enviar a la impresora.
        """
        parts: list[bytes] = []

        # 1) Inicializar impresora (ESC @) + seleccionar codepage CP858 (ESC t 19) para soporte €
        try:
            parts.append(self.ESC + b"@")
            parts.append(self._set_codepage_cp858())
        except Exception:
            # safety: shouldn't fail
            self.logger.exception("Error creando secuencia de inicialización ESC@ / selección codepage")

        # 2) Insertar logo si procede (no imprimir, sólo generar bytes)
        if logo_path is not None:
            try:
                if isinstance(logo_path, Path) and logo_path.exists():
                    logo_bytes = self.render_logo_from_path(logo_path)
                    if logo_bytes:
                            parts.append(logo_bytes)
                            parts.append(b"\n\n")
            except Exception:
                self.logger.exception("Error generando bytes de logo desde %s", str(logo_path))

        # 3) Normalizar saltos de línea y codificar
        if text is None:
            text = ""

        # Normalize CR/LF to LF
        normalized = text.replace("\r\n", "\n").replace("\r", "\n")
        if not normalized.endswith("\n"):
            normalized += "\n"

        try:
            # Codificar línea a línea para permitir aplicar estilos a líneas específicas
            # Evitar línea vacía final innecesaria
            lines = normalized.rstrip("\n").split("\n")
            for idx, line in enumerate(lines):
                # Construir la línea con salto explícito
                line_with_newline = line + "\n"
                stripped = line.strip()
                if stripped.startswith("TOTAL:"):
                    # Separador visual fuerte
                    separator = "*" * 42
                    parts.append((separator + "\n").encode(self.encoding))
                    # Centrar, doble tamaño y negrita para la línea TOTAL
                    parts.append(self.ESC + b"a" + b"\x01")
                    parts.append(self._set_bold(True))
                    parts.append(self._set_double_size(True))
                    centered_line = line.strip().center(42)
                    try:
                        parts.append((centered_line + "\n").encode(self.encoding))
                    except Exception:
                        parts.append((centered_line + "\n").encode("utf-8", errors="replace"))
                    parts.append(self._set_double_size(False))
                    parts.append(self._set_bold(False))
                    parts.append(self.ESC + b"a" + b"\x00")
                elif stripped.startswith("SUBIDA DE NIVEL"):
                    parts.append(self._set_bold(True))
                    try:
                        parts.append(line_with_newline.encode(self.encoding))
                    except Exception:
                        parts.append(line_with_newline.encode("utf-8", errors="replace"))
                    parts.append(self._set_bold(False))
                else:
                    try:
                        parts.append(line_with_newline.encode(self.encoding))
                    except Exception:
                        parts.append(line_with_newline.encode("utf-8", errors="replace"))
        except Exception:
            # Fallback robusto: codificar todo como antes
            try:
                parts.append(normalized.encode(self.encoding))
            except Exception:
                parts.append(normalized.encode("utf-8", errors="replace"))

        # 4) Añadir una línea extra de separación (antes del corte)

        # Añadir QR si procede
        if qr_data:
            try:
                qr_bytes = self.render_qr_code(qr_data)
                if qr_bytes:
                    parts.append(b"\n")
                    parts.append(qr_bytes)
                    parts.append(b"\n")
            except Exception:
                self.logger.exception("Error añadiendo QR al ticket")

        # Espacio antes del corte físico
        parts.append(b"\n")
        parts.append(b"\n\n")

        # 4) Añadir comando de corte parcial (GS V 1)
        if cut:
            try:
                # GS 'V' m -> use m=1 (partial cut)
                parts.append(self.GS + b"V" + b"\x01")
            except Exception:
                self.logger.exception("Error añadiendo comando de corte ESC/POS")
        result = b"".join(parts)

        # Si debug_dump está activado, volcar el binario a disco antes de devolverlo
        if self.debug_dump:
            try:
                dump_dir = self.dump_directory or Path("./debug_escpos")
                dump_dir.mkdir(parents=True, exist_ok=True)
                ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                fname = f"ticket_{ts}.bin"
                path = dump_dir / fname
                with open(path, "wb") as fh:
                    fh.write(result)
                self.logger.info("ESC/POS dump guardado en: %s", str(path))
            except Exception:
                self.logger.exception("Error guardando ESC/POS dump en disco")

        return result

    def render_qr_code(self, data: str, size: int = 6) -> bytes:
        """Genera QR Code usando comandos ESC/POS nativos.

        Args:
            data: texto/URL a codificar
            size: tamaño módulo (1-16, recomendado 6-8)

        Returns:
            bytes con comandos ESC/POS para imprimir QR
        """
        if not data or not data.strip():
            return b""

        try:
            parts = []

            # Centrar QR
            parts.append(self.ESC + b"a" + b"\x01")

            # GS ( k - QR Code commands
            # Using printer-native commands (cn=49)
            cn = 49

            # Store data: fn=80 (0x50)
            payload = data.encode('utf-8')
            pL = (len(payload) + 3) & 0xFF
            pH = (len(payload) + 3) >> 8
            store_cmd = self.GS + b"(k" + bytes([pL, pH, cn, 80, 0]) + payload
            parts.append(store_cmd)

            # Set module size (fn=67)
            size_val = max(1, min(16, int(size)))
            size_cmd = self.GS + b"(k" + b"\x03\x00" + bytes([cn, 67, size_val])
            parts.append(size_cmd)

            # Set error correction level - 48 => M
            ec_cmd = self.GS + b"(k" + b"\x03\x00" + bytes([cn, 69, 48])
            parts.append(ec_cmd)

            # Print QR (fn=81)
            print_cmd = self.GS + b"(k" + b"\x03\x00" + bytes([cn, 81, 48])
            parts.append(print_cmd)

            # Reset alignment
            parts.append(self.ESC + b"a" + b"\x00")

            return b"".join(parts)

        except Exception:
            self.logger.exception("Error generando QR code")
            return b""

    def _set_codepage_cp858(self) -> bytes:
        """Secuencia ESC/POS para seleccionar codepage CP858 (con soporte €).

        Utiliza `ESC t 19` (0x13) que en muchas impresoras corresponde a CP858.
        Devuelve los bytes a insertar justo después de `ESC @`.
        """
        try:
            # ESC t n  -> select character code table n (19 -> CP858 en muchas máquinas)
            return self.ESC + b"t" + b"\x13"
        except Exception:
            self.logger.exception("No se pudo construir secuencia ESC t 19 (CP858)")
            return b""

    def _set_bold(self, enable: bool) -> bytes:
        return self.ESC + b"E" + (b"\x01" if enable else b"\x00")

    def _set_double_size(self, enable: bool) -> bytes:
        # GS ! n  (n=0 normal, n=0x11 doble ancho y alto)
        return self.GS + b"!" + (b"\x11" if enable else b"\x00")

    def render_logo_from_path(self, image_path: Path) -> bytes:
        """Genera bytes ESC/POS (raster GS v 0) desde una imagen en disco.

        - Convierte a escala de grises, redimensiona si ancho > 576 px,
          aplica umbral a 1-bit, empaqueta en formato raster ESC/POS (m=0)
        - Centrado por medio del comando `ESC a 1` antes del raster y
          `ESC a 0` después.
        - No realiza envío a impresora; solo devuelve los bytes.
        """
        try:
            from PIL import Image
        except Exception:
            self.logger.exception("Pillow no está disponible para renderizar logo")
            return b""

        try:
            img_path = Path(image_path)
            if not img_path.exists():
                self.logger.warning("Logo no encontrado: %s", str(img_path))
                return b""

            img = Image.open(img_path).convert("L")

            max_width = 576
            width, height = img.size
            if width > max_width:
                new_h = int((max_width / float(width)) * height)
                img = img.resize((max_width, new_h), Image.LANCZOS)
                width, height = img.size

            # Convertir a modo 1 (1-bit) usando dithering de PIL (mejor para térmicas)
            img = img.convert("1")

            # Preparar datos raster
            bytes_per_row = (width + 7) // 8
            raster_data = bytearray()
            for y in range(height):
                byte = 0
                bits_filled = 0
                for x in range(width):
                    pixel = img.getpixel((x, y))
                    # En modo '1' de PIL los valores son 0 (negro) o 255 (blanco)
                    bit = 1 if pixel == 0 else 0
                    byte = (byte << 1) | bit
                    bits_filled += 1
                    if bits_filled == 8:
                        raster_data.append(byte & 0xFF)
                        byte = 0
                        bits_filled = 0
                # padding remaining bits (if width not multiple of 8)
                if bits_filled > 0:
                    byte = byte << (8 - bits_filled)
                    raster_data.append(byte & 0xFF)

            xL = bytes_per_row & 0xFF
            xH = (bytes_per_row >> 8) & 0xFF
            yL = height & 0xFF
            yH = (height >> 8) & 0xFF

            # GS v 0 m xL xH yL yH [data]
            m = 0
            header = self.GS + b"v" + b"0" + bytes([m, xL, xH, yL, yH])

            # Centering via ESC a 1 ... ESC a 0
            centered = self.ESC + b"a" + b"\x01" + header + bytes(raster_data) + self.ESC + b"a" + b"\x00"
            return centered
        except Exception:
            self.logger.exception("Error procesando imagen para logo: %s", str(image_path))
            return b""

    # Preparado para futuras extensiones (no implementadas)
    def add_logo(self, image_bytes: bytes) -> None:  # pragma: no cover - placeholder
        """Placeholder para añadir logo (implementación futura)."""
        raise NotImplementedError()

    def set_bold(self, enable: bool) -> None:  # pragma: no cover - placeholder
        """Placeholder para activar/desactivar bold (implementación futura)."""
        raise NotImplementedError()

    def set_double_height(self, enable: bool) -> None:  # pragma: no cover - placeholder
        """Placeholder para doble altura."""
        raise NotImplementedError()
