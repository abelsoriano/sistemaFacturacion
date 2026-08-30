"""Application service for submitting signed e-CF XML to DGII."""

from __future__ import annotations

import logging
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
from facturacion.ecf.utils.fingerprint import submission_fingerprint
from facturacion.ecf.state_machine import ECFStateMachine
from facturacion.ecf.services.status_transitions import ECFStatusTransitionService

logger = logging.getLogger(__name__)


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
        """Submit a signed e-CF through durable local delivery phases."""
        try:
            return self._submit(document, user, environment, force)
        except ECFError as exc:
            self._log_error(document, str(exc), user)
            raise

    def _submit(self, document: ElectronicFiscalDocument, user=None, environment: str | None = None, force: bool = False) -> DGIISubmissionResult:
        """Prepare durably, call DGII outside a DB transaction, then persist."""
        fingerprint = self._submission_fingerprint(document)
        prepared_document = self._prepare_submission(
            document,
            fingerprint,
            user=user,
            force=force,
        )

        if getattr(settings, "ECF_DGII_MOCK_ENABLED", False):
            return self._mock_submit(
                document_id=prepared_document.pk,
                fingerprint=fingerprint,
                user=user,
                environment=environment,
            )

        environment_config = self.environment_resolver.resolve(environment)
        token = self.token_provider.get_token()
        result = None
        parsed = None

        try:
            client = self.soap_client_class(environment_config, token)
            result = client.submit_ecf(
                signed_xml_content=prepared_document.signed_xml_content,
                encf=prepared_document.encf,
                issuer_rnc=digits_only(prepared_document.issuer.rnc) or prepared_document.issuer.rnc,
            )
            parsed = self.parser.parse_submission(result.result)
        except Exception as exc:
            self._mark_submission_unknown(
                document_id=prepared_document.pk,
                fingerprint=fingerprint,
                error=str(exc),
                user=user,
                request_xml=result.request_xml if result else None,
                response_xml=result.response_xml if result else None,
                response_data=parsed.raw if parsed else None,
            )
            if isinstance(exc, ECFError):
                raise
            raise ECFValidationError(
                "Resultado de envío DGII desconocido; se requiere reconciliación antes de reenviar."
            ) from exc

        if not parsed.track_id:
            self._persist_response_without_track_id(
                document_id=prepared_document.pk,
                fingerprint=fingerprint,
                error="DGII respondió sin TrackID para el envío e-CF.",
                user=user,
                request_xml=result.request_xml,
                response_xml=result.response_xml,
                response_data=parsed.raw,
            )
            raise ECFValidationError(
                "DGII respondió sin TrackID; el documento requiere revisión manual y no será reenviado."
            )

        return self._persist_confirmed_submission(
            document_id=prepared_document.pk,
            fingerprint=fingerprint,
            environment_name=environment_config.name,
            parsed=parsed,
            result=result,
            user=user,
        )

    @transaction.atomic
    def _prepare_submission(
        self,
        document: ElectronicFiscalDocument,
        fingerprint: str,
        *,
        user=None,
        force: bool = False,
    ) -> ElectronicFiscalDocument:
        locked_document = (
            ElectronicFiscalDocument.objects
            .select_for_update()
            .select_related("issuer")
            .get(pk=document.pk)
        )

        if not locked_document.signed_xml_content:
            raise ECFValidationError("El documento no tiene XML firmado para enviar a DGII.")
        self._assert_can_submit(locked_document, force=force)

        now = timezone.now()
        ElectronicFiscalDocument.objects.filter(pk=locked_document.pk).update(
            submission_outcome="in_flight",
            submission_fingerprint=fingerprint,
            submission_started_at=now,
            reconciliation_attempts=0,
            last_reconciled_at=None,
            last_error=None,
            next_retry_at=None,
            updated_at=now,
        )
        locked_document.refresh_from_db()

        ECFEventLog.objects.create(
            electronic_document=locked_document,
            event_type="queued",
            message="Intención de envío DGII registrada antes de invocar recepción SOAP.",
            payload={
                "stage": "dgii_submission_prepare",
                "submission_outcome": "in_flight",
                "submission_fingerprint": fingerprint,
                "submission_started_at": now.isoformat(),
            },
            created_by=user,
        )
        return locked_document

    def _persist_confirmed_submission(
        self,
        *,
        document_id: int,
        fingerprint: str,
        environment_name: str,
        parsed,
        result,
        user=None,
    ) -> DGIISubmissionResult:
        conflict_event = None
        with transaction.atomic():
            locked_document = (
                ElectronicFiscalDocument.objects
                .select_for_update()
                .select_related("issuer")
                .get(pk=document_id)
            )
            if (
                locked_document.submission_outcome != "in_flight"
                or locked_document.submission_fingerprint != fingerprint
            ):
                conflict_event = {
                    "document_id": locked_document.pk,
                    "payload": {
                        "stage": "dgii_submission_persist_confirmed_conflict",
                        "environment": environment_name,
                        "track_id": parsed.track_id,
                        "dgii_status": parsed.status,
                        "dgii_code": parsed.code,
                        "dgii_messages": parsed.messages,
                        "received_fingerprint": fingerprint,
                        "stored_fingerprint": locked_document.submission_fingerprint,
                        "stored_submission_outcome": locked_document.submission_outcome,
                        "stored_fiscal_status": locked_document.fiscal_status,
                        "stored_job_status": locked_document.job_status,
                        "dgii_response": parsed.raw,
                        "dgii_request_xml": result.request_xml,
                        "dgii_response_xml": result.response_xml,
                    },
                }
            else:
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
                        "submission_outcome": "confirmed",
                        "reconciliation_attempts": 0,
                        "last_reconciled_at": None,
                        "requires_manual_review": False,
                    },
                )
                locked_document = transition.document

                ECFEventLog.objects.create(
                    electronic_document=locked_document,
                    event_type="submitted",
                    message="XML firmado enviado a DGII.",
                    payload={
                        "environment": environment_name,
                        "track_id": parsed.track_id,
                        "status": parsed.status,
                        "code": parsed.code,
                        "messages": parsed.messages,
                        "submission_outcome": "confirmed",
                        "submission_fingerprint": fingerprint,
                    },
                    created_by=user,
                )
                return DGIISubmissionResult(
                    document=locked_document,
                    track_id=parsed.track_id,
                    status=locked_document.fiscal_status,
                )

        ECFEventLog.objects.create(
            electronic_document_id=conflict_event["document_id"],
            event_type="error",
            message=(
                "TrackID real recibido de DGII, pero no se persistió porque "
                "el intento local cambió durante la llamada remota."
            ),
            payload=conflict_event["payload"],
            created_by=user,
        )
        raise ECFValidationError(
            "TrackID DGII recibido, pero no pudo persistirse de forma segura; "
            "requiere recuperación manual."
        )

    @transaction.atomic
    def _mark_submission_unknown(
        self,
        *,
        document_id: int,
        fingerprint: str,
        error: str,
        user=None,
        request_xml: str | None = None,
        response_xml: str | None = None,
        response_data: dict | None = None,
    ) -> None:
        locked_document = ElectronicFiscalDocument.objects.select_for_update().get(pk=document_id)
        if locked_document.submission_fingerprint != fingerprint:
            logger.warning(
                "DGII uncertain submission update discarded due to fingerprint mismatch",
                extra={
                    "ecf": {
                        "document_id": document_id,
                        "stored_fingerprint": locked_document.submission_fingerprint,
                        "received_fingerprint": fingerprint,
                    }
                },
            )
            return
        if locked_document.submission_outcome == "confirmed":
            return

        now = timezone.now()
        update_fields = {
            "submission_outcome": "unknown",
            "last_error": error,
            "updated_at": now,
        }
        if request_xml:
            update_fields["dgii_request_xml"] = request_xml
        if response_xml:
            update_fields["dgii_response_xml"] = response_xml
        if response_data is not None:
            update_fields["dgii_response"] = response_data
        ElectronicFiscalDocument.objects.filter(pk=locked_document.pk).update(**update_fields)
        locked_document.refresh_from_db()

        ECFEventLog.objects.create(
            electronic_document=locked_document,
            event_type="error",
            message="Resultado de envío DGII desconocido; no se permite reenviar antes de reconciliar.",
            payload={
                "stage": "dgii_submission_remote_call",
                "submission_outcome": "unknown",
                "submission_fingerprint": fingerprint,
                "error": error,
            },
            created_by=user,
        )

    @transaction.atomic
    def _persist_response_without_track_id(
        self,
        *,
        document_id: int,
        fingerprint: str,
        error: str,
        user=None,
        request_xml: str | None = None,
        response_xml: str | None = None,
        response_data: dict | None = None,
    ) -> None:
        locked_document = ElectronicFiscalDocument.objects.select_for_update().get(pk=document_id)
        if locked_document.submission_fingerprint != fingerprint:
            logger.warning(
                "DGII response without TrackID discarded due to fingerprint mismatch",
                extra={"ecf": {"document_id": document_id}},
            )
            return

        now = timezone.now()
        update_fields = {
            "submission_outcome": "manual_review",
            "requires_manual_review": True,
            "last_error": error,
            "updated_at": now,
        }
        if request_xml:
            update_fields["dgii_request_xml"] = request_xml
        if response_xml:
            update_fields["dgii_response_xml"] = response_xml
        if response_data is not None:
            update_fields["dgii_response"] = response_data
        ElectronicFiscalDocument.objects.filter(pk=locked_document.pk).update(**update_fields)
        locked_document.refresh_from_db()

        ECFEventLog.objects.create(
            electronic_document=locked_document,
            event_type="manual_review",
            message="DGII respondió sin TrackID; no se hará reconciliación automática ni reenvío.",
            payload={
                "stage": "dgii_submission_response_without_track_id",
                "submission_outcome": "manual_review",
                "submission_fingerprint": fingerprint,
                "error": error,
                "dgii_response": response_data,
            },
            created_by=user,
        )

    def _assert_can_submit(self, document: ElectronicFiscalDocument, *, force: bool = False) -> None:
        # force se conserva por compatibilidad de API, pero nunca evita firma ni idempotencia.
        _ = force
        if document.fiscal_status in {"accepted", "rejected"}:
            raise ECFValidationError(f"No se puede reenviar un e-CF en estado {document.fiscal_status}.")
        if document.track_id or document.submission_outcome == "confirmed":
            raise ECFValidationError("El documento ya fue confirmado por DGII; no se puede reenviar.")
        if document.submission_outcome in {"in_flight", "unknown", "manual_review"}:
            raise ECFValidationError(
                "El resultado del último envío DGII no permite reenvío; primero debe reconciliarse."
            )
        if document.fiscal_status != "signed":
            raise ECFValidationError(f"El documento debe estar firmado antes de enviarse. Estado fiscal actual: {document.fiscal_status}.")

    def _submission_fingerprint(self, document: ElectronicFiscalDocument) -> str:
        return submission_fingerprint(
            issuer_rnc=document.issuer.rnc,
            encf=document.encf,
            signed_xml=document.signed_xml_content or "",
        )

    @transaction.atomic
    def _mock_submit(
        self,
        *,
        document_id: int,
        fingerprint: str,
        user=None,
        environment: str | None = None,
    ) -> DGIISubmissionResult:
        locked_document = ElectronicFiscalDocument.objects.select_for_update().get(pk=document_id)
        if (
            locked_document.submission_outcome != "in_flight"
            or locked_document.submission_fingerprint != fingerprint
        ):
            raise ECFValidationError(
                "El intento simulado DGII cambió mientras se esperaba la respuesta."
            )

        now = timezone.now()
        track_id = locked_document.track_id or f"MOCK-{locked_document.encf}-{locked_document.pk}"

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
                "submission_outcome": "confirmed",
                "reconciliation_attempts": 0,
                "last_reconciled_at": None,
                "requires_manual_review": False,
                "submission_fingerprint": fingerprint,
            },
        )
        locked_document = transition.document

        ECFEventLog.objects.create(
            electronic_document=locked_document,
            event_type="submitted",
            message="XML firmado enviado a DGII en modo simulado.",
            payload={
                "mock": True,
                "track_id": track_id,
                "status": "RECIBIDO",
                "submission_outcome": "confirmed",
                "submission_fingerprint": fingerprint,
            },
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
