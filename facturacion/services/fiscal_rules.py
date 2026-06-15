"""Central fiscal calculation rules for invoices and sales."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings


MONEY_QUANT = Decimal("0.01")


@dataclass(frozen=True)
class FiscalTotals:
    subtotal: Decimal
    taxable_base: Decimal
    discount: Decimal
    tax: Decimal
    total: Decimal
    itbis_rate: Decimal


class FiscalCalculationService:
    """Single backend source of truth for fiscal totals."""

    def default_itbis_rate(self) -> Decimal:
        return Decimal(str(getattr(settings, "ECF_DEFAULT_ITBIS_RATE", "18.00"))).quantize(MONEY_QUANT)

    def calculate_invoice_totals(self, subtotal, discount=Decimal("0.00"), apply_itbis=True) -> FiscalTotals:
        subtotal = self.money(subtotal)
        discount = min(self.money(discount), subtotal)
        taxable_base = max(subtotal - discount, Decimal("0.00"))
        rate = self.default_itbis_rate() if self._bool(apply_itbis) else Decimal("0.00")
        tax = self.money(taxable_base * (rate / Decimal("100.00")))
        total = self.money(taxable_base + tax)
        return FiscalTotals(
            subtotal=subtotal,
            taxable_base=taxable_base,
            discount=discount,
            tax=tax,
            total=total,
            itbis_rate=rate,
        )

    def money(self, value) -> Decimal:
        if value is None or value == "":
            value = Decimal("0.00")
        return Decimal(str(value)).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)

    def _bool(self, value) -> bool:
        if isinstance(value, str):
            return value.lower() not in ("false", "0", "no", "off")
        return bool(value)
