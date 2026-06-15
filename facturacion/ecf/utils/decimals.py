"""Decimal formatting helpers for DGII XML values."""

from decimal import Decimal, ROUND_HALF_UP
from typing import Any


TWOPLACES = Decimal("0.01")
FOURPLACES = Decimal("0.0001")


def to_decimal(value: Any) -> Decimal:
    """Convert a value to Decimal without introducing binary float noise."""
    if value is None:
        return Decimal("0.00")
    return Decimal(str(value))


def quantize_money(value: Any) -> Decimal:
    """Round a monetary amount to two decimal places."""
    return to_decimal(value).quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def quantize_unit_price(value: Any) -> Decimal:
    """Round a unit price to four decimal places, accepted by DGII item price fields."""
    return to_decimal(value).quantize(FOURPLACES, rounding=ROUND_HALF_UP)


def format_money(value: Any) -> str:
    """Format a monetary amount for DGII XML."""
    return f"{quantize_money(value):.2f}"


def format_unit_price(value: Any) -> str:
    """Format an item unit price for DGII XML."""
    return f"{quantize_unit_price(value):.4f}"

