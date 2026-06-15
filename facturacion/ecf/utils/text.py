"""Text normalization helpers for DGII field limits."""

import re
from typing import Any


def clean_text(value: Any, max_length: int | None = None) -> str | None:
    """Normalize whitespace and truncate text to a DGII field length."""
    if value is None:
        return None
    text = re.sub(r"\s+", " ", str(value)).strip()
    if not text:
        return None
    if max_length:
        return text[:max_length]
    return text


def digits_only(value: Any) -> str | None:
    """Return only numeric characters from a value."""
    if value is None:
        return None
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    return digits or None


def dgii_phone(value: Any) -> str | None:
    """Format a Dominican phone number as NNN-NNN-NNNN when possible."""
    digits = digits_only(value)
    if not digits:
        return None
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) != 10:
        return None
    return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"


def dgii_location_code(value: Any) -> str | None:
    """Return a DGII province/municipality code only when it has the XSD shape."""
    digits = digits_only(value)
    if digits and len(digits) == 6:
        return digits
    return None
