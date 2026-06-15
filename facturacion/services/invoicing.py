"""Transactional invoice creation and fiscal automation services."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from facturacion.ecf.exceptions import ECFCeleryUnavailable
from facturacion.ecf.queues import enqueue_submission_pipeline
from facturacion.ecf.services.document_factory import ECFDocumentFactoryService
from facturacion.models import Client, Company, ECFEventLog, ElectronicFiscalDocument, Invoice, InvoiceDetail, Product, Sale, SaleDetail
from facturacion.services.fiscal_rules import FiscalCalculationService


@dataclass(frozen=True)
class InvoiceCreationResult:
    invoice: Invoice
    electronic_document: ElectronicFiscalDocument | None
    ecf_enqueued: bool
    ecf_error: str | None = None


@dataclass(frozen=True)
class SaleInvoiceCreationResult:
    sale: Sale
    invoice: Invoice
    electronic_document: ElectronicFiscalDocument | None
    ecf_enqueued: bool
    ecf_error: str | None = None


class InvoiceCreationService:
    """Create invoices, mutate stock, and start the e-CF pipeline after commit."""

    def __init__(
        self,
        document_factory: ECFDocumentFactoryService | None = None,
        fiscal_calculator: FiscalCalculationService | None = None,
    ) -> None:
        self.document_factory = document_factory or ECFDocumentFactoryService()
        self.fiscal_calculator = fiscal_calculator or FiscalCalculationService()

    def create_invoice(
        self,
        *,
        client_id: int | None,
        details: list[dict],
        payment_method: str = "cash",
        receipt_type: str = "invoice",
        status: str = "pending",
        subtotal: Decimal | float | str | None = None,
        tax: Decimal | float | str | None = None,
        discount: Decimal | float | str | None = None,
        total: Decimal | float | str | None = None,
        cash_received: Decimal | float | str | None = None,
        change: Decimal | float | str | None = None,
        notes: str | None = None,
        user=None,
        auto_ecf: bool | None = None,
        issuer_id: int | None = None,
        ecf_type: str | None = None,
        decrement_stock: bool = True,
        company: Company | None = None,
        apply_itbis: bool = True,
    ) -> InvoiceCreationResult:
        auto_ecf_enabled = getattr(settings, "ECF_AUTO_CREATE_ENABLED", True) if auto_ecf is None else self._bool(auto_ecf)
        enqueue_enabled = getattr(settings, "ECF_AUTO_ENQUEUE_ENABLED", True)
        ecf_error = None
        electronic_document = None

        with transaction.atomic():
            invoice = self._create_invoice_record(
                client_id=client_id,
                details=details,
                payment_method=payment_method,
                receipt_type=receipt_type,
                status=status,
                subtotal=subtotal,
                tax=tax,
                discount=discount,
                total=total,
                cash_received=cash_received,
                change=change,
                notes=notes,
                decrement_stock=decrement_stock,
                company=company,
                apply_itbis=apply_itbis,
            )

            if auto_ecf_enabled and self._should_create_ecf(invoice):
                factory_result = self.document_factory.create_for_invoice(
                    invoice,
                    user=user,
                    issuer_id=issuer_id,
                    ecf_type=ecf_type,
                )
                electronic_document = factory_result.document
                ecf_error = factory_result.error
                if ecf_error:
                    raise ValueError(ecf_error)
                if electronic_document and enqueue_enabled:
                    transaction.on_commit(
                        lambda document_id=electronic_document.id, user_id=getattr(user, "id", None): self._enqueue_after_commit(document_id, user_id)
                    )

        invoice.refresh_from_db()
        if electronic_document:
            electronic_document.refresh_from_db()
        return InvoiceCreationResult(
            invoice=invoice,
            electronic_document=electronic_document,
            ecf_enqueued=bool(electronic_document and enqueue_enabled and not ecf_error),
            ecf_error=ecf_error,
        )

    def collect_and_issue_invoice(
        self,
        *,
        invoice_id: int,
        user=None,
        issuer_id: int | None = None,
        ecf_type: str | None = None,
    ) -> InvoiceCreationResult:
        """Collect a manual invoice, commit inventory once, and start e-CF emission."""
        enqueue_enabled = getattr(settings, "ECF_AUTO_ENQUEUE_ENABLED", True)
        electronic_document = None
        ecf_error = None

        with transaction.atomic():
            invoice = (
                Invoice.objects.select_for_update()
                .select_related("company")
                .get(pk=invoice_id)
            )
            existing_document = getattr(invoice, "electronic_document", None)
            if existing_document:
                raise ValueError("La factura ya tiene e-CF generado y no puede cobrarse nuevamente desde este flujo.")

            if invoice.status in ("cancelled", "refunded"):
                raise ValueError("No se puede cobrar una factura anulada o reembolsada.")

            if invoice.inventory_committed_at is None:
                self._commit_invoice_inventory(invoice)
                invoice.inventory_committed_at = timezone.now()

            invoice.status = "paid"
            invoice.save(update_fields=["status", "inventory_committed_at", "updated_at"])

            if self._should_create_ecf(invoice):
                factory_result = self.document_factory.create_for_invoice(
                    invoice,
                    user=user,
                    issuer_id=issuer_id,
                    ecf_type=ecf_type,
                )
                electronic_document = factory_result.document
                ecf_error = factory_result.error
                if ecf_error:
                    raise ValueError(ecf_error)
                if electronic_document and enqueue_enabled:
                    transaction.on_commit(
                        lambda document_id=electronic_document.id, user_id=getattr(user, "id", None): self._enqueue_after_commit(document_id, user_id)
                    )

        invoice.refresh_from_db()
        if electronic_document:
            electronic_document.refresh_from_db()
        return InvoiceCreationResult(
            invoice=invoice,
            electronic_document=electronic_document,
            ecf_enqueued=bool(electronic_document and enqueue_enabled and not ecf_error),
            ecf_error=ecf_error,
        )

    def create_sale_with_invoice(
        self,
        *,
        customer: str | None,
        details: list[dict],
        client_id: int | None = None,
        user=None,
        issuer_id: int | None = None,
        ecf_type: str | None = None,
        company: Company | None = None,
    ) -> SaleInvoiceCreationResult:
        auto_ecf_enabled = getattr(settings, "ECF_AUTO_CREATE_ENABLED", True)
        enqueue_enabled = getattr(settings, "ECF_AUTO_ENQUEUE_ENABLED", True)
        electronic_document = None
        ecf_error = None

        with transaction.atomic():
            client_queryset = Client.objects.all()
            if company:
                client_queryset = client_queryset.filter(company=company)
            client = client_queryset.filter(pk=client_id).first() if client_id else None
            display_customer = (customer or getattr(client, "name", None) or "Consumidor Final").strip()
            fiscal_ecf_type = ecf_type or ("31" if client and client.ruc_ci else "32")
            invoice = self._create_invoice_record(
                client_id=getattr(client, "id", None),
                details=details,
                payment_method="cash",
                receipt_type="invoice",
                status="paid",
                subtotal=None,
                tax=None,
                discount=Decimal("0.00"),
                total=None,
                cash_received=None,
                change=Decimal("0.00"),
                notes=f"Venta POS: {display_customer}",
                decrement_stock=True,
                company=company,
                apply_itbis=True,
            )
            sale = Sale.objects.create(customer=display_customer, total=invoice.subtotal)
            SaleDetail.objects.bulk_create(
                [
                    SaleDetail(
                        sale=sale,
                        product=detail.product,
                        quantity=detail.quantity,
                        price=detail.price,
                    )
                    for detail in invoice.details.select_related("product").all()
                ]
            )

            if auto_ecf_enabled:
                factory_result = self.document_factory.create_for_invoice(
                    invoice,
                    user=user,
                    issuer_id=issuer_id,
                    ecf_type=fiscal_ecf_type,
                )
                electronic_document = factory_result.document
                ecf_error = factory_result.error
                if ecf_error:
                    raise ValueError(ecf_error)
                if electronic_document and enqueue_enabled:
                    transaction.on_commit(
                        lambda document_id=electronic_document.id, user_id=getattr(user, "id", None): self._enqueue_after_commit(document_id, user_id)
                    )

        sale.refresh_from_db()
        invoice.refresh_from_db()
        if electronic_document:
            electronic_document.refresh_from_db()
        return SaleInvoiceCreationResult(
            sale=sale,
            invoice=invoice,
            electronic_document=electronic_document,
            ecf_enqueued=bool(electronic_document and enqueue_enabled and not ecf_error),
            ecf_error=ecf_error,
        )

    def _create_invoice_record(
        self,
        *,
        client_id: int | None,
        details: list[dict],
        payment_method: str,
        receipt_type: str,
        status: str,
        subtotal,
        tax,
        discount,
        total,
        cash_received,
        change,
        notes,
        decrement_stock: bool,
        company: Company | None,
        apply_itbis: bool,
    ) -> Invoice:
        company = self._resolve_company(client_id=client_id, details=details, company=company)
        client_queryset = Client.objects.all()
        client_queryset = client_queryset.filter(company=company)
        client = client_queryset.filter(pk=client_id).first() if client_id else None
        normalized_details = self._lock_and_normalize_details(details, decrement_stock=decrement_stock, company=company)

        calculated_subtotal = sum(item["subtotal"] for item in normalized_details)
        invoice_subtotal = self._money(subtotal, calculated_subtotal)
        fiscal_totals = self.fiscal_calculator.calculate_invoice_totals(
            subtotal=invoice_subtotal,
            discount=self._money(discount, Decimal("0.00")),
            apply_itbis=apply_itbis,
        )

        invoice = Invoice.objects.create(
            company=company,
            client=client,
            subtotal=fiscal_totals.subtotal,
            tax=fiscal_totals.tax,
            discount=fiscal_totals.discount,
            total=fiscal_totals.total,
            cash_received=self._money(cash_received, Decimal("0.00")),
            change=self._money(change, Decimal("0.00")),
            payment_method=payment_method,
            receipt_type=receipt_type,
            status=status,
            inventory_committed_at=timezone.now() if decrement_stock else None,
            notes=notes,
        )

        InvoiceDetail.objects.bulk_create(
            [
                InvoiceDetail(
                    invoice=invoice,
                    product=item["product"],
                    quantity=item["quantity"],
                    price=item["price"],
                    subtotal=item["subtotal"],
                )
                for item in normalized_details
            ]
        )
        return invoice

    def _lock_and_normalize_details(self, details: list[dict], decrement_stock: bool, company: Company | None) -> list[dict]:
        if not details:
            raise ValueError("Debe incluir al menos un producto.")
        normalized = []
        product_ids = [self._product_id(detail) for detail in details]
        product_queryset = Product.objects.select_for_update().filter(id__in=product_ids)
        if company:
            product_queryset = product_queryset.filter(company=company)
        products = {product.id: product for product in product_queryset}

        for detail in details:
            product_id = self._product_id(detail)
            product = products.get(product_id)
            if not product:
                raise ValueError(f"Producto ID {product_id} no existe.")
            quantity = int(detail.get("quantity") or 0)
            if quantity <= 0:
                raise ValueError("La cantidad debe ser mayor a cero.")
            if decrement_stock and product.stock < quantity:
                raise ValueError(f"Stock insuficiente para '{product.name}'. Disponible: {product.stock}, Solicitado: {quantity}.")
            price = self._money(detail.get("price", product.price), product.price)
            normalized.append(
                {
                    "product": product,
                    "quantity": quantity,
                    "price": price,
                    "subtotal": price * quantity,
                }
            )

        if decrement_stock:
            for item in normalized:
                Product.objects.filter(pk=item["product"].pk).update(stock=F("stock") - item["quantity"])
        return normalized

    def _commit_invoice_inventory(self, invoice: Invoice) -> None:
        details = list(
            invoice.details.select_related("product")
            .select_for_update()
            .all()
        )
        if not details:
            raise ValueError("La factura no tiene productos para cobrar.")

        product_ids = [detail.product_id for detail in details]
        products = {
            product.id: product
            for product in Product.objects.select_for_update().filter(
                id__in=product_ids,
                company=invoice.company,
            )
        }

        for detail in details:
            product = products.get(detail.product_id)
            if not product:
                raise ValueError("La factura contiene productos que no pertenecen a la empresa activa.")
            if product.stock < detail.quantity:
                raise ValueError(
                    f"Stock insuficiente para '{product.name}'. Disponible: {product.stock}, Solicitado: {detail.quantity}."
                )

        for detail in details:
            Product.objects.filter(pk=detail.product_id, company=invoice.company).update(
                stock=F("stock") - detail.quantity
            )

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
            raise ValueError("Debe seleccionar una empresa para crear la factura.")
        raise ValueError("Los productos o cliente pertenecen a empresas diferentes.")

    def _product_id(self, detail: dict) -> int:
        product = detail.get("product") or detail.get("product_id")
        return product.id if hasattr(product, "id") else int(product)

    def _money(self, value, default=Decimal("0.00")) -> Decimal:
        if value is None or value == "":
            return Decimal(str(default)).quantize(Decimal("0.01"))
        return Decimal(str(value)).quantize(Decimal("0.01"))

    def _bool(self, value) -> bool:
        if isinstance(value, str):
            return value.lower() not in ("false", "0", "no", "off")
        return bool(value)

    def _should_create_ecf(self, invoice: Invoice) -> bool:
        eligible_statuses = set(getattr(settings, "ECF_AUTO_CREATE_INVOICE_STATUSES", ("paid", "pending")))
        return invoice.receipt_type == "invoice" and invoice.status in eligible_statuses

    def _enqueue_after_commit(self, document_id: int, user_id: int | None) -> None:
        try:
            enqueue_submission_pipeline(document_id, user_id=user_id)
        except ECFCeleryUnavailable as exc:
            document = ElectronicFiscalDocument.objects.filter(pk=document_id).first()
            if document:
                document.last_error = str(exc)
                document.save(update_fields=["last_error", "updated_at"])
                ECFEventLog.objects.create(
                    electronic_document=document,
                    event_type="error",
                    message="No fue posible encolar el pipeline e-CF automaticamente.",
                    payload={"stage": "auto_enqueue", "error": str(exc)},
                )
