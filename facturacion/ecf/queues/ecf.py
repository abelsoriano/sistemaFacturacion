"""Queue entrypoints for e-CF asynchronous processing."""

from __future__ import annotations

from celery import chain
from django.db import transaction
from django.utils import timezone
from kombu.exceptions import OperationalError

from facturacion.ecf.exceptions import ECFCeleryUnavailable
from facturacion.ecf.services.certificate_policy import ECFCertificateSigningPolicy
from facturacion.ecf.services.status_transitions import ECFStatusTransitionService
from facturacion.ecf.tasks.dgii import check_status, retry_submission, submit_dgii
from facturacion.ecf.tasks.signing import sign_xml
from facturacion.ecf.tasks.xml import generate_xml
from facturacion.ecf.workers.base import ECFCompanyScopeError, validate_document_company_scope
from facturacion.models import ECFEventLog, ECFStatusEvent, ElectronicFiscalDocument


status_transitions = ECFStatusTransitionService()


def enqueue_generate_xml(document_id: int, user_id: int | None = None, validate_xsd: bool = True):
    return _enqueue_single(generate_xml, document_id, user_id, "generate_xml", validate_xsd=validate_xsd)


def enqueue_sign_xml(document_id: int, user_id: int | None = None, validate_xsd: bool = True):
    return _enqueue_single(sign_xml, document_id, user_id, "sign_xml", validate_xsd=validate_xsd)


def enqueue_submit_dgii(document_id: int, user_id: int | None = None, environment: str | None = None, force: bool = False):
    if not force:
        with transaction.atomic():
            document = ElectronicFiscalDocument.objects.select_for_update().get(pk=document_id)
            preflight_error = _company_scope_preflight(document, "submit_dgii")
            if preflight_error:
                return preflight_error
            if document.track_id or document.fiscal_status in {"submitted", "accepted", "rejected"}:
                _log_skip(document, "submit_dgii", "El documento ya fue enviado, está en proceso o está terminal.")
                return _queue_result(document, enqueued=False, track_id=document.track_id)
    return _enqueue_single(submit_dgii, document_id, user_id, "submit_dgii", environment=environment, force=force)


def enqueue_check_status(document_id: int, user_id: int | None = None, environment: str | None = None):
    return _enqueue_single(check_status, document_id, user_id, "check_status", environment=environment)


def enqueue_retry_submission(document_id: int, user_id: int | None = None, environment: str | None = None):
    with transaction.atomic():
        document = ElectronicFiscalDocument.objects.select_for_update().get(pk=document_id)
        preflight_error = _company_scope_preflight(document, "retry_submission")
        if preflight_error:
            return preflight_error
        if document.fiscal_status in {"accepted", "rejected"}:
            _log_skip(document, "retry_submission", "El documento está en estado terminal; no se reenvía.")
            return _queue_result(document, enqueued=False)
        if document.track_id:
            _log_skip(document, "retry_submission", "Documento ya tiene TrackID; no se duplica envío DGII.")
            return _queue_result(document, enqueued=False, track_id=document.track_id)

        if document.xml_content and not document.signed_xml_content:
            certificate_policy_error = _certificate_policy_preflight(document, "retry_submission")
            if certificate_policy_error:
                return certificate_policy_error
            signature = chain(
                sign_xml.si(document_id, user_id=user_id, validate_xsd=False),
                submit_dgii.si(document_id, user_id=user_id, environment=environment, force=True),
            )
            result = _apply_async_or_raise(signature)
            document = status_transitions.transition(
                document,
                job_status="queued",
                source="queue_sign_and_retry_submission",
                reason="Pipeline firma y reenvio encolado.",
                task_id=result.id,
                extra_update_fields={
                    "async_task_id": result.id,
                    "idempotency_key": f"ecf:{document.pk}:sign-and-retry",
                },
            ).document
            _log_queue(document, "sign_and_retry_submission", result.id)
            return _queue_result(document, enqueued=True)

    return _enqueue_single(retry_submission, document_id, user_id, "retry_submission", environment=environment)


def enqueue_submission_pipeline(
    document_id: int,
    user_id: int | None = None,
    validate_xsd: bool = True,
    environment: str | None = None,
):
    """Enqueue generate -> sign -> submit as an idempotent pipeline."""
    with transaction.atomic():
        document = ElectronicFiscalDocument.objects.select_for_update().get(pk=document_id)
        preflight_error = _company_scope_preflight(document, "pipeline")
        if preflight_error:
            return preflight_error
        if document.fiscal_status in {"submitted", "accepted", "rejected"}:
            _log_skip(document, "pipeline", "El documento ya está enviado, terminal o en proceso DGII.")
            return _queue_result(document, enqueued=False)

        steps = []
        if not document.xml_content:
            steps.append(generate_xml.si(document_id, user_id=user_id, validate_xsd=validate_xsd))
        if not document.signed_xml_content:
            certificate_policy_error = _certificate_policy_preflight(document, "pipeline")
            if certificate_policy_error:
                return certificate_policy_error
            steps.append(sign_xml.si(document_id, user_id=user_id, validate_xsd=validate_xsd))
        steps.append(submit_dgii.si(document_id, user_id=user_id, environment=environment))

        signature = chain(*steps)
        result = _apply_async_or_raise(signature)
        document = status_transitions.transition(
            document,
            job_status="queued",
            source="queue_pipeline",
            reason="Pipeline e-CF encolado.",
            task_id=result.id,
            extra_update_fields={
                "async_task_id": result.id,
                "idempotency_key": f"ecf:{document.pk}:pipeline",
            },
        ).document
        _log_queue(document, "pipeline", result.id)
        return _queue_result(document, enqueued=True)


def _enqueue_single(task, document_id: int, user_id: int | None, stage: str, **kwargs):
    with transaction.atomic():
        document = ElectronicFiscalDocument.objects.select_for_update().get(pk=document_id)
        preflight_error = _company_scope_preflight(document, stage)
        if preflight_error:
            return preflight_error
        if document.fiscal_status in {"accepted", "rejected"}:
            _log_skip(document, stage, "El documento está en estado terminal; no se encola la task.")
            return _queue_result(document, enqueued=False)
        if stage == "sign_xml":
            certificate_policy_error = _certificate_policy_preflight(document, stage)
            if certificate_policy_error:
                return certificate_policy_error
        result = _apply_async_or_raise(task, args=[document_id], kwargs={"user_id": user_id, **kwargs})
        document = status_transitions.transition(
            document,
            job_status="queued",
            source=f"queue_{stage}",
            reason=f"Task e-CF encolada: {stage}.",
            task_id=result.id,
            extra_update_fields={
                "async_task_id": result.id,
                "idempotency_key": f"ecf:{document.pk}:{stage}",
            },
        ).document
        _log_queue(document, stage, result.id)
        return _queue_result(document, enqueued=True)


def _company_scope_preflight(document: ElectronicFiscalDocument, stage: str):
    try:
        validate_document_company_scope(document)
    except ECFCompanyScopeError as exc:
        return _record_company_scope_failure(document, stage, exc)
    return None


def _certificate_policy_preflight(document: ElectronicFiscalDocument, stage: str):
    policy = ECFCertificateSigningPolicy()
    result = policy.evaluate(document.issuer)
    if not result.blocked:
        return None
    document = policy.record_blocked(
        document,
        result,
        source=f"queue_{stage}_certificate_policy_failed",
    )
    return _queue_result(document, enqueued=False, error=result.reason)


def _record_company_scope_failure(document: ElectronicFiscalDocument, stage: str, exc: Exception):
    previous_fiscal_status = document.fiscal_status
    previous_job_status = document.job_status

    ElectronicFiscalDocument.objects.filter(pk=document.pk).update(
        job_status="failed",
        last_error=str(exc),
        next_retry_at=None,
        updated_at=timezone.now(),
    )
    document.refresh_from_db()
    ECFStatusEvent.objects.create(
        document=document,
        previous_fiscal_status=previous_fiscal_status,
        new_fiscal_status=previous_fiscal_status,
        previous_job_status=previous_job_status,
        new_job_status="failed",
        source=f"queue_{stage}_failed",
        reason=str(exc),
    )
    ECFEventLog.objects.create(
        electronic_document=document,
        event_type="error",
        message=f"Preflight e-CF fallido antes de encolar: {stage}.",
        payload={
            "stage": stage,
            "error": str(exc),
            "company_id": document.company_id,
            "company_scope_error": True,
            "fiscal_status": document.fiscal_status,
            "job_status": document.job_status,
        },
    )
    return _queue_result(document, enqueued=False, error=str(exc))


def _log_queue(document: ElectronicFiscalDocument, stage: str, task_id: str) -> None:
    ECFEventLog.objects.create(
        electronic_document=document,
        event_type="queued",
        message=f"Task e-CF encolada: {stage}.",
        payload={
            "stage": stage,
            "task_id": task_id,
            "idempotency_key": document.idempotency_key,
            "fiscal_status": document.fiscal_status,
            "job_status": document.job_status,
        },
    )


def _log_skip(document: ElectronicFiscalDocument, stage: str, message: str) -> None:
    ECFEventLog.objects.create(
        electronic_document=document,
        event_type="skipped",
        message=message,
        payload={"stage": stage, "status": document.status, "fiscal_status": document.fiscal_status, "job_status": document.job_status, "track_id": document.track_id},
    )


def _queue_result(document: ElectronicFiscalDocument, *, enqueued: bool, track_id: str | None = None, error: str | None = None):
    result = {
        "enqueued": enqueued,
        "task_id": document.async_task_id,
        "status": document.fiscal_status,
        "fiscal_status": document.fiscal_status,
        "job_status": document.job_status,
    }
    if track_id is not None:
        result["track_id"] = track_id
    if error is not None:
        result["error"] = error
    return result


def _apply_async_or_raise(signature_or_task, *args, **kwargs):
    try:
        return signature_or_task.apply_async(*args, **kwargs)
    except (OperationalError, ConnectionError, RuntimeError) as exc:
        message = str(exc)
        if "Retry limit exceeded" in message or "Error 10061" in message or isinstance(exc, OperationalError):
            raise ECFCeleryUnavailable(
                "Celery/Redis no está disponible. Inicia Redis y el worker Celery antes de procesar e-CF."
            ) from exc
        raise
