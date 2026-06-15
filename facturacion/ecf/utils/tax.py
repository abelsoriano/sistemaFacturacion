"""Tax calculation helpers for e-CF XML generation."""

from decimal import Decimal

from django.conf import settings

from facturacion.ecf.constants import (
    ITBIS_INDICATOR_16,
    ITBIS_INDICATOR_18,
    ITBIS_INDICATOR_0,
    ITBIS_INDICATOR_EXEMPT,
    ITBIS_RATE_16,
    ITBIS_RATE_18,
    ITBIS_RATE_0,
)
from facturacion.ecf.utils.decimals import quantize_money


def infer_itbis_rate(subtotal: Decimal, tax: Decimal) -> Decimal:
    """Infer the ITBIS rate from invoice totals."""
    subtotal = quantize_money(subtotal)
    tax = quantize_money(tax)
    if subtotal <= 0 or tax <= 0:
        return ITBIS_RATE_0

    rate = (tax / subtotal * Decimal("100")).quantize(Decimal("0.01"))
    if abs(rate - ITBIS_RATE_18) <= Decimal("0.25"):
        return ITBIS_RATE_18
    if abs(rate - ITBIS_RATE_16) <= Decimal("0.25"):
        return ITBIS_RATE_16

    configured_rate = getattr(settings, "ECF_DEFAULT_ITBIS_RATE", "18.00")
    return Decimal(str(configured_rate)).quantize(Decimal("0.01"))


def indicator_for_rate(rate: Decimal, taxable: bool = True) -> str:
    """Map an ITBIS rate to DGII IndicadorFacturacion."""
    if not taxable:
        return ITBIS_INDICATOR_EXEMPT
    if rate == ITBIS_RATE_18:
        return ITBIS_INDICATOR_18
    if rate == ITBIS_RATE_16:
        return ITBIS_INDICATOR_16
    if rate == ITBIS_RATE_0:
        return ITBIS_INDICATOR_0
    return ITBIS_INDICATOR_18


def taxable_base_from_total(subtotal: Decimal, discount: Decimal) -> Decimal:
    """Calculate the taxable base before ITBIS."""
    value = quantize_money(subtotal) - quantize_money(discount)
    return max(value, Decimal("0.00"))

