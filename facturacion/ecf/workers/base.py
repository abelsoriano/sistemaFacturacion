"""Shared Celery worker primitives for e-CF tasks."""

from __future__ import annotations

import logging

from celery import Task
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from facturacion.ecf.exceptions import ECFError, ECFPermanentError, ECFTemporaryError
from facturacion.ecf.services.status_transitions import ECFStatusTransitionService
from facturacion.models import ECFEventLog, ECFStatusEvent, ElectronicFiscalDocument

logger = logging.getLogger("facturacion.ecf.tasks")

TERMINAL_STATUSES = {"accepted", "rejected", "cancelled"}
status_transitions = ECFStatusTransitionService()


class ECFCompanyScopeError(ECFPermanentError):
    """Raised when an async e-CF task detects a cross-company document graph."""


def validate_document_company_scope(document: ElectronicFiscalDocument) -> None:
    """Ensure an async e-CF task only operates a company-consistent document."""
    company_id = document.company_id
    if not company_id:
        raise ECFCompanyScopeError("El documento e-CF no tiene empresa asociada.")

    related_checks = (
        ("invoice", document.invoice_id, getattr(document, "invoice", None)),
        ("credit_note", document.credit_note_id, getattr(document, "credit_note", None)),
        ("issuer", document.issuer_id, getattr(document, "issuer", None)),
        ("sequence", document.sequence_id, getattr(document, "sequence", None)),
    )
    for relation_name, relation_id, related in related_checks:
        if not relation_id:
            continue
        related_company_id = getattr(related, "company_id", None)
        if not related_company_id:
            raise ECFCompanyScopeError(
                f"Inconsistencia multiempresa e-CF: {relation_name} no tiene empresa asociada."
            )
        if related_company_id != company_id:
            raise ECFCompanyScopeError(
                f"Inconsistencia multiempresa e-CF: {relation_name} pertenece a otra empresa."
            )


class ECFTask(Task):
    """Base task with structured logging and exponential retry helpers."""

    abstract = True
    max_retries = getattr(settings, "ECF_TASK_MAX_RETRIES", 5)

    def retry_delay(self) -> int:
        base = getattr(settings, "ECF_TASK_RETRY_BACKOFF_SECONDS", 60)
        return min(base * (2 ** int(self.request.retries or 0)), 3600)

    def log(self, level: int, message: str, **extra) -> None:
        logger.log(level, message, extra={"ecf": extra})

    def mark_started(self, document_id: int, stage: str):
        document = self._load_task_document(document_id)
        try:
            validate_document_company_scope(document)
        except ECFCompanyScopeError as exc:
            self._record_failure(document_id, stage, exc, is_temporary=False, delay=0)
            raise
        return status_transitions.transition(
            document,
            job_status="running",
            source=f"task_{stage}_started",
            reason=f"Task e-CF iniciada: {stage}.",
            task_id=self.request.id,
            validate=False,
        ).document

    def mark_succeeded(self, document_id: int, stage: str):
        document = self._load_task_document(document_id)
        validate_document_company_scope(document)
        return status_transitions.transition(
            document,
            job_status="idle",
            source=f"task_{stage}_succeeded",
            reason=f"Task e-CF completada: {stage}.",
            task_id=self.request.id,
            validate=False,
            extra_update_fields={"last_error": None, "next_retry_at": None},
        ).document

    def fail_or_retry(self, exc: Exception, document_id: int, stage: str):
        delay = self.retry_delay()
        is_temporary = isinstance(exc, ECFTemporaryError) or _looks_temporary(exc)
        self._record_failure(document_id, stage, exc, is_temporary, delay)

        if is_temporary and self.request.retries < self.max_retries:
            self.log(
                logging.WARNING,
                "temporary e-CF task failure; scheduling retry",
                document_id=document_id,
                stage=stage,
                retry_in_seconds=delay,
                retries=self.request.retries,
                error=str(exc),
            )
            raise self.retry(exc=exc, countdown=delay)

        self.log(
            logging.ERROR,
            "permanent e-CF task failure",
            document_id=document_id,
            stage=stage,
            retries=self.request.retries,
            error=str(exc),
        )
        raise exc

    @transaction.atomic
    def _record_failure(self, document_id: int, stage: str, exc: Exception, is_temporary: bool, delay: int) -> None:
        document = self._load_task_document(document_id, for_update=True)
        previous_fiscal_status = document.fiscal_status
        previous_job_status = document.job_status
        target_job_status = "retrying" if is_temporary else "failed"
        next_retry_at = timezone.now() + timezone.timedelta(seconds=delay) if is_temporary else None

        ElectronicFiscalDocument.objects.filter(pk=document_id).update(
            job_status=target_job_status,
            last_error=str(exc),
            next_retry_at=next_retry_at,
            updated_at=timezone.now(),
        )
        document.refresh_from_db()
        ECFStatusEvent.objects.create(
            document=document,
            previous_fiscal_status=previous_fiscal_status,
            new_fiscal_status=previous_fiscal_status,
            previous_job_status=previous_job_status,
            new_job_status=target_job_status,
            source=f"task_{stage}_{'retrying' if is_temporary else 'failed'}",
            reason=str(exc),
            task_id=self.request.id,
        )

        ECFEventLog.objects.create(
            electronic_document=document,
            event_type="retry_scheduled" if is_temporary else "error",
            message=f"{stage}: {'reintento programado' if is_temporary else 'error permanente'}.",
            payload={
                "stage": stage,
                "task_id": self.request.id,
                "retries": self.request.retries,
                "max_retries": self.max_retries,
                "retry_in_seconds": delay if is_temporary else None,
                "error": str(exc),
                "company_id": document.company_id,
                "company_scope_error": isinstance(exc, ECFCompanyScopeError),
            },
        )

    def _load_task_document(self, document_id: int, for_update: bool = False) -> ElectronicFiscalDocument:
        if for_update:
            return ElectronicFiscalDocument.objects.select_for_update().get(pk=document_id)

        queryset = ElectronicFiscalDocument.objects.select_related(
            "company",
            "invoice",
            "credit_note",
            "issuer",
            "sequence",
        )
        return queryset.get(pk=document_id)


def _looks_temporary(exc: Exception) -> bool:
    message = str(exc).lower()
    temporary_markers = (
        "timeout",
        "timed out",
        "connection",
        "tempor",
        "503",
        "502",
        "504",
        "429",
        "soap dgii",
        "invocando soap",
    )
    return isinstance(exc, ECFError) and any(marker in message for marker in temporary_markers)
