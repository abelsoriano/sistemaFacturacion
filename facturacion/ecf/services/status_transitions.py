"""Runtime status transition helpers for e-CF fiscal and job states."""

from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction

from facturacion.ecf.state_machine import ECFFiscalStateMachine, ECFJobStateMachine
from facturacion.models import ECFStatusEvent, ElectronicFiscalDocument


@dataclass(frozen=True)
class StatusTransitionResult:
    document: ElectronicFiscalDocument
    changed: bool


class ECFStatusTransitionService:
    """Apply audited fiscal/job status changes without mixing both domains."""

    def __init__(
        self,
        fiscal_state_machine: ECFFiscalStateMachine | None = None,
        job_state_machine: ECFJobStateMachine | None = None,
    ) -> None:
        self.fiscal_state_machine = fiscal_state_machine or ECFFiscalStateMachine()
        self.job_state_machine = job_state_machine or ECFJobStateMachine()

    @transaction.atomic
    def transition(
        self,
        document: ElectronicFiscalDocument,
        *,
        fiscal_status: str | None = None,
        job_status: str | None = None,
        source: str,
        reason: str | None = None,
        task_id: str | None = None,
        validate: bool = True,
        extra_update_fields: dict | None = None,
    ) -> StatusTransitionResult:
        locked_document = ElectronicFiscalDocument.objects.select_for_update().get(pk=document.pk)
        previous_fiscal_status = locked_document.fiscal_status
        previous_job_status = locked_document.job_status
        new_fiscal_status = fiscal_status or previous_fiscal_status
        new_job_status = job_status or previous_job_status

        fiscal_changed = new_fiscal_status != previous_fiscal_status
        job_changed = new_job_status != previous_job_status

        if validate and fiscal_changed:
            self.fiscal_state_machine.assert_transition(previous_fiscal_status, new_fiscal_status)
        if validate and job_changed:
            self.job_state_machine.assert_transition(previous_job_status, new_job_status)

        updates: list[str] = []
        if fiscal_changed:
            locked_document.fiscal_status = new_fiscal_status
            locked_document.status = new_fiscal_status
            updates.extend(["fiscal_status", "status"])
        if job_changed:
            locked_document.job_status = new_job_status
            updates.append("job_status")

        for field, value in (extra_update_fields or {}).items():
            setattr(locked_document, field, value)
            updates.append(field)

        if updates:
            updates.append("updated_at")
            locked_document.save(update_fields=sorted(set(updates)))
            ECFStatusEvent.objects.create(
                document=locked_document,
                previous_fiscal_status=previous_fiscal_status,
                new_fiscal_status=new_fiscal_status,
                previous_job_status=previous_job_status,
                new_job_status=new_job_status,
                source=source,
                reason=reason,
                task_id=task_id,
            )

        return StatusTransitionResult(document=locked_document, changed=bool(updates))
