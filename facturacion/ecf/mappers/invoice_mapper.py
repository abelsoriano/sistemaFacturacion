"""Map Invoice models into a DGII-oriented e-CF payload."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from django.conf import settings

from facturacion.models import ElectronicFiscalDocument, InvoiceDetail
from facturacion.ecf.constants import PAYMENT_METHOD_TO_DGII
from facturacion.ecf.utils.dates import format_dgii_date, format_dgii_datetime
from facturacion.ecf.utils.decimals import quantize_money
from facturacion.ecf.utils.tax import infer_itbis_rate, indicator_for_rate, taxable_base_from_total
from facturacion.ecf.utils.text import clean_text, dgii_location_code, dgii_phone, digits_only


@dataclass(frozen=True)
class ECFPayload:
    """Normalized data required to serialize an e-CF XML document."""

    ecf_type: str
    encf: str
    issue_date: str
    signature_datetime: str
    sequence_expiration_date: str | None
    income_type: str
    payment_type: str
    payment_form: str
    credit_note_indicator: str | None
    issuer: dict[str, Any]
    buyer: dict[str, Any]
    totals: dict[str, Decimal]
    items: list[dict[str, Any]]
    internal_invoice_number: str
    modified_document: dict[str, Any] | None = None
    include_signature_placeholder: bool = True


class InvoiceECFMapper:
    """Build a stable e-CF payload from an ElectronicFiscalDocument."""

    def map(self, document: ElectronicFiscalDocument) -> ECFPayload:
        """Return a normalized e-CF payload for the document invoice."""
        source = document.credit_note if document.credit_note_id else document.invoice
        details = list(source.details.select_related("product").all())
        subtotal = quantize_money(source.subtotal)
        discount = quantize_money(source.discount)
        tax = quantize_money(source.tax)
        taxable_base = taxable_base_from_total(subtotal, discount)
        itbis_rate = infer_itbis_rate(taxable_base, tax)
        taxable = taxable_base > 0 and tax > 0
        indicator = indicator_for_rate(itbis_rate, taxable=taxable)

        return ECFPayload(
            ecf_type=document.ecf_type,
            encf=document.encf,
            issue_date=format_dgii_date(source.created_at),
            signature_datetime=format_dgii_datetime(),
            sequence_expiration_date=format_dgii_date(document.sequence.expiration_date),
            income_type=getattr(settings, "ECF_DEFAULT_INCOME_TYPE", "01"),
            payment_type=self._map_payment_type(getattr(source, "status", "paid")),
            payment_form=PAYMENT_METHOD_TO_DGII.get(getattr(source, "payment_method", "cash"), "8"),
            credit_note_indicator=self._map_credit_note_indicator(document),
            issuer=self._map_issuer(document),
            buyer=self._map_buyer(document),
            totals=self._map_totals(taxable_base, tax, source.total, itbis_rate, taxable),
            items=self._map_items(details, indicator, discount, subtotal),
            internal_invoice_number=clean_text(
                getattr(source, "invoice_number", None) or getattr(source, "credit_note_number", None),
                20,
            ) or str(source.id),
            modified_document=self._map_modified_document(document),
        )

    def _map_issuer(self, document: ElectronicFiscalDocument) -> dict[str, Any]:
        issuer = document.issuer
        return {
            "rnc": digits_only(issuer.rnc),
            "business_name": clean_text(issuer.business_name, 150),
            "trade_name": clean_text(issuer.trade_name, 150),
            "address": clean_text(issuer.address, 100),
            "municipality": dgii_location_code(issuer.municipality),
            "province": dgii_location_code(issuer.province),
            "phone": dgii_phone(issuer.phone),
            "email": clean_text(issuer.email, 80),
        }

    def _map_buyer(self, document: ElectronicFiscalDocument) -> dict[str, Any]:
        invoice = document.credit_note.origin_invoice if document.credit_note_id else document.invoice
        client = invoice.client
        if not client:
            return {}

        return {
            "rnc": digits_only(client.ruc_ci),
            "business_name": clean_text(client.name, 150),
            "email": clean_text(client.email, 80),
            "address": clean_text(client.address, 100),
            "phone": dgii_phone(client.phone),
        }

    def _map_totals(
        self,
        taxable_base: Decimal,
        tax: Decimal,
        total: Decimal,
        itbis_rate: Decimal,
        taxable: bool,
    ) -> dict[str, Decimal]:
        totals = {
            "amount_total": quantize_money(total),
            "total_itbis": tax,
            "itbis_rate": itbis_rate,
            "taxable_amount": taxable_base if taxable else Decimal("0.00"),
            "exempt_amount": Decimal("0.00") if taxable else taxable_base,
        }
        return totals

    def _map_items(
        self,
        details: list[InvoiceDetail],
        indicator: str,
        invoice_discount: Decimal,
        invoice_subtotal: Decimal,
    ) -> list[dict[str, Any]]:
        items = []
        discount_accumulator = Decimal("0.00")
        for index, detail in enumerate(details, start=1):
            product = detail.product
            line_subtotal = quantize_money(detail.subtotal)
            line_discount = self._line_discount(
                line_subtotal=line_subtotal,
                invoice_discount=invoice_discount,
                invoice_subtotal=invoice_subtotal,
                is_last_line=index == len(details),
                accumulated=discount_accumulator,
            )
            discount_accumulator += line_discount
            line_amount = max(line_subtotal - line_discount, Decimal("0.00"))
            items.append(
                {
                    "line_number": index,
                    "billing_indicator": indicator,
                    "name": clean_text(product.name, 80),
                    "description": clean_text(product.description, 1000),
                    "is_good_or_service": "1",
                    "quantity": quantize_money(detail.quantity),
                    "unit_price": detail.price,
                    "discount": line_discount,
                    "amount": line_amount,
                    "code": clean_text(product.barcode, 35),
                }
            )
        return items

    def _map_modified_document(self, document: ElectronicFiscalDocument) -> dict[str, Any] | None:
        if not document.credit_note_id:
            return None
        origin_invoice = document.credit_note.origin_invoice
        origin_document = getattr(origin_invoice, "electronic_document", None)
        return {
            "encf": getattr(origin_document, "encf", None),
            "issue_date": format_dgii_date(origin_invoice.created_at),
            "code": "1" if document.credit_note.reversal_type == "total" else "3",
            "reason": clean_text(document.credit_note.reason, 90),
        }

    def _map_credit_note_indicator(self, document: ElectronicFiscalDocument) -> str | None:
        if not document.credit_note_id:
            return None
        origin_date = document.credit_note.origin_invoice.created_at.date()
        note_date = document.credit_note.created_at.date() if document.credit_note.created_at else date.today()
        return "1" if (note_date - origin_date).days > 30 else "0"

    def _map_payment_type(self, invoice_status: str) -> str:
        if invoice_status == "paid":
            return "1"
        return "2"

    def _line_discount(
        self,
        line_subtotal: Decimal,
        invoice_discount: Decimal,
        invoice_subtotal: Decimal,
        is_last_line: bool,
        accumulated: Decimal,
    ) -> Decimal:
        if invoice_discount <= 0 or invoice_subtotal <= 0:
            return Decimal("0.00")
        if is_last_line:
            return max(quantize_money(invoice_discount - accumulated), Decimal("0.00"))
        return quantize_money(line_subtotal / invoice_subtotal * invoice_discount)
