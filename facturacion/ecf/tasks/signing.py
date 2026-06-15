"""XML signing Celery tasks."""

from __future__ import annotations

import logging

from celery import shared_task
from django.contrib.auth import get_user_model
from django.db import transaction

from facturacion.ecf.exceptions import ECFPermanentError
from facturacion.ecf.certificates.resolver import resolve_certificate_credentials
from facturacion.ecf.services.certificate_policy import ECFCertificateSigningPolicy
from facturacion.ecf.services.signing import ECFSigningService
from facturacion.ecf.workers.base import ECFTask
from facturacion.models import ECFEventLog, ElectronicFiscalDocument


@shared_task(bind=True, base=ECFTask, name="facturacion.ecf.tasks.signing.sign_xml")
def sign_xml(self, document_id: int, user_id: int | None = None, validate_xsd: bool = True):
    """Sign generated XML idempotently."""
    user = _user(user_id)
    self.mark_started(document_id, "sign_xml")
    try:
        certificate_policy = ECFCertificateSigningPolicy()
        with transaction.atomic():
            document = ElectronicFiscalDocument.objects.select_for_update().select_related("issuer").get(pk=document_id)
            if document.signed_xml_content and document.fiscal_status in {"signed", "submitted", "accepted", "rejected"}:
                ECFEventLog.objects.create(
                    electronic_document=document,
                    event_type="skipped",
                    message="XML ya firmado; task omitida por idempotencia.",
                    payload={"stage": "sign_xml", "task_id": self.request.id, "status": document.fiscal_status, "job_status": document.job_status},
                    created_by=user,
                )
                document = self.mark_succeeded(document_id, "sign_xml")
                return {"document_id": document_id, "status": document.fiscal_status, "fiscal_status": document.fiscal_status, "job_status": document.job_status, "skipped": True}
            policy_result = certificate_policy.evaluate(document.issuer)
            if policy_result.blocked:
                document = certificate_policy.record_blocked(
                    document,
                    policy_result,
                    user=user,
                    source="task_sign_xml_certificate_policy_failed",
                    task_id=self.request.id,
                )
                return {
                    "document_id": document_id,
                    "status": document.fiscal_status,
                    "fiscal_status": document.fiscal_status,
                    "job_status": document.job_status,
                    "error": policy_result.reason,
                }
            certificate_policy.log_warnings(document, policy_result, user=user)
            certificate_path, certificate_password = resolve_certificate_credentials(document.issuer)
            if not certificate_path:
                raise ECFPermanentError("El emisor no tiene certificado e-CF configurado.")

        result = ECFSigningService().sign(
            document=document,
            certificate_path=certificate_path,
            certificate_password=certificate_password,
            user=user,
            validate_xsd=validate_xsd,
        )
        document = self.mark_succeeded(document_id, "sign_xml")
        self.log(logging.INFO, "e-CF XML signed", document_id=document_id, status=result.document.status)
        return {
            "document_id": document_id,
            "status": document.fiscal_status,
            "fiscal_status": document.fiscal_status,
            "job_status": document.job_status,
            "signature_validated": result.signature_validated,
            "xsd_validated": result.xsd_validated,
        }
    except Exception as exc:
        self.fail_or_retry(exc, document_id, "sign_xml")


def _user(user_id: int | None):
    if not user_id:
        return None
    return get_user_model().objects.filter(pk=user_id).first()
