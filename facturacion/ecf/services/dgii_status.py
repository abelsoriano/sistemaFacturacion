"""Application service for querying DGII e-CF status by TrackID."""

from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from facturacion.models import ECFEventLog, ElectronicFiscalDocument
from facturacion.ecf.exceptions import ECFError, ECFValidationError
from facturacion.ecf.soap.auth import SettingsTokenProvider
from facturacion.ecf.soap.clients.dgii import DGIISOAPClient
from facturacion.ecf.soap.environments import DGIISOAPEnvironmentResolver
from facturacion.ecf.soap.parsers.dgii import DGIISOAPResponseParser
from facturacion.ecf.state_machine import ECFStateMachine
from facturacion.ecf.services.job_reconciliation import ECFJobStatusReconciliationService
from facturacion.ecf.services.status_transitions import ECFStatusTransitionService
from facturacion.services.credit_note_reconciliation import CreditNoteReconciliationService


@dataclass(frozen=True)
class DGIIStatusCheckResult:
    """Result of querying DGII processing status."""

    document: ElectronicFiscalDocument
    status: str
    dgii_status: str


class DGIIStatusService:
    """Query DGII for an e-CF status and persist the response."""

    def __init__(
        self,
        environment_resolver: DGIISOAPEnvironmentResolver | None = None,
        token_provider: SettingsTokenProvider | None = None,
        parser: DGIISOAPResponseParser | None = None,
        soap_client_class= DGIISOAPClient,
    ) -> None:
        self.environment_resolver = environment_resolver or DGIISOAPEnvironmentResolver()
        self.token_provider = token_provider or SettingsTokenProvider()
        self.parser = parser or DGIISOAPResponseParser()
        self.soap_client_class = soap_client_class
        self.state_machine = ECFStateMachine()
        self.status_transitions = ECFStatusTransitionService()
        self.credit_note_reconciliation = CreditNoteReconciliationService()
        self.job_status_reconciliation = ECFJobStatusReconciliationService(self.status_transitions)

    def check(self, document: ElectronicFiscalDocument, user=None, environment: str | None = None) -> DGIIStatusCheckResult:
        """Query DGII by TrackID and update the local document status."""
        try:
            return self._check_atomic(document, user, environment)
        except ECFError as exc:
            self._log_error(document, str(exc), user)
            raise

    @transaction.atomic
    def _check_atomic(self, document: ElectronicFiscalDocument, user=None, environment: str | None = None) -> DGIIStatusCheckResult:
        locked_document = (
            ElectronicFiscalDocument.objects
            .select_for_update()
            .get(pk=document.pk)
        )

        if not locked_document.track_id:
            raise ECFValidationError("El documento no tiene TrackID para consultar estado.")

        self._prepare_for_status_check(locked_document, user)

        if getattr(settings, "ECF_DGII_MOCK_ENABLED", False):
            return self._mock_check(locked_document, user, environment)

        environment_config = self.environment_resolver.resolve(environment)
        token = self.token_provider.get_token()
        client = self.soap_client_class(environment_config, token)
        result = client.query_status(locked_document.track_id)
        parsed = self.parser.parse_status(result.result)
        now = timezone.now()
        target_fiscal_status = self._target_fiscal_status(parsed.normalized_status)
        extra_fields = {
            "dgii_request_xml": result.request_xml or locked_document.dgii_request_xml,
            "dgii_response_xml": result.response_xml,
            "dgii_response": parsed.raw,
            "last_status_checked_at": now,
        }
        if target_fiscal_status == "accepted":
            extra_fields["accepted_at"] = now
            extra_fields["rejection_reason"] = None
        elif target_fiscal_status == "rejected":
            extra_fields["rejection_reason"] = self._rejection_reason(parsed.messages)

        transition = self.status_transitions.transition(
            locked_document,
            fiscal_status=target_fiscal_status,
            source="dgii_status",
            reason=f"Estado DGII consultado: {parsed.status} ({parsed.normalized_status}).",
            extra_update_fields=extra_fields,
        )
        locked_document = transition.document
        self.credit_note_reconciliation.reconcile_after_dgii_status(locked_document, user=user)
        locked_document = self.job_status_reconciliation.reconcile_terminal_document(
            locked_document,
            user=user,
            source="dgii_status_terminal_job_reconciliation",
            reason="Consulta DGII dejo el documento en estado fiscal terminal.",
        ).document

        ECFEventLog.objects.create(
            electronic_document=locked_document,
            event_type="status_checked",
            message="Estado e-CF consultado en DGII.",
            payload={
                "environment": environment_config.name,
                "dgii_status": parsed.status,
                "normalized_status": parsed.normalized_status,
                "fiscal_status": locked_document.fiscal_status,
                "code": parsed.code,
                "messages": parsed.messages,
            },
            created_by=user,
        )

        return DGIIStatusCheckResult(
            document=locked_document,
            status=locked_document.fiscal_status,
            dgii_status=parsed.status,
        )

    def _prepare_for_status_check(self, locked_document: ElectronicFiscalDocument, user=None) -> None:
        """Reconcile local async state when DGII already assigned a TrackID."""
        if locked_document.fiscal_status == "submitted":
            return
        if locked_document.fiscal_status in {"accepted", "rejected"}:
            raise ECFValidationError(f"No se consulta DGII para documento terminal: {locked_document.fiscal_status}.")

        previous_status = locked_document.fiscal_status
        transition = self.status_transitions.transition(
            locked_document,
            fiscal_status="submitted",
            source="dgii_status_reconciliation",
            reason="Documento con TrackID reconciliado a estado fiscal submitted antes de consultar DGII.",
            extra_update_fields={"last_error": None, "next_retry_at": None},
            validate=False,
        )
        locked_document.fiscal_status = transition.document.fiscal_status
        locked_document.status = transition.document.status
        locked_document.last_error = transition.document.last_error
        locked_document.next_retry_at = transition.document.next_retry_at

        ECFEventLog.objects.create(
            electronic_document=locked_document,
            event_type="status_checked",
            message="Estado local e-CF reconciliado antes de consultar DGII.",
            payload={
                "previous_status": previous_status,
                "normalized_status": "submitted",
                "track_id": locked_document.track_id,
            },
            created_by=user,
        )

    def _rejection_reason(self, messages: list[dict]) -> str | None:
        values = [str(message.get("valor") or message.get("message") or message) for message in messages]
        return " | ".join(values) if values else None

    def _mock_check(self, locked_document: ElectronicFiscalDocument, user=None, environment: str | None = None) -> DGIIStatusCheckResult:
        now = timezone.now()
        transition = self.status_transitions.transition(
            locked_document,
            fiscal_status="accepted",
            source="dgii_status_mock",
            reason="Estado DGII simulado aceptado.",
            extra_update_fields={
                "dgii_response_xml": (
                    "<?xml version='1.0' encoding='UTF-8'?>"
                    f"<MockDGIIStatus><TrackID>{locked_document.track_id}</TrackID><Estado>ACEPTADO</Estado></MockDGIIStatus>"
                ),
                "dgii_response": {
                    "mock": True,
                    "environment": environment or getattr(settings, "ECF_DGII_ENVIRONMENT", "testing"),
                    "track_id": locked_document.track_id,
                    "status": "ACEPTADO",
                    "messages": ["Estado DGII simulado para desarrollo."],
                },
                "last_status_checked_at": now,
                "accepted_at": now,
                "rejection_reason": None,
            },
        )
        locked_document = transition.document
        self.credit_note_reconciliation.reconcile_after_dgii_status(locked_document, user=user)
        locked_document = self.job_status_reconciliation.reconcile_terminal_document(
            locked_document,
            user=user,
            source="dgii_status_mock_terminal_job_reconciliation",
            reason="Consulta DGII simulada dejo el documento en estado fiscal terminal.",
        ).document
        ECFEventLog.objects.create(
            electronic_document=locked_document,
            event_type="status_checked",
            message="Estado e-CF consultado en DGII en modo simulado.",
            payload={"mock": True, "dgii_status": "ACEPTADO", "normalized_status": "accepted", "fiscal_status": "accepted"},
            created_by=user,
        )
        return DGIIStatusCheckResult(document=locked_document, status="accepted", dgii_status="ACEPTADO")

    def _target_fiscal_status(self, normalized_status: str) -> str:
        if normalized_status in {"accepted", "rejected"}:
            return normalized_status
        return "submitted"

    def _log_error(self, document: ElectronicFiscalDocument, message: str, user=None) -> None:
        ECFEventLog.objects.create(
            electronic_document=document,
            event_type="error",
            message=f"Error consultando estado e-CF en DGII: {message}",
            payload={"stage": "dgii_status"},
            created_by=user,
        )
