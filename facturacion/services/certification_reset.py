"""Atomic, auditable reset of DGII certification transport cycles."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from facturacion.models import (
    CompanyMembership,
    DGIICertificationDocument,
    DGIICertificationEvent,
    DGIICertificationItem,
)
from facturacion.services.certification_locking import (
    CertificationLockService,
    CertificationMutationBlocked,
)


class CertificationResetError(Exception):
    """Base error for certification reset protocol failures."""


class CertificationResetAuthorizationError(CertificationResetError):
    """Raised when a manual reset lacks an authorized actor."""


class CertificationResetEvidenceRequired(CertificationResetError):
    """Raised when a reset is not backed by authoritative evidence."""


@dataclass(frozen=True)
class CertificationResetResult:
    reset_key: str
    groups: tuple[int, ...]
    applied: int = 0
    idempotent: int = 0
    no_op: int = 0

    def as_dict(self):
        return {
            'reset_key': self.reset_key,
            'groups': list(self.groups),
            'applied': self.applied,
            'idempotent': self.idempotent,
            'no_op': self.no_op,
        }


class CertificationResetService:
    EVENT_DGII_RESET_APPLIED = 'dgii_reset_applied'
    SOURCE_AUTOMATIC = 'automatic'
    SOURCE_MANUAL = 'manual'
    blocked_outcomes = {
        DGIICertificationDocument.SUBMISSION_OUTCOME_CLAIMED,
        DGIICertificationDocument.SUBMISSION_OUTCOME_IN_FLIGHT,
        DGIICertificationDocument.SUBMISSION_OUTCOME_UNKNOWN,
        DGIICertificationDocument.SUBMISSION_OUTCOME_MANUAL_REVIEW,
    }

    def __init__(self, *, lock_service=None):
        self.lock_service = lock_service or CertificationLockService()

    def apply_reset(
        self,
        *,
        plan_id: int,
        groups,
        source: str,
        reason: str,
        evidence,
        actor=None,
        confirmed: bool = False,
        reset_key: str | None = None,
    ) -> CertificationResetResult:
        normalized_groups = tuple(sorted({int(group) for group in groups}))
        if not normalized_groups:
            raise CertificationResetEvidenceRequired('El scope del reset no puede estar vacío.')
        reason = (reason or '').strip()
        if not reason:
            raise CertificationResetEvidenceRequired('La razón del reset es obligatoria.')
        evidence = json.loads(json.dumps(evidence, ensure_ascii=False, default=str))
        self._assert_source_authorized(
            source=source, actor=actor, confirmed=confirmed, evidence=evidence,
        )
        reset_key = reset_key or self.build_reset_key(
            plan_id=plan_id,
            groups=normalized_groups,
            source=source,
            reason=reason,
            evidence=evidence,
        )

        with transaction.atomic():
            plan = self.lock_service.lock_plan(plan_id=plan_id)
            if source == self.SOURCE_MANUAL and not self._actor_can_reset(actor, plan.company_id):
                raise CertificationResetAuthorizationError(
                    'Solo owner, admin o superusuario de la empresa puede aplicar un reset manual.'
                )
            item_ids = list(
                plan.items.filter(dgii_group__in=normalized_groups)
                .order_by('pk').values_list('pk', flat=True)
            )
            items = self.lock_service.lock_items(plan=plan, item_ids=item_ids)
            document_ids = list(
                DGIICertificationDocument.objects.filter(
                    plan=plan, company=plan.company, item_id__in=item_ids,
                ).order_by('pk').values_list('pk', flat=True)
            )
            documents = self.lock_service.lock_documents(
                plan=plan, document_ids=document_ids, locked_item_ids=item_ids,
            )
            item_by_id = {item.pk: item for item in items}
            documents = sorted(documents, key=lambda document: document.pk)
            self._validate_scope(documents=documents, source=source)

            history_documents = [document for document in documents if self._has_cycle_history(document)]
            existing_ids = set(
                DGIICertificationEvent.objects.filter(
                    plan=plan,
                    event_type=self.EVENT_DGII_RESET_APPLIED,
                    payload__reset_key=reset_key,
                ).values_list('item_id', flat=True)
            )
            scope_item_ids = {document.item_id for document in documents}
            if existing_ids:
                if not existing_ids.issubset(scope_item_ids):
                    raise CertificationMutationBlocked(
                        'El reset_key existente no coincide con el scope solicitado.'
                    )
                return CertificationResetResult(
                    reset_key=reset_key,
                    groups=normalized_groups,
                    idempotent=len(existing_ids),
                    no_op=len(documents) - len(existing_ids),
                )
            if not history_documents:
                return CertificationResetResult(
                    reset_key=reset_key,
                    groups=normalized_groups,
                    no_op=len(documents),
                )

            now = timezone.now()
            scope_payload = {
                'plan_id': plan.pk,
                'company_id': plan.company_id,
                'groups': list(normalized_groups),
                'document_ids': [document.pk for document in documents],
            }
            for document in history_documents:
                item = item_by_id[document.item_id]
                DGIICertificationEvent.objects.create(
                    company=plan.company,
                    plan=plan,
                    item=item,
                    event_type=self.EVENT_DGII_RESET_APPLIED,
                    message='Ciclo anterior archivado antes de aplicar reset DGII.',
                    payload={
                        'reset_key': reset_key,
                        'source': source,
                        'scope': scope_payload,
                        'actor_id': getattr(actor, 'pk', None),
                        'reason': reason,
                        'timestamp': now.isoformat(),
                        'document_id': document.pk,
                        'item_id': item.pk,
                        'previous': self._historical_snapshot(document=document, item=item),
                        'evidence': evidence,
                    },
                    created_by=actor if getattr(actor, 'is_authenticated', False) else None,
                )

            for document in history_documents:
                item = item_by_id[document.item_id]
                self._open_new_cycle(document=document, item=item, reason=reason, now=now)

            return CertificationResetResult(
                reset_key=reset_key,
                groups=normalized_groups,
                applied=len(history_documents),
                no_op=len(documents) - len(history_documents),
            )

    def _validate_scope(self, *, documents, source):
        for document in documents:
            if document.submission_outcome in self.blocked_outcomes:
                raise CertificationMutationBlocked(
                    f'{document.encf or document.pk}: submission_outcome='
                    f'{document.submission_outcome} bloquea reset.'
                )
            if document.reconciliation_lease_until or document.reconciliation_lease_token:
                raise CertificationMutationBlocked(
                    f'{document.encf or document.pk}: existe un lease de reconciliación activo.'
                )
            if (
                document.submission_outcome == DGIICertificationDocument.SUBMISSION_OUTCOME_CONFIRMED
                and source not in {self.SOURCE_AUTOMATIC, self.SOURCE_MANUAL}
            ):
                raise CertificationResetEvidenceRequired(
                    f'{document.encf or document.pk}: confirmed requiere reset autoritativo.'
                )
            if self._has_cycle_history(document) and not all((
                document.signed_xml_path, document.signed_xml_hash, document.signed_at,
            )):
                raise CertificationMutationBlocked(
                    f'{document.encf or document.pk}: no existe artefacto firmado íntegro para el nuevo ciclo.'
                )

    @classmethod
    def _assert_source_authorized(cls, *, source, actor, confirmed, evidence):
        if source == cls.SOURCE_AUTOMATIC:
            if not evidence:
                raise CertificationResetEvidenceRequired('El reset automático requiere respuesta DGII nueva.')
            return
        if source != cls.SOURCE_MANUAL:
            raise CertificationResetEvidenceRequired('Fuente de reset no autorizada.')
        if not confirmed:
            raise CertificationResetEvidenceRequired('El reset manual requiere confirmación explícita.')
        if not evidence:
            raise CertificationResetEvidenceRequired('El reset manual requiere referencia/evidencia DGII.')
    @staticmethod
    def _actor_can_reset(actor, company_id):
        if not actor or not getattr(actor, 'is_authenticated', False):
            return False
        if actor.is_superuser:
            return True
        return CompanyMembership.objects.filter(
            user=actor,
            company_id=company_id,
            is_active=True,
            role__in=(CompanyMembership.ROLE_OWNER, CompanyMembership.ROLE_ADMIN),
        ).exists()

    @staticmethod
    def _has_cycle_history(document):
        return bool(
            document.submission_outcome != DGIICertificationDocument.SUBMISSION_OUTCOME_NOT_STARTED
            or document.status in {
                DGIICertificationDocument.STATUS_SUBMITTED,
                DGIICertificationDocument.STATUS_ACCEPTED,
                DGIICertificationDocument.STATUS_REJECTED,
                DGIICertificationDocument.STATUS_SUBMIT_ERROR,
                DGIICertificationDocument.STATUS_SUBMIT_CONFLICT,
            }
            or document.dgii_track_id
            or document.dgii_status
            or document.dgii_response_code
            or document.dgii_response_message
            or document.dgii_response is not None
            or document.submitted_at
            or document.accepted_at
            or document.rejected_at
            or document.submit_error
            or document.submission_started_at
            or document.submission_fingerprint
            or document.reconciliation_attempts
            or document.next_retry_at
        )

    @staticmethod
    def _serialize(value):
        return value.isoformat() if hasattr(value, 'isoformat') else value

    def _historical_snapshot(self, *, document, item):
        fields = (
            'dgii_track_id', 'dgii_status', 'dgii_response_code',
            'dgii_response_message', 'dgii_response', 'submitted_at', 'accepted_at',
            'rejected_at', 'submit_error', 'submission_outcome', 'submission_started_at',
            'submission_fingerprint', 'submission_attempt_token',
            'submission_dispatch_started_at', 'reconciliation_attempts', 'next_retry_at',
            'reconciliation_lease_until', 'reconciliation_lease_token', 'status',
            'accepted_stale', 'stale_reason', 'stale_at',
        )
        snapshot = {field: self._serialize(getattr(document, field)) for field in fields}
        if snapshot['submission_attempt_token'] is not None:
            snapshot['submission_attempt_token'] = str(snapshot['submission_attempt_token'])
        snapshot['item_status'] = item.status
        return snapshot

    @staticmethod
    def _open_new_cycle(*, document, item, reason, now):
        document.status = DGIICertificationDocument.STATUS_SIGNED
        document.accepted_stale = True
        document.stale_reason = reason
        document.stale_at = now
        document.dgii_track_id = ''
        document.dgii_status = ''
        document.dgii_response_code = ''
        document.dgii_response_message = ''
        document.dgii_response = None
        document.submitted_at = None
        document.accepted_at = None
        document.rejected_at = None
        document.submit_error = ''
        document.submission_outcome = DGIICertificationDocument.SUBMISSION_OUTCOME_NOT_STARTED
        document.submission_started_at = None
        document.submission_fingerprint = ''
        document.submission_attempt_token = None
        document.submission_dispatch_started_at = None
        document.reconciliation_attempts = 0
        document.next_retry_at = None
        document.save(update_fields=[
            'status', 'accepted_stale', 'stale_reason', 'stale_at',
            'dgii_track_id', 'dgii_status', 'dgii_response_code',
            'dgii_response_message', 'dgii_response', 'submitted_at', 'accepted_at',
            'rejected_at', 'submit_error', 'submission_outcome',
            'submission_started_at', 'submission_fingerprint', 'submission_attempt_token',
            'submission_dispatch_started_at',
            'reconciliation_attempts', 'next_retry_at', 'updated_at',
        ])
        item.status = DGIICertificationItem.STATUS_SIGNED
        item.generation_error = ''
        item.save(update_fields=['status', 'generation_error', 'updated_at'])

    @staticmethod
    def build_reset_key(*, plan_id, groups, source, reason, evidence):
        canonical = json.dumps(
            {
                'plan_id': int(plan_id),
                'groups': list(sorted(int(group) for group in groups)),
                'source': source,
                'reason': reason,
                'evidence': evidence,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(',', ':'),
            default=str,
        )
        return hashlib.sha256(canonical.encode('utf-8')).hexdigest()
