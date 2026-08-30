"""Recover TrackIDs after uncertain DGII submissions without resending XML."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from facturacion.ecf.services.status_transitions import ECFStatusTransitionService
from facturacion.ecf.soap.auth import SettingsTokenProvider
from facturacion.ecf.soap.clients.dgii import DGIISOAPClient
from facturacion.ecf.soap.environments import DGIISOAPEnvironmentResolver
from facturacion.ecf.soap.parsers.dgii import DGIISOAPResponseParser
from facturacion.ecf.utils.text import digits_only
from facturacion.models import ECFEventLog, ElectronicFiscalDocument


@dataclass(frozen=True)
class DGIIReconciliationResult:
    document: ElectronicFiscalDocument
    outcome: str
    track_id: str | None = None


class DGIIReconciliationService:
    grace_period = timedelta(minutes=5)
    lease_period = timedelta(minutes=10)
    max_attempts = 5

    def __init__(self, environment_resolver=None, token_provider=None, parser=None, soap_client_class=DGIISOAPClient) -> None:
        self.environment_resolver = environment_resolver or DGIISOAPEnvironmentResolver()
        self.token_provider = token_provider or SettingsTokenProvider()
        self.parser = parser or DGIISOAPResponseParser()
        self.soap_client_class = soap_client_class
        self.status_transitions = ECFStatusTransitionService()

    def reconcile(self, document_id: int, environment: str | None = None, user=None):
        claim = self._claim(document_id, user=user)
        if claim is None:
            return None
        document, lease_token = claim
        try:
            environment_config = self.environment_resolver.resolve(environment)
            token = self.token_provider.get_token()
            client = self.soap_client_class(environment_config, token)
            response = client.query_trackids(
                issuer_rnc=digits_only(document.issuer.rnc) or document.issuer.rnc,
                encf=document.encf,
            )
            parsed = self.parser.parse_trackids(response.result)
        except Exception as exc:
            return self._record_ambiguous(document_id, lease_token, error=str(exc), user=user)

        # TrackIDs are not evidence for this document until DGII confirms RNC/e-NCF scope.
        if not self._response_matches_document(parsed, document):
            return self._record_ambiguous(
                document_id, lease_token,
                error="Respuesta TrackID DGII no asociada al RNC/e-NCF consultado.",
                user=user, parsed=parsed, response=response,
            )
        if len(parsed.track_ids) > 1:
            return self._record_multiple_track_ids(
                document_id, lease_token, parsed, response, environment_config.name, user=user,
            )
        if len(parsed.track_ids) == 1:
            return self._record_track_id(
                document_id, lease_token, parsed.track_ids[0], parsed, response, environment_config.name, user=user,
            )
        if parsed.is_not_found:
            return self._record_not_found(
                document_id, lease_token, parsed, response, environment_config.name, user=user,
            )
        return self._record_ambiguous(
            document_id, lease_token, error="Respuesta TrackID DGII ambigua.",
            user=user, parsed=parsed, response=response,
        )

    @transaction.atomic
    def _claim(self, document_id: int, user=None):
        document = ElectronicFiscalDocument.objects.select_for_update().select_related("issuer").get(pk=document_id)
        now = timezone.now()
        unknown_due = (
            document.submission_outcome == "unknown"
            and document.reconciliation_attempts < self.max_attempts
            and (document.next_retry_at is None or document.next_retry_at <= now)
        )
        in_flight_expired = (
            document.submission_outcome == "in_flight"
            and document.submission_started_at
            and document.submission_started_at <= now - self.grace_period
        )
        if not (unknown_due or in_flight_expired):
            return None
        if document.reconciliation_lease_until and document.reconciliation_lease_until > now:
            return None
        lease_token = uuid.uuid4().hex
        document.reconciliation_lease_until = now + self.lease_period
        document.reconciliation_lease_token = lease_token
        document.save(update_fields=["reconciliation_lease_until", "reconciliation_lease_token", "updated_at"])
        ECFEventLog.objects.create(
            electronic_document=document, event_type="queued",
            message="Documento reclamado para reconciliación de TrackID DGII.",
            payload={"stage": "dgii_reconciliation_claim", "submission_outcome": document.submission_outcome, "lease_token": lease_token},
            created_by=user,
        )
        return document, lease_token

    @transaction.atomic
    def _record_track_id(self, document_id, lease_token, track_id, parsed, response, environment_name, user=None):
        document = self._locked_claim(document_id, lease_token)
        if document is None:
            return None
        transition = self.status_transitions.transition(
            document, fiscal_status="submitted", source="dgii_reconciliation_track_id_recovered",
            reason="TrackID recuperado mediante consulta DGII por RNC y e-NCF.",
            extra_update_fields={
                "track_id": track_id, "submission_outcome": "confirmed",
                "dgii_request_xml": response.request_xml or document.dgii_request_xml,
                "dgii_response_xml": response.response_xml, "dgii_response": parsed.raw,
                "last_reconciled_at": timezone.now(), "reconciliation_lease_until": None,
                "reconciliation_lease_token": "", "last_error": None, "next_retry_at": None,
            },
        )
        document = transition.document
        ECFEventLog.objects.create(
            electronic_document=document, event_type="submitted",
            message="TrackID DGII recuperado durante reconciliación.",
            payload={"stage": "dgii_reconciliation_track_id_recovered", "environment": environment_name, "track_id": track_id, "submission_fingerprint": document.submission_fingerprint, "dgii_response": parsed.raw},
            created_by=user,
        )
        return DGIIReconciliationResult(document, "confirmed", track_id)

    @transaction.atomic
    def _record_not_found(self, document_id, lease_token, parsed, response, environment_name, user=None):
        document = self._locked_claim(document_id, lease_token)
        if document is None:
            return None
        now = timezone.now()
        ElectronicFiscalDocument.objects.filter(pk=document.pk).update(
            submission_outcome="not_started", submission_started_at=None,
            reconciliation_lease_until=None, reconciliation_lease_token="", last_reconciled_at=now,
            last_error="DGII no encontró TrackID para el e-NCF; reenvío manual habilitado.",
            next_retry_at=None, updated_at=now,
        )
        document.refresh_from_db()
        ECFEventLog.objects.create(
            electronic_document=document, event_type="status_checked",
            message="DGII no encontró TrackID; documento habilitado para reenvío manual.",
            payload={"stage": "dgii_reconciliation_not_found", "environment": environment_name, "submission_fingerprint": document.submission_fingerprint, "dgii_response": parsed.raw},
            created_by=user,
        )
        return DGIIReconciliationResult(document, "not_found")

    @transaction.atomic
    def _record_multiple_track_ids(self, document_id, lease_token, parsed, response, environment_name, user=None):
        document = self._locked_claim(document_id, lease_token)
        if document is None:
            return None
        now = timezone.now()
        ElectronicFiscalDocument.objects.filter(pk=document.pk).update(
            submission_outcome="manual_review", requires_manual_review=True,
            reconciliation_lease_until=None, reconciliation_lease_token="", last_reconciled_at=now,
            next_retry_at=None, last_error="DGII devolvió múltiples TrackID para el mismo RNC/e-NCF.",
            job_status="failed", updated_at=now,
        )
        document.refresh_from_db()
        ECFEventLog.objects.create(
            electronic_document=document, event_type="multiple_track_ids_detected",
            message="DGII devolvió múltiples TrackID para el mismo RNC/e-NCF.",
            payload={
                "stage": "dgii_reconciliation_multiple_track_ids", "track_ids": parsed.track_ids,
                "submission_fingerprint": document.submission_fingerprint, "environment": environment_name,
                "dgii_response": parsed.raw, "dgii_request_xml": response.request_xml,
                "dgii_response_xml": response.response_xml,
            }, created_by=user,
        )
        return DGIIReconciliationResult(document, "manual_review")

    @transaction.atomic
    def _record_ambiguous(self, document_id, lease_token, error, user=None, parsed=None, response=None):
        document = self._locked_claim(document_id, lease_token)
        if document is None:
            return None
        now = timezone.now()
        attempts = document.reconciliation_attempts + 1
        if attempts >= self.max_attempts:
            updates = {
                "submission_outcome": "manual_review", "requires_manual_review": True,
                "reconciliation_attempts": attempts, "reconciliation_lease_until": None,
                "reconciliation_lease_token": "", "last_reconciled_at": now, "next_retry_at": None,
                "last_error": error, "job_status": "failed", "updated_at": now,
            }
            event_type, message, outcome = "manual_review", "Reconciliación DGII agotada; requiere revisión manual.", "manual_review"
        else:
            retry_minutes = (1, 5, 15, 60, 240)[attempts - 1]
            updates = {
                "submission_outcome": "unknown", "reconciliation_attempts": attempts,
                "reconciliation_lease_until": None, "reconciliation_lease_token": "",
                "last_reconciled_at": now, "next_retry_at": now + timedelta(minutes=retry_minutes),
                "last_error": error, "updated_at": now,
            }
            event_type, message, outcome = "retry_scheduled", "Reconciliación DGII ambigua; se reintentará mediante Celery Beat.", "unknown"
        ElectronicFiscalDocument.objects.filter(pk=document.pk).update(**updates)
        document.refresh_from_db()
        ECFEventLog.objects.create(
            electronic_document=document, event_type=event_type, message=message,
            payload={
                "stage": "dgii_reconciliation_ambiguous", "submission_outcome": outcome,
                "reconciliation_attempts": attempts, "error": error,
                "dgii_response": parsed.raw if parsed else None,
                "dgii_request_xml": response.request_xml if response else None,
                "dgii_response_xml": response.response_xml if response else None,
            }, created_by=user,
        )
        return DGIIReconciliationResult(document, outcome)

    def _locked_claim(self, document_id, lease_token):
        document = ElectronicFiscalDocument.objects.select_for_update().get(pk=document_id)
        return document if document.reconciliation_lease_token == lease_token else None

    def _response_matches_document(self, parsed, document) -> bool:
        response_rnc = digits_only(parsed.rnc) if parsed.rnc else None
        response_encf = parsed.encf or None
        document_rnc = digits_only(document.issuer.rnc) or document.issuer.rnc
        return (response_rnc is None or response_rnc == document_rnc) and (response_encf is None or response_encf == document.encf)
