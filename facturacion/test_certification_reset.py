import hashlib
import tempfile
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import close_old_connections, connection, transaction
from django.test import TransactionTestCase, override_settings
from django.utils import timezone

from facturacion.models import (
    Company,
    CompanyMembership,
    DGIICertificationDocument,
    DGIICertificationEvent,
    DGIICertificationItem,
    DGIICertificationPlan,
)
from facturacion.services.certification_locking import (
    CertificationLockService,
    CertificationMutationBlocked,
)
from facturacion.services.certification_reset import (
    CertificationResetAuthorizationError,
    CertificationResetEvidenceRequired,
    CertificationResetService,
)
from facturacion.services.certification_submission import CertificationSubmissionService
from facturacion.services.dgii_certification import DGIICertificationDGIISubmitter
from facturacion.services.dgii_certification import (
    CertificationPreparedSignature,
    DGIICertificationDocumentGenerator,
    DGIICertificationDocumentSigner,
    DGIICertificationRFCERebuilder,
)


class CertificationResetSafetyTests(TransactionTestCase):
    def setUp(self):
        self.media_dir = tempfile.TemporaryDirectory()
        self.override = override_settings(MEDIA_ROOT=self.media_dir.name)
        self.override.enable()
        self.company = Company.objects.create(name='Reset seguro', rnc='101778899')
        self.plan = DGIICertificationPlan.objects.create(
            company=self.company, source_filename='reset.xlsx', file_sha256='a' * 64,
        )
        self.user = get_user_model().objects.create_user('reset-owner', password='x')
        CompanyMembership.objects.create(
            user=self.user, company=self.company, role=CompanyMembership.ROLE_OWNER,
        )

    def tearDown(self):
        self.override.disable()
        self.media_dir.cleanup()

    def _item(self, group, row):
        return DGIICertificationItem.objects.create(
            plan=self.plan, company=self.company, dgii_group=group, ecf_type='32',
            encf=f'E3200000000{group}{row:02d}', source_sheet='Reset', source_row=row,
            status=DGIICertificationItem.STATUS_ACCEPTED,
        )

    def _document(self, item, *, outcome='confirmed', status='accepted'):
        xml = f'<ECF><ENCF>{item.encf}</ENCF></ECF>'
        signed = f'<ECF><ENCF>{item.encf}</ENCF><Signature>ok</Signature></ECF>'.encode()
        path = default_storage.save(f'reset/{item.pk}.xml', ContentFile(signed))
        fields = {}
        if outcome in {'in_flight', 'unknown', 'claimed'}:
            marker = timezone.now()
            fields = {
                'submission_started_at': marker,
                'submission_fingerprint': 'f' * 64,
                'submission_attempt_token': uuid.uuid4(),
            }
            if outcome != 'claimed':
                fields['submission_dispatch_started_at'] = marker
        return DGIICertificationDocument.objects.create(
            plan=self.plan, company=self.company, item=item, ecf_type='32', encf=item.encf,
            status=status, xml_content=xml, xml_hash=hashlib.sha256(xml.encode()).hexdigest(),
            generated_at=timezone.now(), signed_xml_path=path,
            signed_xml_hash=hashlib.sha256(signed).hexdigest(), signed_at=timezone.now(),
            submission_outcome=outcome, dgii_track_id=f'TRACK-{item.pk}',
            dgii_status='Aceptado', dgii_response_code='0',
            dgii_response_message='Documento aceptado', dgii_response={'accepted': True},
            submitted_at=timezone.now(), accepted_at=timezone.now(),
            submission_fingerprint=fields.get('submission_fingerprint', 'b' * 64),
            submission_started_at=fields.get('submission_started_at', timezone.now()),
            submission_dispatch_started_at=fields.get('submission_dispatch_started_at'),
            submission_attempt_token=fields.get('submission_attempt_token'),
            reconciliation_attempts=2,
        )

    def _manual_reset(self, groups, **kwargs):
        return CertificationResetService().apply_reset(
            plan_id=self.plan.pk, groups=groups,
            source=CertificationResetService.SOURCE_MANUAL,
            reason=kwargs.pop('reason', 'Reset confirmado en portal DGII'),
            evidence=kwargs.pop('evidence', {'portal_reference': 'DGII-RESET-1'}),
            actor=kwargs.pop('actor', self.user), confirmed=kwargs.pop('confirmed', True),
            **kwargs,
        )

    def test_suite_runs_against_postgresql(self):
        self.assertEqual(connection.vendor, 'postgresql')

    def test_confirmed_authoritative_reset_opens_not_started_cycle_and_archives_history(self):
        item = self._item(3, 1)
        document = self._document(item)
        old_artifact = (document.xml_content, document.xml_hash, document.generated_at,
                        document.signed_xml_path, document.signed_xml_hash, document.signed_at)
        result = self._manual_reset((3,))
        document.refresh_from_db()
        item.refresh_from_db()
        self.assertEqual(result.applied, 1)
        self.assertEqual(document.submission_outcome, 'not_started')
        self.assertEqual(document.status, 'signed')
        self.assertTrue(document.accepted_stale)
        self.assertEqual(item.status, 'signed')
        self.assertEqual(
            (document.xml_content, document.xml_hash, document.generated_at,
             document.signed_xml_path, document.signed_xml_hash, document.signed_at),
            old_artifact,
        )
        event = DGIICertificationEvent.objects.get(event_type='dgii_reset_applied')
        previous = event.payload['previous']
        self.assertEqual(previous['dgii_track_id'], f'TRACK-{item.pk}')
        self.assertEqual(previous['submission_outcome'], 'confirmed')
        self.assertEqual(previous['submission_fingerprint'], 'b' * 64)
        self.assertEqual(previous['reconciliation_attempts'], 2)

    def test_blocked_outcomes_abort_entire_scope(self):
        for outcome in ('claimed', 'in_flight', 'unknown', 'manual_review'):
            with self.subTest(outcome=outcome):
                item = self._item(3, self.plan.items.count() + 1)
                document = self._document(item, outcome=outcome, status='signed')
                if outcome == 'manual_review':
                    document.next_retry_at = None
                    document.save(update_fields=['next_retry_at', 'updated_at'])
                with self.assertRaises(CertificationMutationBlocked):
                    self._manual_reset((3,), reset_key=f'{outcome:0<64}'[:64])
                document.refresh_from_db()
                self.assertEqual(document.submission_outcome, outcome)
                document.delete()
                item.delete()

    def test_claimed_reset_is_zero_change(self):
        item = self._item(3, 1)
        document = self._document(item, outcome='claimed', status='signed')
        before = (
            document.submission_outcome, document.submission_fingerprint,
            document.submission_attempt_token, document.submission_started_at,
            document.submission_dispatch_started_at, document.status,
        )

        with self.assertRaises(CertificationMutationBlocked):
            self._manual_reset((3,))

        document.refresh_from_db()
        self.assertEqual(
            (
                document.submission_outcome, document.submission_fingerprint,
                document.submission_attempt_token, document.submission_started_at,
                document.submission_dispatch_started_at, document.status,
            ),
            before,
        )

    def test_confirmed_modern_reset_clears_transport_fence(self):
        item = self._item(3, 1)
        document = self._document(item)
        attempt_token = uuid.uuid4()
        document.submission_attempt_token = attempt_token
        document.submission_dispatch_started_at = timezone.now()
        document.save(update_fields=[
            'submission_attempt_token', 'submission_dispatch_started_at', 'updated_at',
        ])

        self._manual_reset((3,))

        document.refresh_from_db()
        self.assertIsNone(document.submission_attempt_token)
        self.assertIsNone(document.submission_dispatch_started_at)
        event = DGIICertificationEvent.objects.get(event_type='dgii_reset_applied')
        self.assertEqual(
            event.payload['previous']['submission_attempt_token'],
            str(attempt_token),
        )

    def test_active_lease_blocks_reset(self):
        item = self._item(3, 1)
        document = self._document(item)
        document.reconciliation_lease_until = timezone.now()
        document.reconciliation_lease_token = 'lease-token'
        document.save(update_fields=['reconciliation_lease_until', 'reconciliation_lease_token', 'updated_at'])
        with self.assertRaises(CertificationMutationBlocked):
            self._manual_reset((3,))

    def test_confirmed_without_authoritative_source_is_blocked(self):
        self._document(self._item(3, 1))
        with self.assertRaises(CertificationResetEvidenceRequired):
            CertificationResetService().apply_reset(
                plan_id=self.plan.pk, groups=(3,), source='diagnostic',
                reason='stored text', evidence={'stored': True},
            )

    def test_not_started_without_history_is_safe_no_op(self):
        item = self._item(3, 1)
        document = self._document(item, outcome='not_started', status='signed')
        DGIICertificationDocument.objects.filter(pk=document.pk).update(
            dgii_track_id='', dgii_status='', dgii_response_code='',
            dgii_response_message='', dgii_response=None, submitted_at=None,
            accepted_at=None, submission_started_at=None, submission_fingerprint='',
            reconciliation_attempts=0,
        )
        result = self._manual_reset((3,))
        self.assertEqual(result.no_op, 1)
        self.assertEqual(result.applied, 0)
        self.assertFalse(DGIICertificationEvent.objects.exists())

    def test_reset_key_is_idempotent(self):
        self._document(self._item(3, 1))
        key = 'c' * 64
        first = self._manual_reset((3,), reset_key=key)
        second = self._manual_reset((3,), reset_key=key)
        self.assertEqual(first.applied, 1)
        self.assertEqual(second.idempotent, 1)
        self.assertEqual(DGIICertificationEvent.objects.filter(event_type='dgii_reset_applied').count(), 1)

    def test_groups_one_two_are_all_or_nothing(self):
        first = self._document(self._item(1, 1))
        blocked = self._document(self._item(2, 2), outcome='unknown', status='signed')
        with self.assertRaises(CertificationMutationBlocked):
            self._manual_reset((1, 2))
        first.refresh_from_db()
        blocked.refresh_from_db()
        self.assertEqual(first.submission_outcome, 'confirmed')
        self.assertEqual(blocked.submission_outcome, 'unknown')
        self.assertFalse(DGIICertificationEvent.objects.exists())

    def test_group_three_is_one_atomic_scope(self):
        documents = [self._document(self._item(3, row)) for row in (1, 2, 3, 4)]
        result = self._manual_reset((3,))
        self.assertEqual(result.applied, 4)
        self.assertEqual(DGIICertificationEvent.objects.filter(event_type='dgii_reset_applied').count(), 4)
        self.assertEqual(
            DGIICertificationDocument.objects.filter(pk__in=[d.pk for d in documents], submission_outcome='not_started').count(),
            4,
        )

    def test_event_failure_rolls_back_whole_scope(self):
        documents = [self._document(self._item(3, row)) for row in (1, 2)]
        with patch.object(DGIICertificationEvent.objects, 'create', side_effect=RuntimeError('event failure')):
            with self.assertRaises(RuntimeError):
                self._manual_reset((3,))
        self.assertEqual(
            DGIICertificationDocument.objects.filter(pk__in=[d.pk for d in documents], submission_outcome='confirmed').count(),
            2,
        )

    def test_failure_mid_transition_rolls_back_events_and_documents(self):
        documents = [self._document(self._item(3, row)) for row in (1, 2)]
        service = CertificationResetService()
        original = service._open_new_cycle
        calls = {'count': 0}

        def fail_second(**kwargs):
            calls['count'] += 1
            if calls['count'] == 2:
                raise RuntimeError('mid-scope failure')
            return original(**kwargs)

        with patch.object(service, '_open_new_cycle', side_effect=fail_second):
            with self.assertRaises(RuntimeError):
                service.apply_reset(
                    plan_id=self.plan.pk, groups=(3,), source='manual', reason='DGII reset',
                    evidence={'ref': 'X'}, actor=self.user, confirmed=True,
                )
        self.assertFalse(DGIICertificationEvent.objects.exists())
        self.assertEqual(
            DGIICertificationDocument.objects.filter(pk__in=[d.pk for d in documents], submission_outcome='confirmed').count(),
            2,
        )

    def test_sync_reset_state_is_diagnostic_and_does_not_mutate(self):
        document = self._document(self._item(3, 1))
        document.dgii_response_message = DGIICertificationDGIISubmitter.data_ecf_reset_phrase
        document.save(update_fields=['dgii_response_message', 'updated_at'])
        summary = DGIICertificationDGIISubmitter().sync_reset_state_from_stored_responses(plan=self.plan)
        document.refresh_from_db()
        self.assertGreater(summary['possible_resets'], 0)
        self.assertEqual(summary['total_marked'], 0)
        self.assertEqual(document.submission_outcome, 'confirmed')
        self.assertFalse(document.accepted_stale)

    def test_ambiguous_zero_marker_is_only_diagnostic(self):
        document = self._document(self._item(1, 1))
        submitter = DGIICertificationDGIISubmitter()
        self.assertTrue(submitter._response_indicates_data_ecf_reset('0/21'))
        self.assertFalse(submitter._response_is_authoritative_reset('0/21'))
        self.assertEqual(submitter._invalidate_data_ecf_if_reset_detected(
            trigger_document=document, user=self.user, message='0/21', response_payload={},
        ), 0)
        document.refresh_from_db()
        self.assertEqual(document.dgii_track_id, f'TRACK-{document.item_id}')

    def test_manual_reset_requires_authorization_reason_evidence_and_confirmation(self):
        self._document(self._item(3, 1))
        outsider = get_user_model().objects.create_user('outsider', password='x')
        with self.assertRaises(CertificationResetAuthorizationError):
            self._manual_reset((3,), actor=outsider)
        with self.assertRaises(CertificationResetEvidenceRequired):
            self._manual_reset((3,), reason='')
        with self.assertRaises(CertificationResetEvidenceRequired):
            self._manual_reset((3,), evidence=None)
        with self.assertRaises(CertificationResetEvidenceRequired):
            self._manual_reset((3,), confirmed=False)

    def test_legacy_pre_submission_reset_hook_is_non_destructive(self):
        document = self._document(self._item(1, 1))
        before = (document.status, document.dgii_track_id, document.dgii_response,
                  document.submission_outcome, document.submission_fingerprint)
        DGIICertificationDGIISubmitter()._reset_previous_dgii_results([document], self.user)
        document.refresh_from_db()
        self.assertEqual(
            (document.status, document.dgii_track_id, document.dgii_response,
             document.submission_outcome, document.submission_fingerprint),
            before,
        )

    def test_reset_and_submission_claim_are_serialized_by_plan_lock(self):
        item = self._item(3, 1)
        document = self._document(item)
        barrier = threading.Barrier(2)

        def reset_worker():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                try:
                    return self._manual_reset((3,), reset_key='d' * 64).applied
                except CertificationMutationBlocked:
                    return 'blocked'
            finally:
                close_old_connections()

        def claim_worker():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                try:
                    with transaction.atomic():
                        scope = CertificationLockService().lock_scope(
                            plan_id=self.plan.pk, item_ids=[item.pk], document_ids=[document.pk],
                        )
                        locked = scope.document(document.pk)
                        if locked.submission_outcome != 'not_started':
                            return 'blocked'
                        CertificationSubmissionService().mark_claimed(locked, 'e' * 64, self.user)
                        return 'claimed'
                except Exception:
                    return 'blocked'
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            reset_future = pool.submit(reset_worker)
            claim_future = pool.submit(claim_worker)
            results = {reset_future.result(timeout=20), claim_future.result(timeout=20)}
        document.refresh_from_db()
        if results == {'claimed', 1}:
            self.assertEqual(document.submission_outcome, 'claimed')
        self.assertIn(document.submission_outcome, {'confirmed', 'not_started', 'claimed'})

    def test_reset_competing_with_generation_preserves_signed_artifact(self):
        item = self._item(3, 1)
        document = self._document(item)
        old_path = document.signed_xml_path
        barrier = threading.Barrier(2)

        def reset_worker():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return self._manual_reset((3,), reset_key='1' * 64).applied
            finally:
                close_old_connections()

        def generation_worker():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                try:
                    DGIICertificationDocumentGenerator().generate_item(
                        item=DGIICertificationItem.objects.get(pk=item.pk),
                    )
                    return 'generated'
                except Exception:
                    return 'blocked'
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            reset_future = pool.submit(reset_worker)
            generation_future = pool.submit(generation_worker)
            self.assertEqual(reset_future.result(timeout=20), 1)
            self.assertEqual(generation_future.result(timeout=20), 'blocked')
        document.refresh_from_db()
        self.assertEqual(document.signed_xml_path, old_path)
        self.assertEqual(document.status, 'signed')

    def test_reset_competing_with_refirma_is_serialized_and_keeps_valid_blob(self):
        item = self._item(3, 1)
        document = self._document(item)
        signer = DGIICertificationDocumentSigner()

        def prepare(snapshot):
            content = b'<ECF><Signature>resigned</Signature></ECF>'
            digest = hashlib.sha256(content).hexdigest()
            path = default_storage.save(
                f'reset/resign-{threading.get_ident()}-{digest}.xml', ContentFile(content),
            )
            return CertificationPreparedSignature(snapshot, path, digest, 'test', ())

        signer._prepare_signature = prepare
        barrier = threading.Barrier(2)

        def reset_worker():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return self._manual_reset((3,), reset_key='2' * 64).applied
            finally:
                close_old_connections()

        def resign_worker():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                try:
                    signer.resign_item(
                        item=DGIICertificationItem.objects.get(pk=item.pk),
                        actor=self.user,
                        reason='Refirma concurrente controlada',
                    )
                    return 'resigned'
                except Exception:
                    return 'blocked'
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            reset_future = pool.submit(reset_worker)
            resign_future = pool.submit(resign_worker)
            self.assertEqual(reset_future.result(timeout=20), 1)
            self.assertIn(resign_future.result(timeout=20), {'resigned', 'blocked'})
        document.refresh_from_db()
        self.assertEqual(document.status, 'signed')
        self.assertTrue(default_storage.exists(document.signed_xml_path))

    def test_reset_competing_with_rfce_rebuild_is_serialized(self):
        rfce_item = self._item(3, 1)
        rfce_item.ecf_type = 'RFCE'
        rfce_item.save(update_fields=['ecf_type', 'updated_at'])
        rfce = self._document(rfce_item)
        rfce.ecf_type = 'RFCE'
        rfce.save(update_fields=['ecf_type', 'updated_at'])
        integral_item = self._item(4, 2)
        self._document(integral_item)
        barrier = threading.Barrier(2)

        def reset_worker():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return self._manual_reset((3,), reset_key='3' * 64).applied
            finally:
                close_old_connections()

        def rebuild_worker():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return DGIICertificationRFCERebuilder().rebuild(
                    plan=DGIICertificationPlan.objects.get(pk=self.plan.pk),
                )
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            reset_future = pool.submit(reset_worker)
            rebuild_future = pool.submit(rebuild_worker)
            self.assertEqual(reset_future.result(timeout=20), 1)
            self.assertTrue(rebuild_future.result(timeout=20)['failed'])
        rfce.refresh_from_db()
        self.assertEqual(rfce.submission_outcome, 'not_started')
        self.assertEqual(rfce.status, 'signed')
