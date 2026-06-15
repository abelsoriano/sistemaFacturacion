"""XML generation Celery tasks."""

from __future__ import annotations

import logging

from celery import shared_task
from django.contrib.auth import get_user_model
from django.db import transaction

from facturacion.ecf.services.xml_generation import ECFXMLGenerationService
from facturacion.ecf.workers.base import ECFTask
from facturacion.models import ECFEventLog, ElectronicFiscalDocument


@shared_task(bind=True, base=ECFTask, name="facturacion.ecf.tasks.xml.generate_xml")
def generate_xml(self, document_id: int, user_id: int | None = None, validate_xsd: bool = True):
    """Generate and persist XML idempotently."""
    user = _user(user_id)
    self.mark_started(document_id, "generate_xml")

    with transaction.atomic():
        document = ElectronicFiscalDocument.objects.select_for_update().get(pk=document_id)
        if document.xml_content and document.fiscal_status in {"xml_generated", "signed", "submitted", "accepted", "rejected"}:
            ECFEventLog.objects.create(
                electronic_document=document,
                event_type="skipped",
                message="XML ya generado; task omitida por idempotencia.",
                payload={"stage": "generate_xml", "task_id": self.request.id, "status": document.fiscal_status, "job_status": document.job_status},
                created_by=user,
            )
            self.mark_succeeded(document_id, "generate_xml")
            return {"document_id": document_id, "status": document.fiscal_status, "fiscal_status": document.fiscal_status, "job_status": "idle", "skipped": True}

    try:
        result = ECFXMLGenerationService().generate(document=document, user=user, validate_xsd=validate_xsd)
        document = self.mark_succeeded(document_id, "generate_xml")
        self.log(logging.INFO, "e-CF XML generated", document_id=document_id, status=result.document.status)
        return {"document_id": document_id, "status": document.fiscal_status, "fiscal_status": document.fiscal_status, "job_status": document.job_status, "xsd_validated": result.xsd_validated}
    except Exception as exc:
        self.fail_or_retry(exc, document_id, "generate_xml")


def _user(user_id: int | None):
    if not user_id:
        return None
    return get_user_model().objects.filter(pk=user_id).first()
