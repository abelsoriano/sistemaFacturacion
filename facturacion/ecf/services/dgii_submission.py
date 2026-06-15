"""Application service for submitting signed e-CF XML to DGII."""

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
from facturacion.ecf.utils.text import digits_only
from facturacion.ecf.state_machine import ECFStateMachine
from facturacion.ecf.services.status_transitions import ECFStatusTransitionService


@dataclass(frozen=True)
class DGIISubmissionResult:
    """Result of submitting a signed e-CF XML to DGII."""

    document: ElectronicFiscalDocument
    track_id: str | None
    status: str


class DGIISubmissionService:
    """Submit signed e-CF XML to DGII and persist the full exchange."""

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

    def submit(self, document: ElectronicFiscalDocument, user=None, environment: str | None = None, force: bool = False) -> DGIISubmissionResult:
        """Submit a signed e-CF and update local tracking state."""
        try:
            return self._submit_atomic(document, user, environment, force)
        except ECFError as exc:
            self._log_error(document, str(exc), user)
            raise

    @transaction.atomic
    def _submit_atomic(self, document: ElectronicFiscalDocument, user=None, environment: str | None = None, force: bool = False) -> DGIISubmissionResult:
        locked_document = (
            ElectronicFiscalDocument.objects
            .select_for_update()
            .select_related("issuer")
            .get(pk=document.pk)
        )

        if not locked_document.signed_xml_content:
            raise ECFValidationError("El documento no tiene XML firmado para enviar a DGII.")
        self._assert_can_submit(locked_document, force=force)

        if getattr(settings, "ECF_DGII_MOCK_ENABLED", False):
            return self._mock_submit(locked_document, user, environment, force=force)

        environment_config = self.environment_resolver.resolve(environment)
        token = self.token_provider.get_token()
        client = self.soap_client_class(environment_config, token)
        result = client.submit_ecf(
            signed_xml_content=locked_document.signed_xml_content,
            encf=locked_document.encf,
            issuer_rnc=digits_only(locked_document.issuer.rnc) or locked_document.issuer.rnc,
        )
        parsed = self.parser.parse_submission(result.result)
        if not parsed.track_id:
            raise ECFValidationError("DGII no retorno TrackID para el envio e-CF.")

        transition = self.status_transitions.transition(
            locked_document,
            fiscal_status="submitted",
            source="dgii_submission",
            reason="XML firmado enviado a DGII y TrackID recibido.",
            extra_update_fields={
                "track_id": parsed.track_id,
                "dgii_request_xml": result.request_xml,
                "dgii_response_xml": result.response_xml,
                "dgii_response": parsed.raw,
                "last_submitted_at": timezone.now(),
                "last_error": None,
                "next_retry_at": None,
            },
        )
        locked_document = transition.document

        ECFEventLog.objects.create(
            electronic_document=locked_document,
            event_type="submitted",
            message="XML firmado enviado a DGII.",
            payload={
                "environment": environment_config.name,
                "track_id": parsed.track_id,
                "status": parsed.status,
                "code": parsed.code,
                "messages": parsed.messages,
            },
            created_by=user,
        )

        return DGIISubmissionResult(
            document=locked_document,
            track_id=parsed.track_id,
            status=locked_document.fiscal_status,
        )

    def _assert_can_submit(self, document: ElectronicFiscalDocument, *, force: bool = False) -> None:
        if document.fiscal_status in {"accepted", "rejected"}:
            raise ECFValidationError(f"No se puede reenviar un e-CF en estado {document.fiscal_status}.")
        if document.track_id and not force:
            raise ECFValidationError("El documento ya fue enviado a DGII. Usa force solo para reintentos controlados.")
        if document.fiscal_status != "signed" and not force:
            raise ECFValidationError(f"El documento debe estar firmado antes de enviarse. Estado fiscal actual: {document.fiscal_status}.")

    def _mock_submit(self, locked_document: ElectronicFiscalDocument, user=None, environment: str | None = None, force: bool = False) -> DGIISubmissionResult:
        now = timezone.now()
        track_id = locked_document.track_id or f"MOCK-{locked_document.encf}-{locked_document.pk}"
        self._assert_can_submit(locked_document, force=force)

        transition = self.status_transitions.transition(
            locked_document,
            fiscal_status="submitted",
            source="dgii_submission_mock",
            reason="XML firmado enviado a DGII en modo simulado.",
            extra_update_fields={
                "track_id": track_id,
                "dgii_request_xml": self._mock_request_xml(locked_document),
                "dgii_response_xml": self._mock_response_xml(track_id),
                "dgii_response": {
                    "mock": True,
                    "environment": environment or getattr(settings, "ECF_DGII_ENVIRONMENT", "testing"),
                    "track_id": track_id,
                    "status": "RECIBIDO",
                    "messages": ["Respuesta DGII simulada para desarrollo."],
                },
                "last_submitted_at": now,
                "last_error": None,
                "next_retry_at": None,
            },
        )
        locked_document = transition.document

        ECFEventLog.objects.create(
            electronic_document=locked_document,
            event_type="submitted",
            message="XML firmado enviado a DGII en modo simulado.",
            payload={"mock": True, "track_id": track_id, "status": "RECIBIDO"},
            created_by=user,
        )
        return DGIISubmissionResult(document=locked_document, track_id=track_id, status=locked_document.fiscal_status)

    def _mock_request_xml(self, document: ElectronicFiscalDocument) -> str:
        return (
            "<?xml version='1.0' encoding='UTF-8'?>"
            f"<MockDGIISubmission><eNCF>{document.encf}</eNCF>"
            f"<RNCEmisor>{document.issuer.rnc}</RNCEmisor></MockDGIISubmission>"
        )

    def _mock_response_xml(self, track_id: str) -> str:
        return (
            "<?xml version='1.0' encoding='UTF-8'?>"
            f"<MockDGIIResponse><TrackID>{track_id}</TrackID><Estado>RECIBIDO</Estado></MockDGIIResponse>"
        )

    def _log_error(self, document: ElectronicFiscalDocument, message: str, user=None) -> None:
        ECFEventLog.objects.create(
            electronic_document=document,
            event_type="error",
            message=f"Error enviando XML e-CF a DGII: {message}",
            payload={"stage": "dgii_submission"},
            created_by=user,
        )
