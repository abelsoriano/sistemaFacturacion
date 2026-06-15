"""Factory service for creating e-CF documents from invoices."""

from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction

from facturacion.ecf.utils.text import digits_only
from facturacion.models import Company, CreditNote, ECFEventLog, ECFIssuerConfig, ECFSequence, ElectronicFiscalDocument, Invoice


@dataclass(frozen=True)
class ECFDocumentFactoryResult:
    document: ElectronicFiscalDocument | None
    created: bool
    error: str | None = None


class ECFDocumentFactoryService:
    """Create an ElectronicFiscalDocument safely and idempotently."""

    def create_for_invoice(
        self,
        invoice: Invoice,
        user=None,
        issuer_id: int | None = None,
        ecf_type: str | None = None,
    ) -> ECFDocumentFactoryResult:
        try:
            return self._create_for_invoice_atomic(invoice, user=user, issuer_id=issuer_id, ecf_type=ecf_type)
        except ValidationError as exc:
            return ECFDocumentFactoryResult(document=None, created=False, error=self._format_validation_error(exc))

    def create_for_credit_note(
        self,
        credit_note: CreditNote,
        user=None,
        issuer_id: int | None = None,
    ) -> ECFDocumentFactoryResult:
        try:
            return self._create_for_credit_note_atomic(credit_note, user=user, issuer_id=issuer_id)
        except ValidationError as exc:
            return ECFDocumentFactoryResult(document=None, created=False, error=self._format_validation_error(exc))

    @transaction.atomic
    def _create_for_invoice_atomic(
        self,
        invoice: Invoice,
        user=None,
        issuer_id: int | None = None,
        ecf_type: str | None = None,
    ) -> ECFDocumentFactoryResult:
        locked_invoice = Invoice.objects.select_for_update().get(pk=invoice.pk)

        existing = getattr(locked_invoice, "electronic_document", None)
        if existing:
            return ECFDocumentFactoryResult(document=existing, created=False)

        issuer = self._resolve_issuer(issuer_id, company=locked_invoice.company)
        document_type = ecf_type or self._resolve_ecf_type(locked_invoice, issuer)
        encf, sequence = ECFSequence.allocate_next(issuer=issuer, ecf_type=document_type)

        document = ElectronicFiscalDocument.objects.create(
            invoice=locked_invoice,
            company=locked_invoice.company,
            issuer=issuer,
            sequence=sequence,
            ecf_type=document_type,
            encf=encf,
            status="draft",
        )
        ECFEventLog.objects.create(
            electronic_document=document,
            event_type="created",
            message="Documento e-CF creado automaticamente desde factura.",
            created_by=user,
            payload={
                "invoice_id": locked_invoice.id,
                "invoice_number": locked_invoice.invoice_number,
                "auto_created": True,
            },
        )
        return ECFDocumentFactoryResult(document=document, created=True)

    @transaction.atomic
    def _create_for_credit_note_atomic(
        self,
        credit_note: CreditNote,
        user=None,
        issuer_id: int | None = None,
    ) -> ECFDocumentFactoryResult:
        locked_note = CreditNote.objects.select_for_update().select_related("origin_invoice").get(pk=credit_note.pk)

        existing = getattr(locked_note, "electronic_document", None)
        if existing:
            return ECFDocumentFactoryResult(document=existing, created=False)

        issuer = self._resolve_issuer(issuer_id, company=locked_note.company)
        encf, sequence = ECFSequence.allocate_next(issuer=issuer, ecf_type="34")
        document = ElectronicFiscalDocument.objects.create(
            credit_note=locked_note,
            company=locked_note.company,
            issuer=issuer,
            sequence=sequence,
            ecf_type="34",
            encf=encf,
            status="draft",
        )
        ECFEventLog.objects.create(
            electronic_document=document,
            event_type="created",
            message="Documento e-CF E34 creado desde nota de credito.",
            created_by=user,
            payload={
                "credit_note_id": locked_note.id,
                "credit_note_number": locked_note.credit_note_number,
                "origin_invoice_id": locked_note.origin_invoice_id,
                "origin_invoice_number": locked_note.origin_invoice.invoice_number,
            },
        )
        return ECFDocumentFactoryResult(document=document, created=True)

    def _resolve_issuer(self, issuer_id: int | None, *, company: Company | None) -> ECFIssuerConfig:
        if company is None:
            raise ValidationError("El documento comercial no tiene empresa asociada para resolver emisor e-CF.")

        queryset = ECFIssuerConfig.objects.filter(company=company, is_active=True)
        if issuer_id:
            queryset = queryset.filter(pk=issuer_id)
            issuer = queryset.order_by("id").first()
            if not issuer:
                raise ValidationError("El emisor e-CF no pertenece a la empresa activa o no esta activo.")
            return issuer

        issuer_count = queryset.count()
        if issuer_count > 1:
            raise ValidationError("Hay varios emisores e-CF activos para la empresa; especifica issuer_id.")
        issuer = queryset.order_by("id").first()
        if not issuer:
            raise ValidationError("No hay emisor e-CF activo configurado para la empresa.")
        return issuer

    def _resolve_ecf_type(self, invoice: Invoice, issuer: ECFIssuerConfig) -> str:
        if issuer.auto_ecf_rules_enabled:
            client_rnc = digits_only(invoice.client.ruc_ci) if invoice.client else ""
            client_rnc = client_rnc or ""
            if invoice.client and len(client_rnc) in (9, 11):
                return "31"
            return "32"
        requested = issuer.default_ecf_type or getattr(settings, "ECF_DEFAULT_TYPE", "32")
        return str(requested or "32")

    def _format_validation_error(self, exc: ValidationError) -> str:
        if hasattr(exc, "messages"):
            return " ".join(str(message) for message in exc.messages)
        return str(exc)
