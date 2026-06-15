"""Commercial quotation services."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from facturacion.models import Client, Company, Invoice, Quotation, QuotationDetail, Product
from facturacion.services.fiscal_rules import FiscalCalculationService
from facturacion.services.invoicing import InvoiceCreationService


@dataclass(frozen=True)
class QuotationCreationResult:
    quotation: Quotation


@dataclass(frozen=True)
class QuotationConversionResult:
    quotation: Quotation
    invoice: Invoice
    electronic_document: object | None
    ecf_enqueued: bool
    ecf_error: str | None = None


class QuotationService:
    """Create and transition non-fiscal commercial estimates."""

    terminal_statuses = {"rejected", "expired"}

    def __init__(self, fiscal_calculator: FiscalCalculationService | None = None) -> None:
        self.fiscal_calculator = fiscal_calculator or FiscalCalculationService()

    @transaction.atomic
    def create_quotation(
        self,
        *,
        client_id: int | None,
        customer_name: str | None,
        details: list[dict],
        discount: Decimal | float | str | None = None,
        notes: str | None = None,
        valid_until=None,
        user=None,
        company: Company | None = None,
        apply_itbis: bool = True,
    ) -> QuotationCreationResult:
        if not details:
            raise ValueError("Debe incluir al menos un producto.")

        company = self._resolve_company(client_id=client_id, details=details, company=company)
        client_queryset = Client.objects.all()
        client_queryset = client_queryset.filter(company=company)
        client = client_queryset.filter(pk=client_id).first() if client_id else None
        normalized = self._normalize_details(details, company=company)
        subtotal = sum(item["subtotal"] for item in normalized)
        totals = self.fiscal_calculator.calculate_invoice_totals(
            subtotal,
            discount or Decimal("0.00"),
            apply_itbis=apply_itbis,
        )

        quotation = Quotation.objects.create(
            company=company,
            client=client,
            customer_name=customer_name,
            subtotal=totals.subtotal,
            tax=totals.tax,
            discount=totals.discount,
            total=totals.total,
            notes=notes,
            valid_until=valid_until,
            created_by=user,
        )
        QuotationDetail.objects.bulk_create(
            [
                QuotationDetail(
                    quotation=quotation,
                    product=item["product"],
                    quantity=item["quantity"],
                    price=item["price"],
                    subtotal=item["subtotal"],
                )
                for item in normalized
            ]
        )
        return QuotationCreationResult(quotation=quotation)

    @transaction.atomic
    def update_quotation(self, quotation: Quotation, *, data: dict, user=None) -> Quotation:
        locked = Quotation.objects.select_for_update().get(pk=quotation.pk)
        if locked.converted_at:
            raise ValueError("No se puede modificar una cotizacion ya convertida a factura.")
        if locked.status not in {"draft", "sent"}:
            raise ValueError("Solo cotizaciones en borrador o enviadas pueden modificarse.")

        details = data.pop("details", None)
        client_id = data.pop("client_id", None)
        client = data.pop("client", None)
        has_apply_itbis = "apply_itbis" in data
        apply_itbis = data.pop("apply_itbis", locked.tax > 0)
        if client_id or client:
            client_queryset = Client.objects.all()
            if locked.company_id:
                client_queryset = client_queryset.filter(company_id=locked.company_id)
            locked.client = client_queryset.filter(pk=client_id or getattr(client, "id", client)).first()
        for field in ("customer_name", "notes", "valid_until"):
            if field in data:
                setattr(locked, field, data[field])

        if details is not None:
            normalized = self._normalize_details(details, company=locked.company)
            subtotal = sum(item["subtotal"] for item in normalized)
            totals = self.fiscal_calculator.calculate_invoice_totals(
                subtotal,
                data.get("discount", locked.discount),
                apply_itbis=apply_itbis,
            )
            locked.subtotal = totals.subtotal
            locked.tax = totals.tax
            locked.discount = totals.discount
            locked.total = totals.total
            locked.details.all().delete()
            QuotationDetail.objects.bulk_create(
                [
                    QuotationDetail(
                        quotation=locked,
                        product=item["product"],
                        quantity=item["quantity"],
                        price=item["price"],
                        subtotal=item["subtotal"],
                    )
                    for item in normalized
                ]
            )
        elif "discount" in data:
            totals = self.fiscal_calculator.calculate_invoice_totals(
                locked.subtotal,
                data["discount"],
                apply_itbis=apply_itbis,
            )
            locked.tax = totals.tax
            locked.discount = totals.discount
            locked.total = totals.total
        elif has_apply_itbis:
            totals = self.fiscal_calculator.calculate_invoice_totals(
                locked.subtotal,
                locked.discount,
                apply_itbis=apply_itbis,
            )
            locked.tax = totals.tax
            locked.total = totals.total

        locked.save()
        return locked

    @transaction.atomic
    def mark_sent(self, quotation_id: int) -> Quotation:
        quotation = Quotation.objects.select_for_update().get(pk=quotation_id)
        self._assert_not_expired_by_date(quotation)
        if quotation.status not in {"draft", "sent"}:
            raise ValueError("Solo cotizaciones en borrador pueden enviarse.")
        quotation.status = "sent"
        quotation.sent_at = quotation.sent_at or timezone.now()
        quotation.save(update_fields=["status", "sent_at", "updated_at"])
        return quotation

    @transaction.atomic
    def approve(self, quotation_id: int) -> Quotation:
        quotation = Quotation.objects.select_for_update().get(pk=quotation_id)
        self._assert_not_expired_by_date(quotation)
        if quotation.status in self.terminal_statuses:
            raise ValueError("No se puede aprobar una cotizacion rechazada o expirada.")
        quotation.status = "approved"
        quotation.approved_at = timezone.now()
        quotation.save(update_fields=["status", "approved_at", "updated_at"])
        return quotation

    @transaction.atomic
    def reject(self, quotation_id: int) -> Quotation:
        quotation = Quotation.objects.select_for_update().get(pk=quotation_id)
        if quotation.converted_at:
            raise ValueError("No se puede rechazar una cotizacion ya convertida.")
        quotation.status = "rejected"
        quotation.rejected_at = timezone.now()
        quotation.save(update_fields=["status", "rejected_at", "updated_at"])
        return quotation

    @transaction.atomic
    def expire(self, quotation_id: int) -> Quotation:
        quotation = Quotation.objects.select_for_update().get(pk=quotation_id)
        if quotation.converted_at:
            raise ValueError("No se puede expirar una cotizacion ya convertida.")
        quotation.status = "expired"
        quotation.expired_at = timezone.now()
        quotation.save(update_fields=["status", "expired_at", "updated_at"])
        return quotation

    @transaction.atomic
    def convert_to_invoice(
        self,
        *,
        quotation_id: int,
        user=None,
        payment_method: str = "cash",
        status: str = "pending",
        cash_received=None,
        change=None,
        issuer_id: int | None = None,
        ecf_type: str | None = None,
    ) -> QuotationConversionResult:
        quotation = Quotation.objects.select_for_update().prefetch_related("details__product").get(pk=quotation_id)
        self._assert_not_expired_by_date(quotation)
        if quotation.converted_at:
            raise ValueError("La cotizacion ya fue convertida a factura.")
        if quotation.status != "approved":
            raise ValueError("Solo cotizaciones aprobadas pueden convertirse a factura.")

        details = [
            {"product": detail.product_id, "quantity": detail.quantity, "price": detail.price}
            for detail in quotation.details.all()
        ]
        result = InvoiceCreationService().create_invoice(
            client_id=quotation.client_id,
            details=details,
            payment_method=payment_method,
            receipt_type="invoice",
            status="pending",
            discount=quotation.discount,
            cash_received=None,
            change=None,
            notes=f"Convertida desde {quotation.quotation_number}. {quotation.notes or ''}".strip(),
            user=user,
            auto_ecf=False,
            issuer_id=issuer_id,
            ecf_type=ecf_type,
            decrement_stock=False,
            company=quotation.company,
            apply_itbis=quotation.tax > 0,
        )
        invoice = result.invoice
        invoice.origin_quotation = quotation
        invoice.save(update_fields=["origin_quotation", "updated_at"])
        quotation.converted_at = timezone.now()
        quotation.save(update_fields=["converted_at", "updated_at"])
        quotation.refresh_from_db()
        invoice.refresh_from_db()
        return QuotationConversionResult(
            quotation=quotation,
            invoice=invoice,
            electronic_document=result.electronic_document,
            ecf_enqueued=result.ecf_enqueued,
            ecf_error=result.ecf_error,
        )

    def _normalize_details(self, details: list[dict], company: Company | None = None) -> list[dict]:
        product_ids = [self._product_id(detail) for detail in details]
        product_queryset = Product.objects.filter(id__in=product_ids)
        if company:
            product_queryset = product_queryset.filter(company=company)
        products = {product.id: product for product in product_queryset}
        normalized = []
        for detail in details:
            product_id = self._product_id(detail)
            product = products.get(product_id)
            if not product:
                raise ValueError(f"Producto ID {product_id} no existe.")
            quantity = int(detail.get("quantity") or 0)
            if quantity <= 0:
                raise ValueError("La cantidad debe ser mayor a cero.")
            price = self.fiscal_calculator.money(detail.get("price", product.price))
            normalized.append(
                {
                    "product": product,
                    "quantity": quantity,
                    "price": price,
                    "subtotal": price * quantity,
                }
            )
        return normalized

    def _resolve_company(self, *, client_id: int | None, details: list[dict], company: Company | None) -> Company:
        if company:
            return company

        company_ids = set()
        if client_id:
            client_company_id = Client.objects.filter(pk=client_id).values_list("company_id", flat=True).first()
            if client_company_id:
                company_ids.add(client_company_id)

        product_ids = [self._product_id(detail) for detail in details]
        company_ids.update(
            Product.objects.filter(pk__in=product_ids).values_list("company_id", flat=True).distinct()
        )
        company_ids.discard(None)

        if len(company_ids) == 1:
            return Company.objects.get(pk=company_ids.pop())
        if not company_ids:
            raise ValueError("Debe seleccionar una empresa para crear la cotizacion.")
        raise ValueError("Los productos o cliente pertenecen a empresas diferentes.")

    def _product_id(self, detail: dict) -> int:
        product = detail.get("product") or detail.get("product_id")
        return product.id if hasattr(product, "id") else int(product)

    def _assert_not_expired_by_date(self, quotation: Quotation) -> None:
        if quotation.valid_until and quotation.valid_until < timezone.localdate():
            quotation.status = "expired"
            quotation.expired_at = quotation.expired_at or timezone.now()
            quotation.save(update_fields=["status", "expired_at", "updated_at"])
            raise ValueError("La cotizacion esta vencida y no puede avanzar de estado.")
