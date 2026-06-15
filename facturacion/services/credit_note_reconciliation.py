"""Post-DGII reconciliation for E34 credit notes."""

from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from facturacion.models import CreditNote, ECFEventLog, ElectronicFiscalDocument, InvoiceDetail, Product, SaleDetail


@dataclass(frozen=True)
class ReconciliationResult:
    credit_note: CreditNote
    changed: bool
    message: str


class CreditNoteReconciliationService:
    """Keep commercial credit notes aligned with the DGII outcome for E34."""

    def reconcile_after_dgii_status(self, document: ElectronicFiscalDocument, user=None) -> ReconciliationResult | None:
        if not document.credit_note_id:
            return None
        if document.fiscal_status == "accepted":
            return self.confirm_accepted(document.credit_note, document=document, user=user)
        if document.fiscal_status == "rejected":
            return self.mark_rejected(document.credit_note, document=document, user=user)
        return None

    @transaction.atomic
    def confirm_accepted(self, credit_note: CreditNote, *, document: ElectronicFiscalDocument | None = None, user=None) -> ReconciliationResult:
        note = CreditNote.objects.select_for_update().select_related("origin_invoice").get(pk=credit_note.pk)
        document = document or getattr(note, "electronic_document", None)
        if note.fiscal_resolution_status == "confirmed" and note.inventory_reconciliation_status == "confirmed":
            return ReconciliationResult(note, False, "E34 ya estaba confirmada.")

        now = timezone.now()
        note.fiscal_resolution_status = "confirmed"
        note.inventory_reconciliation_status = "confirmed"
        note.inventory_reconciled_at = note.inventory_reconciled_at or now
        note.requires_manual_review = False
        note.save(update_fields=[
            "fiscal_resolution_status",
            "inventory_reconciliation_status",
            "inventory_reconciled_at",
            "requires_manual_review",
            "updated_at",
        ])
        self._mark_origin_refunded_if_total(note)
        self._log(
            document,
            "accepted",
            "Nota de credito E34 confirmada fiscalmente por DGII.",
            {
                "credit_note_id": note.id,
                "credit_note_number": note.credit_note_number,
                "inventory_reconciliation_status": note.inventory_reconciliation_status,
                "fiscal_resolution_status": note.fiscal_resolution_status,
            },
            user=user,
        )
        return ReconciliationResult(note, True, "E34 confirmada.")

    @transaction.atomic
    def mark_rejected(self, credit_note: CreditNote, *, document: ElectronicFiscalDocument | None = None, user=None) -> ReconciliationResult:
        note = CreditNote.objects.select_for_update().get(pk=credit_note.pk)
        document = document or getattr(note, "electronic_document", None)
        if (
            note.fiscal_resolution_status == "rejected"
            and note.inventory_reconciliation_status == "compensation_required"
            and note.requires_manual_review
        ):
            return ReconciliationResult(note, False, "E34 rechazada ya estaba marcada para revision.")

        note.fiscal_resolution_status = "rejected"
        note.inventory_reconciliation_status = "compensation_required"
        note.requires_manual_review = True
        note.save(update_fields=[
            "fiscal_resolution_status",
            "inventory_reconciliation_status",
            "requires_manual_review",
            "updated_at",
        ])
        self._log(
            document,
            "rejected",
            "Nota de credito E34 rechazada por DGII; requiere revision manual de inventario.",
            {
                "credit_note_id": note.id,
                "credit_note_number": note.credit_note_number,
                "rejection_reason": getattr(document, "rejection_reason", None),
                "inventory_reconciliation_status": note.inventory_reconciliation_status,
                "requires_manual_review": note.requires_manual_review,
            },
            user=user,
        )
        return ReconciliationResult(note, True, "E34 rechazada; requiere revision manual.")

    @transaction.atomic
    def compensate_inventory(self, credit_note: CreditNote, *, user=None) -> ReconciliationResult:
        note = (
            CreditNote.objects
            .select_for_update()
            .select_related("origin_invoice")
            .prefetch_related("details__product")
            .get(pk=credit_note.pk)
        )
        document = getattr(note, "electronic_document", None)
        if note.inventory_compensated_at:
            self._log(
                document,
                "skipped",
                "Compensacion de inventario E34 omitida; ya habia sido aplicada.",
                {"credit_note_id": note.id, "inventory_compensated_at": note.inventory_compensated_at.isoformat()},
                user=user,
            )
            return ReconciliationResult(note, False, "Inventario ya compensado.")
        if note.inventory_reconciliation_status != "compensation_required":
            raise ValueError("La nota no requiere compensacion de inventario.")

        issues = self._compensation_blockers(note)
        if issues:
            self._log(
                document,
                "skipped",
                "Compensacion de inventario E34 bloqueada por actividad posterior.",
                {"credit_note_id": note.id, "issues": issues},
                user=user,
            )
            raise ValueError("No se puede compensar automaticamente: " + " ".join(issues))

        for detail in note.details.select_related("product").all():
            Product.objects.filter(pk=detail.product_id).update(stock=F("stock") - detail.quantity)

        now = timezone.now()
        note.inventory_compensated_at = now
        note.inventory_reconciliation_status = "compensated"
        note.fiscal_resolution_status = "resolved"
        note.requires_manual_review = False
        note.save(update_fields=[
            "inventory_compensated_at",
            "inventory_reconciliation_status",
            "fiscal_resolution_status",
            "requires_manual_review",
            "updated_at",
        ])
        self._log(
            document,
            "inventory_compensated",
            "Inventario compensado por rechazo DGII de E34.",
            {
                "credit_note_id": note.id,
                "credit_note_number": note.credit_note_number,
                "items": [
                    {"product_id": detail.product_id, "quantity": detail.quantity}
                    for detail in note.details.all()
                ],
            },
            user=user,
        )
        return ReconciliationResult(note, True, "Inventario compensado.")

    @transaction.atomic
    def mark_reviewed(self, credit_note: CreditNote, *, user=None) -> ReconciliationResult:
        note = CreditNote.objects.select_for_update().get(pk=credit_note.pk)
        document = getattr(note, "electronic_document", None)
        if note.manual_reviewed_at:
            return ReconciliationResult(note, False, "Revision manual ya registrada.")

        note.manual_reviewed_at = timezone.now()
        if note.inventory_reconciliation_status in {"confirmed", "compensated"}:
            note.requires_manual_review = False
        note.save(update_fields=["manual_reviewed_at", "requires_manual_review", "updated_at"])
        self._log(
            document,
            "manual_review",
            "Revision manual registrada para nota de credito E34.",
            {
                "credit_note_id": note.id,
                "credit_note_number": note.credit_note_number,
                "requires_manual_review": note.requires_manual_review,
                "inventory_reconciliation_status": note.inventory_reconciliation_status,
            },
            user=user,
        )
        return ReconciliationResult(note, True, "Revision manual registrada.")

    def _compensation_blockers(self, note: CreditNote) -> list[str]:
        issues: list[str] = []
        restored_at = note.inventory_restored_at or note.created_at
        product_ids = [detail.product_id for detail in note.details.all()]
        if not product_ids:
            return ["La nota no tiene detalles para compensar."]

        later_invoice_exists = InvoiceDetail.objects.filter(
            product_id__in=product_ids,
            invoice__created_at__gt=restored_at,
        ).exclude(invoice_id=note.origin_invoice_id).exists()
        if later_invoice_exists:
            issues.append("Hay facturas posteriores con productos afectados.")

        later_sale_exists = SaleDetail.objects.filter(
            product_id__in=product_ids,
            sale__date__gt=restored_at,
        ).exists()
        if later_sale_exists:
            issues.append("Hay ventas posteriores con productos afectados.")

        for detail in note.details.select_related("product").all():
            if detail.product.stock < detail.quantity:
                issues.append(f"Stock insuficiente para compensar {detail.product.name}.")

        return issues

    def _mark_origin_refunded_if_total(self, note: CreditNote) -> None:
        if note.reversal_type != "total":
            return
        invoice = note.origin_invoice
        if invoice.status != "refunded":
            invoice.status = "refunded"
            invoice.save(update_fields=["status", "updated_at"])

    def _log(self, document, event_type: str, message: str, payload: dict, *, user=None) -> None:
        if not document:
            return
        ECFEventLog.objects.create(
            electronic_document=document,
            event_type=event_type,
            message=message,
            payload=payload,
            created_by=user,
        )
