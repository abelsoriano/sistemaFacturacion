"""Transactional credit note creation and fiscal reversal rules."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.db.models import F, Sum
from django.utils import timezone

from facturacion.ecf.exceptions import ECFCeleryUnavailable
from facturacion.ecf.queues import enqueue_submission_pipeline
from facturacion.ecf.services.document_factory import ECFDocumentFactoryService
from facturacion.models import Company, CreditNote, CreditNoteDetail, ECFEventLog, Invoice, InvoiceDetail, Product, ElectronicFiscalDocument


@dataclass(frozen=True)
class CreditNoteCreationResult:
    credit_note: CreditNote
    electronic_document: ElectronicFiscalDocument | None
    ecf_enqueued: bool = False
    ecf_error: str | None = None


class CreditNoteService:
    """Create E34 credit notes for partial or total reversals."""

    def __init__(self, document_factory: ECFDocumentFactoryService | None = None) -> None:
        self.document_factory = document_factory or ECFDocumentFactoryService()

    @transaction.atomic
    def create_credit_note(
        self,
        *,
        origin_invoice_id: int,
        details: list[dict] | None,
        reason: str,
        user=None,
        issuer_id: int | None = None,
        restore_inventory: bool = True,
        company: Company | None = None,
    ) -> CreditNoteCreationResult:
        enqueue_enabled = getattr(settings, "ECF_AUTO_ENQUEUE_ENABLED", True)
        ecf_error = None

        if not user or not (user.is_superuser or user.has_perm("facturacion.reverse_invoice")):
            raise ValueError("No tienes permiso para reversar facturas fiscalmente.")
        if not reason:
            raise ValueError("El motivo fiscal de la nota de credito es requerido.")

        invoice = (
            Invoice.objects
            .select_for_update()
            .prefetch_related("details")
            .get(pk=origin_invoice_id)
        )
        note_company = company or invoice.company
        if not note_company:
            raise ValueError("La factura origen no tiene empresa asociada.")
        if invoice.company_id != note_company.id:
            raise ValueError("La factura origen no pertenece a la empresa activa.")
        document = getattr(invoice, "electronic_document", None)
        if not document or document.fiscal_status != "accepted":
            raise ValueError("La factura origen debe tener e-CF aceptado por DGII para crear E34.")
        self._assert_no_unresolved_credit_notes(invoice)

        normalized = self._normalize_details(invoice, details)
        subtotal = sum(item["subtotal"] for item in normalized)
        tax = self._proportional_amount(invoice.tax, invoice.subtotal, subtotal)
        discount = self._proportional_amount(invoice.discount, invoice.subtotal, subtotal)
        total = subtotal + tax - discount
        reversal_type = "total" if self._is_total_reversal(invoice, normalized) else "partial"

        note = CreditNote.objects.create(
            company=note_company,
            origin_invoice=invoice,
            reversal_type=reversal_type,
            reason=reason,
            subtotal=subtotal,
            tax=tax,
            discount=discount,
            total=total,
            created_by=user,
        )
        CreditNoteDetail.objects.bulk_create(
            [
                CreditNoteDetail(
                    credit_note=note,
                    origin_detail=item["origin_detail"],
                    product=item["product"],
                    quantity=item["quantity"],
                    price=item["price"],
                    subtotal=item["subtotal"],
                )
                for item in normalized
            ]
        )

        factory_result = self.document_factory.create_for_credit_note(
            note,
            user=user,
            issuer_id=issuer_id or document.issuer_id,
        )
        if factory_result.error:
            raise ValueError(factory_result.error)
        if restore_inventory:
            self._restore_inventory_once(note, normalized, factory_result.document, user=user)
        if factory_result.document:
            ECFEventLog.objects.create(
                electronic_document=factory_result.document,
                event_type="created",
                message="E34 creado para nota de credito fiscal.",
                payload={
                    "origin_invoice_id": invoice.id,
                    "origin_invoice_number": invoice.invoice_number,
                    "origin_encf": document.encf,
                    "credit_note_id": note.id,
                    "credit_note_number": note.credit_note_number,
                    "reversal_type": note.reversal_type,
                    "restore_inventory": restore_inventory,
                    "fiscal_status": factory_result.document.fiscal_status,
                    "job_status": factory_result.document.job_status,
                },
                created_by=user,
            )
            if enqueue_enabled:
                transaction.on_commit(
                    lambda document_id=factory_result.document.id, user_id=getattr(user, "id", None): self._enqueue_after_commit(document_id, user_id)
                )
            note.refresh_from_db()
        return CreditNoteCreationResult(
            credit_note=note,
            electronic_document=factory_result.document,
            ecf_enqueued=bool(factory_result.document and enqueue_enabled and not ecf_error),
            ecf_error=ecf_error,
        )

    def _normalize_details(self, invoice: Invoice, details: list[dict] | None) -> list[dict]:
        origin_details = {detail.id: detail for detail in invoice.details.select_related("product").all()}
        if not origin_details:
            raise ValueError("La factura origen no tiene detalles.")
        requested = details or [
            {"origin_detail": detail.id, "quantity": detail.quantity}
            for detail in origin_details.values()
        ]

        normalized = []
        for item in requested:
            origin_detail_id = int(item.get("origin_detail") or item.get("origin_detail_id") or item.get("invoice_detail"))
            origin_detail = origin_details.get(origin_detail_id)
            if not origin_detail:
                raise ValueError(f"Detalle origen {origin_detail_id} no pertenece a la factura.")
            quantity = int(item.get("quantity") or 0)
            if quantity <= 0:
                raise ValueError("La cantidad a reversar debe ser mayor a cero.")
            available = origin_detail.quantity - self._already_reversed(origin_detail)
            if quantity > available:
                raise ValueError(f"Cantidad a reversar excede lo disponible para {origin_detail.product.name}. Disponible: {available}.")
            price = origin_detail.price
            normalized.append(
                {
                    "origin_detail": origin_detail,
                    "product": origin_detail.product,
                    "quantity": quantity,
                    "price": price,
                    "subtotal": price * quantity,
                }
            )
        return normalized

    def _already_reversed(self, origin_detail: InvoiceDetail) -> int:
        return origin_detail.credit_note_details.aggregate(total=Sum("quantity"))["total"] or 0

    def _assert_no_unresolved_credit_notes(self, invoice: Invoice) -> None:
        unresolved = (
            invoice.credit_notes
            .exclude(fiscal_resolution_status__in={"confirmed", "resolved"})
            .filter(
                fiscal_resolution_status__in={"pending", "rejected"},
            )
            .exists()
        )
        if unresolved:
            raise ValueError("La factura tiene una E34 pendiente o rechazada sin resolver; no se permiten nuevos reversos.")

    def _restore_inventory_once(self, note: CreditNote, normalized: list[dict], document: ElectronicFiscalDocument | None, user=None) -> bool:
        locked_note = CreditNote.objects.select_for_update().get(pk=note.pk)
        if locked_note.inventory_restored_at:
            if document:
                ECFEventLog.objects.create(
                    electronic_document=document,
                    event_type="skipped",
                    message="Restauracion de inventario E34 omitida; ya habia sido aplicada.",
                    payload={
                        "credit_note_id": locked_note.id,
                        "credit_note_number": locked_note.credit_note_number,
                        "inventory_restored_at": locked_note.inventory_restored_at.isoformat(),
                    },
                    created_by=user,
                )
            return False

        for item in normalized:
            Product.objects.filter(pk=item["product"].pk).update(stock=F("stock") + item["quantity"])

        locked_note.inventory_restored_at = timezone.now()
        locked_note.save(update_fields=["inventory_restored_at", "updated_at"])
        if document:
            ECFEventLog.objects.create(
                electronic_document=document,
                event_type="inventory_restored",
                message="Inventario restaurado por nota de credito E34.",
                payload={
                    "credit_note_id": locked_note.id,
                    "credit_note_number": locked_note.credit_note_number,
                    "items": [
                        {
                            "product_id": item["product"].id,
                            "origin_detail_id": item["origin_detail"].id,
                            "quantity": item["quantity"],
                        }
                        for item in normalized
                    ],
                    "inventory_restored_at": locked_note.inventory_restored_at.isoformat(),
                },
                created_by=user,
            )
        return True

    def _proportional_amount(self, value: Decimal, base: Decimal, subtotal: Decimal) -> Decimal:
        if not value or not base:
            return Decimal("0.00")
        return (Decimal(value) * Decimal(subtotal) / Decimal(base)).quantize(Decimal("0.01"))

    def _is_total_reversal(self, invoice: Invoice, normalized: list[dict]) -> bool:
        reversed_by_detail = {item["origin_detail"].id: item["quantity"] for item in normalized}
        for detail in invoice.details.all():
            if reversed_by_detail.get(detail.id, 0) + self._already_reversed(detail) < detail.quantity:
                return False
        return True

    def _enqueue_after_commit(self, document_id: int, user_id: int | None) -> None:
        try:
            enqueue_submission_pipeline(document_id, user_id=user_id, validate_xsd=True)
        except ECFCeleryUnavailable as exc:
            document = ElectronicFiscalDocument.objects.filter(pk=document_id).first()
            if document:
                document.last_error = str(exc)
                document.save(update_fields=["last_error", "updated_at"])
                ECFEventLog.objects.create(
                    electronic_document=document,
                    event_type="error",
                    message="No fue posible encolar automaticamente el pipeline E34.",
                    payload={
                        "stage": "auto_enqueue_e34",
                        "error": str(exc),
                        "fiscal_status": document.fiscal_status,
                        "job_status": document.job_status,
                    },
                )
