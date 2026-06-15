"""Reconcile technical job state for terminal fiscal documents."""

from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction

from facturacion.ecf.services.status_transitions import ECFStatusTransitionService
from facturacion.models import ECFEventLog, ElectronicFiscalDocument


TERMINAL_FISCAL_STATUSES = {"accepted", "rejected"}
NON_IDLE_JOB_STATUSES = {"queued", "running", "retrying", "failed"}


@dataclass(frozen=True)
class JobStatusReconciliationResult:
    document: ElectronicFiscalDocument
    reconciled: bool
    previous_job_status: str


class ECFJobStatusReconciliationService:
    """Set stale technical job states to idle when fiscal processing is terminal."""

    def __init__(self, status_transitions: ECFStatusTransitionService | None = None) -> None:
        self.status_transitions = status_transitions or ECFStatusTransitionService()

    @transaction.atomic
    def reconcile_terminal_document(
        self,
        document: ElectronicFiscalDocument,
        *,
        user=None,
        source: str = "terminal_job_status_reconciliation",
        reason: str | None = None,
        task_id: str | None = None,
    ) -> JobStatusReconciliationResult:
        locked_document = ElectronicFiscalDocument.objects.select_for_update().get(pk=document.pk)
        previous_job_status = locked_document.job_status

        if locked_document.fiscal_status not in TERMINAL_FISCAL_STATUSES:
            return JobStatusReconciliationResult(locked_document, False, previous_job_status)
        if locked_document.job_status not in NON_IDLE_JOB_STATUSES:
            return JobStatusReconciliationResult(locked_document, False, previous_job_status)

        transition = self.status_transitions.transition(
            locked_document,
            job_status="idle",
            source=source,
            reason=reason or "Documento fiscal terminal; estado tecnico reconciliado a idle.",
            task_id=task_id,
            validate=False,
            extra_update_fields={"next_retry_at": None},
        )
        locked_document = transition.document

        ECFEventLog.objects.create(
            electronic_document=locked_document,
            event_type="job_reconciled",
            message="Estado tecnico reconciliado para documento fiscal terminal.",
            payload={
                "previous_job_status": previous_job_status,
                "new_job_status": locked_document.job_status,
                "fiscal_status": locked_document.fiscal_status,
                "source": source,
            },
            created_by=user,
        )

        return JobStatusReconciliationResult(locked_document, True, previous_job_status)

    def reconcile_terminal_queryset(self, *, limit: int | None = None, user=None) -> int:
        queryset = (
            ElectronicFiscalDocument.objects
            .filter(fiscal_status__in=TERMINAL_FISCAL_STATUSES, job_status__in=NON_IDLE_JOB_STATUSES)
            .order_by("id")
        )
        if limit:
            queryset = queryset[:limit]

        reconciled = 0
        for document in queryset:
            result = self.reconcile_terminal_document(document, user=user, source="terminal_job_status_bulk_reconciliation")
            if result.reconciled:
                reconciled += 1
        return reconciled
