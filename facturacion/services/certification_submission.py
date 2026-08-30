"""Isolated, fenced preparation and delivery of one certification e-CF."""

from __future__ import annotations

import hashlib
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Callable

from django.core.files.storage import default_storage
from django.db import transaction
from django.utils import timezone

from facturacion.ecf.exceptions import ECFValidationError
from facturacion.ecf.rest.clients import DGIIRESTClient
from facturacion.ecf.rest.environments import DGIIRESTEnvironmentResolver
from facturacion.ecf.soap.parsers.dgii import DGIISOAPResponseParser
from facturacion.ecf.utils.fingerprint import submission_fingerprint
from facturacion.ecf.utils.text import digits_only
from facturacion.models import (
    DGIICertificationDocument,
    DGIICertificationEvent,
    DGIICertificationItem,
    DGIICertificationPlan,
)
from facturacion.services.certification_dependency_graph import (
    CertificationDependencyGraphPreflight,
    CertificationSignedArtifactSnapshot,
)
from facturacion.services.certification_locking import CertificationLockService
from facturacion.services.dgii_certification import (
    DGIICertificationDocumentGenerator,
    resolve_certificate_credentials,
)


class CertificationSubmissionError(Exception):
    pass


class CertificationSubmissionBlocked(CertificationSubmissionError):
    pass


class CertificationSubmissionUnknown(CertificationSubmissionError):
    pass


class CertificationSubmissionFencingConflict(CertificationSubmissionError):
    pass


@dataclass(frozen=True)
class CertificationRemoteSubmissionResponse:
    track_id: str
    status: str = "RECIBIDO"
    code: str = ""
    messages: tuple[str, ...] = ()
    raw: object = None


@dataclass(frozen=True)
class PreparedCertificationSubmission:
    document_id: int
    fingerprint: str
    snapshot: CertificationSignedArtifactSnapshot


class CertificationSubmissionService:
    def __init__(
        self,
        *,
        lock_service: CertificationLockService | None = None,
        preflight: CertificationDependencyGraphPreflight | None = None,
        remote_submitter: Callable | None = None,
    ):
        self.lock_service = lock_service or CertificationLockService()
        self.preflight = preflight or CertificationDependencyGraphPreflight(
            lock_service=self.lock_service
        )
        self.remote_submitter = remote_submitter

    def submit(
        self,
        *,
        plan_id: int,
        document_id: int,
        actor=None,
        environment: str | None = None,
    ) -> DGIICertificationDocument:
        snapshots = self._snapshot_plan(plan_id)
        prepared = self.prepare_certification_submission(
            plan_id=plan_id,
            document_id=document_id,
            snapshots=snapshots,
            actor=actor,
        )
        try:
            response = (
                self.remote_submitter(prepared)
                if self.remote_submitter
                else self._post_to_dgii(prepared, environment=environment)
            )
        except Exception as exc:
            self.mark_submission_unknown(
                prepared.document_id,
                prepared.fingerprint,
                str(exc),
                actor,
            )
            raise CertificationSubmissionUnknown(str(exc)) from exc
        return self.persist_submission_response(
            prepared.document_id,
            prepared.fingerprint,
            response,
            actor,
        )

    def prepare_certification_submission(
        self,
        *,
        plan_id: int,
        document_id: int,
        snapshots: dict[int, CertificationSignedArtifactSnapshot],
        actor=None,
    ) -> PreparedCertificationSubmission:
        with transaction.atomic():
            plan = self.lock_service.lock_plan(plan_id=plan_id)
            diagnostic = self.preflight.validate_locked_plan(
                plan,
                signed_artifact_snapshots=snapshots,
            )
            if not diagnostic.is_valid:
                reasons = ", ".join(
                    f"{issue.document_id}:{issue.kind.value}:{issue.reason}"
                    for issue in diagnostic.issues
                )
                raise CertificationSubmissionBlocked(f"Preflight inválido: {reasons}")

            snapshot = snapshots.get(document_id)
            if snapshot is None:
                raise CertificationSubmissionBlocked("El candidato no tiene snapshot firmado.")
            dependency_id = next(
                (
                    edge.original_document_id
                    for edge in diagnostic.edges
                    if edge.dependent_document_id == document_id
                ),
                None,
            )
            document_ids = [document_id] + ([dependency_id] if dependency_id else [])
            preliminary = {
                row["pk"]: row["item_id"]
                for row in DGIICertificationDocument.objects.filter(pk__in=document_ids).values(
                    "pk", "item_id"
                )
            }
            scope = self.lock_service.lock_scope(
                plan_id=plan.pk,
                item_ids=preliminary.values(),
                document_ids=document_ids,
            )
            document = scope.document(document_id)
            if dependency_id:
                original = scope.document(dependency_id)
                if (
                    original.status != DGIICertificationDocument.STATUS_ACCEPTED
                    or original.accepted_stale
                ):
                    raise CertificationSubmissionBlocked(
                        "El documento original interno aún no tiene aceptación vigente."
                    )
            self._assert_candidate_ready(document, snapshot)
            fingerprint = submission_fingerprint(
                issuer_rnc=snapshot.issuer_rnc,
                encf=document.encf,
                signed_xml=snapshot.signed_xml,
            )
            self.mark_in_flight(document, fingerprint, actor)
            return PreparedCertificationSubmission(document.pk, fingerprint, snapshot)

    def mark_in_flight(self, document, fingerprint, actor) -> None:
        if document.submission_outcome != DGIICertificationDocument.SUBMISSION_OUTCOME_NOT_STARTED:
            raise CertificationSubmissionBlocked("El documento ya tiene un intento de envío.")
        if document.dgii_track_id:
            raise CertificationSubmissionBlocked("El documento ya tiene TrackID.")
        now = timezone.now()
        document.submission_outcome = DGIICertificationDocument.SUBMISSION_OUTCOME_IN_FLIGHT
        document.submission_fingerprint = fingerprint
        document.submission_started_at = now
        document.reconciliation_attempts = 0
        document.next_retry_at = None
        document.reconciliation_lease_until = None
        document.reconciliation_lease_token = ""
        document.last_error = ""
        document.save(update_fields=[
            "submission_outcome", "submission_fingerprint", "submission_started_at",
            "reconciliation_attempts", "next_retry_at", "reconciliation_lease_until",
            "reconciliation_lease_token", "last_error", "updated_at",
        ])
        self._event(document, DGIICertificationEvent.EVENT_DOCUMENT_STATUS_CHECKED,
                    "Intención de envío DGII registrada.", actor,
                    {"stage": "certification_submission_prepare", "fingerprint": fingerprint})

    def persist_submission_response(self, document_id, fingerprint, response, actor):
        conflict_document = None
        with transaction.atomic():
            document = self._lock_single_document(document_id)
            if not self._fence_matches(document, fingerprint):
                conflict_document = document
            elif not response.track_id:
                raise CertificationSubmissionUnknown("DGII respondió sin TrackID.")
            else:
                now = timezone.now()
                document.submission_outcome = DGIICertificationDocument.SUBMISSION_OUTCOME_CONFIRMED
                document.status = DGIICertificationDocument.STATUS_SUBMITTED
                document.dgii_track_id = response.track_id
                document.dgii_status = response.status
                document.dgii_response_code = response.code
                document.dgii_response_message = "; ".join(response.messages)
                document.dgii_response = response.raw
                document.submitted_at = now
                document.last_error = ""
                document.save(update_fields=[
                    "submission_outcome", "status", "dgii_track_id", "dgii_status",
                    "dgii_response_code", "dgii_response_message", "dgii_response",
                    "submitted_at", "last_error", "updated_at",
                ])
                document.item.status = DGIICertificationItem.STATUS_SENT
                document.item.save(update_fields=["status", "updated_at"])
                self._event(document, DGIICertificationEvent.EVENT_DOCUMENT_SUBMITTED,
                            "Documento de certificación enviado a DGII.", actor,
                            {"stage": "certification_submission_confirmed", "fingerprint": fingerprint,
                             "track_id": response.track_id})
                return document
        self._fencing_event(conflict_document, fingerprint, "persist_response", actor)
        raise CertificationSubmissionFencingConflict("El intento cambió antes de persistir.")

    def mark_submission_unknown(self, document_id, fingerprint, error, actor) -> None:
        with transaction.atomic():
            document = self._lock_single_document(document_id)
            if not self._fence_matches(document, fingerprint):
                self._fencing_event(document, fingerprint, "mark_unknown", actor)
                return
            document.submission_outcome = DGIICertificationDocument.SUBMISSION_OUTCOME_UNKNOWN
            document.last_error = error
            document.next_retry_at = None
            document.save(update_fields=["submission_outcome", "last_error", "next_retry_at", "updated_at"])
            self._event(document, DGIICertificationEvent.EVENT_DOCUMENT_SUBMIT_ERROR,
                        "Resultado de envío DGII desconocido.", actor,
                        {"stage": "certification_submission_unknown", "fingerprint": fingerprint,
                         "error": error})

    def _snapshot_plan(self, plan_id):
        documents = DGIICertificationDocument.objects.filter(plan_id=plan_id).order_by("pk")
        return {document.pk: self._snapshot(document) for document in documents}

    def _snapshot(self, document):
        if not document.signed_xml_path or not default_storage.exists(document.signed_xml_path):
            return None
        with default_storage.open(document.signed_xml_path, "rb") as signed_file:
            content = signed_file.read()
        signed_xml = content.decode("utf-8")
        root = ET.fromstring(content)
        find = lambda tag: next(((node.text or "").strip() for node in root.iter()
                                 if node.tag.split("}")[-1] == tag), "")
        return CertificationSignedArtifactSnapshot(
            document_id=document.pk,
            signed_xml_path=document.signed_xml_path,
            sha256=hashlib.sha256(content).hexdigest(),
            signed_xml=signed_xml,
            modified_encf=find("NCFModificado"),
            other_taxpayer_rnc=find("RNCOtroContribuyente"),
            issuer_rnc=find("RNCEmisor"),
        )

    def _assert_candidate_ready(self, document, snapshot):
        if document.status != DGIICertificationDocument.STATUS_SIGNED:
            raise CertificationSubmissionBlocked("El candidato no está firmado.")
        if document.signed_xml_path != snapshot.signed_xml_path or document.signed_xml_hash != snapshot.sha256:
            raise CertificationSubmissionBlocked("El artefacto firmado del candidato cambió.")
        if digits_only(snapshot.issuer_rnc) != digits_only(document.company.rnc):
            raise CertificationSubmissionBlocked("RNCEmisor firmado no coincide con la empresa.")

    def _lock_single_document(self, document_id):
        identifiers = DGIICertificationDocument.objects.values("plan_id", "item_id").get(pk=document_id)
        plan = self.lock_service.lock_plan(plan_id=identifiers["plan_id"])
        scope = self.lock_service.lock_scope(
            plan_id=plan.pk,
            item_ids=[identifiers["item_id"]],
            document_ids=[document_id],
        )
        return scope.document(document_id)

    @staticmethod
    def _fence_matches(document, fingerprint):
        return (
            document.submission_outcome == DGIICertificationDocument.SUBMISSION_OUTCOME_IN_FLIGHT
            and document.submission_fingerprint == fingerprint
        )

    def _post_to_dgii(self, prepared, *, environment=None):
        document = DGIICertificationDocument.objects.select_related("plan__company").get(pk=prepared.document_id)
        issuer = DGIICertificationDocumentGenerator()._resolve_issuer(document.plan.company)
        certificate_path, certificate_password = resolve_certificate_credentials(issuer)
        config = DGIIRESTEnvironmentResolver().resolve(environment)
        client = DGIIRESTClient(environment=config)
        result = client.submit_ecf(
            signed_xml_content=prepared.snapshot.signed_xml,
            encf=document.encf,
            issuer_rnc=digits_only(prepared.snapshot.issuer_rnc),
            certificate_path=certificate_path,
            certificate_password=certificate_password,
            filename=f"{digits_only(prepared.snapshot.issuer_rnc)}{document.encf}.xml",
        )
        parsed = DGIISOAPResponseParser().parse_submission(result.result)
        return CertificationRemoteSubmissionResponse(
            track_id=parsed.track_id or "", status=parsed.status or "", code=str(parsed.code or ""),
            messages=tuple(parsed.messages), raw=parsed.raw,
        )

    def _fencing_event(self, document, fingerprint, stage, actor):
        self._event(document, DGIICertificationEvent.EVENT_DOCUMENT_SUBMIT_ERROR,
                    "Conflicto de fencing al persistir envío DGII.", actor,
                    {"stage": stage, "received_fingerprint": fingerprint,
                     "stored_fingerprint": document.submission_fingerprint,
                     "stored_outcome": document.submission_outcome})

    @staticmethod
    def _event(document, event_type, message, actor, payload):
        DGIICertificationEvent.objects.create(
            company=document.company, plan=document.plan, item=document.item,
            event_type=event_type, message=message, payload=payload, created_by=actor,
        )


def prepare_certification_submission(**kwargs):
    return CertificationSubmissionService().prepare_certification_submission(**kwargs)
