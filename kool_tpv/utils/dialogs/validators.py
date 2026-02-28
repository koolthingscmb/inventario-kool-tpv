"""Validadores reutilizables para InputDialog.

Contienen comprobaciones robustas y anotaciones de tipo. Se prioriza
`Decimal` para comprobaciones monetarias y `datetime.strptime` para fecha.
"""
from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from datetime import datetime
from email.utils import parseaddr
from typing import Optional


def validate_numeric(value: Optional[str]) -> bool:
    """Valida que sea un número válido (entero o decimal).

    Usa Decimal para aceptar formatos numéricos más amplios (incluye notación
    científica). No acepta separadores de miles.
    """
    try:
        if value is None:
            return False
        s = str(value).strip()
        if s == "":
            return False
        Decimal(s)
        return True
    except (InvalidOperation, ValueError, AttributeError):
        return False


def validate_decimal(value: Optional[str], decimals: int = 2) -> bool:
    """Valida formato monetario con hasta `decimals` decimales.

    Se utiliza la representación interna de Decimal para contar decimales
    de forma precisa (gestiona notación científica).
    """
    try:
        if value is None:
            return False
        s = str(value).strip()
        if s == "":
            return False
        d = Decimal(s)
        # d.as_tuple().exponent es negativo cuando hay decimales
        exp = d.as_tuple().exponent
        decimals_count = -exp if exp < 0 else 0
        return decimals_count <= int(decimals)
    except (InvalidOperation, ValueError, AttributeError):
        return False


def validate_email(value: Optional[str]) -> bool:
    """Validación básica de email.

    Usa `email.utils.parseaddr` para extraer la dirección y una regex simple
    para validar el formato local/domain.tld. Es intencionadamente liviana
    (adecuada para validación UI), no para validación exhaustiva de RFC.
    """
    try:
        if value is None:
            return False
        val = str(value).strip()
        if val == "":
            return False
        _, addr = parseaddr(val)
        if not addr or "@" not in addr:
            return False
        pattern = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
        return bool(re.match(pattern, addr))
    except Exception:
        return False


def validate_min_length(value: Optional[str], min_len: int = 1) -> bool:
    """Valida longitud mínima (ignora espacios al inicio/fin)."""
    try:
        if value is None:
            return False
        return len(str(value).strip()) >= int(min_len)
    except Exception:
        return False


def validate_date(value: Optional[str]) -> bool:
    """Valida formato y fecha real `YYYY-MM-DD` usando datetime.

    Evita falsos positivos que una regex sencilla podría aceptar (por ejemplo,
    2026-02-31).
    """
    try:
        if value is None:
            return False
        s = str(value).strip()
        if s == "":
            return False
        datetime.strptime(s, "%Y-%m-%d")
        return True
    except (ValueError, TypeError, AttributeError):
        return False


def validate_not_empty(value: Optional[str]) -> bool:
    """Valida que no esté vacío (después de strip)."""
    try:
        if value is None:
            return False
        return bool(str(value).strip())
    except Exception:
        return False


__all__ = [
    "validate_numeric",
    "validate_decimal",
    "validate_email",
    "validate_min_length",
    "validate_date",
    "validate_not_empty",
]
