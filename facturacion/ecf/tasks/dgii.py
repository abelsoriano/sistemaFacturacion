"""DGII submission and status Celery tasks."""

from __future__ import annotations

import logging

from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import F

from facturacion.ecf.exceptions import ECFPermanentError
from facturacion.ecf.services.dgii_status import DGIIStatusService
from facturacion.ecf.services.dgii_submission import DGIISubmissionService
from facturacion.ecf.workers.base import ECFTask
from facturacion.models import ECFEventLog, ElectronicFiscalDocument


@shared_task(bind=True, base=ECFTask, name="facturacion.ecf.tasks.dgii.submit_dgii")
def submit_dgii(self, document_id: int, user_id: int | None = None, environment: str | None = None, force: bool = False):
    """Submit signed XML to DGII with duplicate-send protection."""
    user = _user(user_id)
    self.mark_started(document_id, "submit_dgii")
    try:
        skip = _submission_preflight(document_id, user, self.request.id, force=force)
        if skip:
            document = self.mark_succeeded(document_id, "submit_dgii")
            skip["status"] = document.fiscal_status
            skip["fiscal_status"] = document.fiscal_status
            skip["job_status"] = document.job_status
            return skip

        document = ElectronicFiscalDocument.objects.get(pk=document_id)
        result = DGIISubmissionService().submit(document=document, user=user, environment=environment)
        self.log(logging.INFO, "e-CF submitted to DGII", document_id=document_id, track_id=result.track_id, status=result.status)

        if result.track_id:
            countdown = getattr(settings, "ECF_TASK_STATUS_CHECK_DELAY_SECONDS", 120)
            check_status.apply_async(args=[document_id], kwargs={"user_id": user_id, "environment": environment}, countdown=countdown)

        document = self.mark_succeeded(document_id, "submit_dgii")
        return {"document_id": document_id, "track_id": result.track_id, "status": document.fiscal_status, "fiscal_status": document.fiscal_status, "job_status": document.job_status}
    except Exception as exc:
        self.fail_or_retry(exc, document_id, "submit_dgii")


@shared_task(bind=True, base=ECFTask, name="facturacion.ecf.tasks.dgii.check_status")
def check_status(self, document_id: int, user_id: int | None = None, environment: str | None = None):
    """Query DGII status by TrackID."""
    user = _user(user_id)
    self.mark_started(document_id, "check_status")
    try:
        with transaction.atomic():
            document = ElectronicFiscalDocument.objects.select_for_update().get(pk=document_id)
            if document.fiscal_status in {"accepted", "rejected"}:
                ECFEventLog.objects.create(
                    electronic_document=document,
                    event_type="skipped",
                    message="Consulta omitida: documento en estado terminal.",
                    payload={"stage": "check_status", "task_id": self.request.id, "status": document.fiscal_status, "job_status": document.job_status},
                    created_by=user,
                )
                document = self.mark_succeeded(document_id, "check_status")
                return {"document_id": document_id, "status": document.fiscal_status, "fiscal_status": document.fiscal_status, "job_status": document.job_status, "skipped": True}
            if not document.track_id:
                raise ECFPermanentError("El documento no tiene TrackID para consultar estado.")
            ElectronicFiscalDocument.objects.filter(pk=document_id).update(status_check_attempts=F("status_check_attempts") + 1)

        document = ElectronicFiscalDocument.objects.get(pk=document_id)
        result = DGIIStatusService().check(document=document, user=user, environment=environment)
        document = self.mark_succeeded(document_id, "check_status")
        self.log(logging.INFO, "e-CF status checked", document_id=document_id, status=result.status, dgii_status=result.dgii_status)
        return {"document_id": document_id, "status": document.fiscal_status, "fiscal_status": document.fiscal_status, "job_status": document.job_status, "dgii_status": result.dgii_status}
    except Exception as exc:
        self.fail_or_retry(exc, document_id, "check_status")


@shared_task(bind=True, base=ECFTask, name="facturacion.ecf.tasks.dgii.retry_submission")
def retry_submission(self, document_id: int, user_id: int | None = None, environment: str | None = None):
    """Explicit operator-triggered retry for documents that never got a TrackID."""
    user = _user(user_id)
    self.mark_started(document_id, "retry_submission")
    try:
        skip = _submission_preflight(document_id, user, self.request.id, force=True)
        if skip:
            document = self.mark_succeeded(document_id, "retry_submission")
            skip["status"] = document.fiscal_status
            skip["fiscal_status"] = document.fiscal_status
            skip["job_status"] = document.job_status
            return skip

        document = ElectronicFiscalDocument.objects.get(pk=document_id)
        result = DGIISubmissionService().submit(document=document, user=user, environment=environment)
        document = self.mark_succeeded(document_id, "retry_submission")
        self.log(logging.INFO, "e-CF resubmitted to DGII", document_id=document_id, track_id=result.track_id, status=result.status)
        return {"document_id": document_id, "track_id": result.track_id, "status": document.fiscal_status, "fiscal_status": document.fiscal_status, "job_status": document.job_status}
    except Exception as exc:
        self.fail_or_retry(exc, document_id, "retry_submission")


@transaction.atomic
def _submission_preflight(document_id: int, user, task_id: str, force: bool = False):
    document = ElectronicFiscalDocument.objects.select_for_update().get(pk=document_id)
    if document.fiscal_status in {"accepted", "rejected"}:
        return _skip(document, user, task_id, "submit_dgii", "Documento terminal; no se reenvía a DGII.")
    if document.track_id:
        return _skip(document, user, task_id, "submit_dgii", "Documento ya tiene TrackID; no se duplica envío DGII.")
    if not document.signed_xml_content:
        raise ECFPermanentError("El documento no tiene XML firmado para enviar a DGII.")

    ElectronicFiscalDocument.objects.filter(pk=document_id).update(
        submission_attempts=F("submission_attempts") + 1,
        last_error=None,
        next_retry_at=None,
    )
    return None


def _skip(document, user, task_id: str, stage: str, message: str):
    ECFEventLog.objects.create(
        electronic_document=document,
        event_type="skipped",
        message=message,
        payload={"stage": stage, "task_id": task_id, "status": document.fiscal_status, "job_status": document.job_status, "track_id": document.track_id},
        created_by=user,
    )
    return {"document_id": document.pk, "status": document.fiscal_status, "fiscal_status": document.fiscal_status, "job_status": document.job_status, "track_id": document.track_id, "skipped": True}


def _user(user_id: int | None):
    if not user_id:
        return None
    return get_user_model().objects.filter(pk=user_id).first()
