import hashlib
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import close_old_connections, connection
from django.test import TransactionTestCase, override_settings
from django.utils import timezone
from lxml import etree
from rest_framework.test import APIRequestFactory, force_authenticate

from facturacion.api.views.dgii_certification import DGIICertificationPlanViewSet
from facturacion.ecf.exceptions import ECFValidationError
from facturacion.models import (
    Company,
    CompanyMembership,
    DGIICertificationDocument,
    DGIICertificationEvent,
    DGIICertificationItem,
    DGIICertificationPlan,
)
from facturacion.services.certification_locking import (
    CertificationArtifactChanged,
    CertificationMutationBlocked,
)
from facturacion.services.dgii_certification import (
    CertificationDocumentImmutableForSigning,
    CertificationPreparedSignature,
    CertificationResignAuthorizationError,
    CertificationSigningAttemptFailed,
    DGIICertificationDocumentSigner,
    DGIICertificationDocumentGenerator,
)


class CertificationSigningLockingTests(TransactionTestCase):
    def setUp(self):
        self.media_dir = tempfile.TemporaryDirectory()
        self.settings_override = override_settings(MEDIA_ROOT=self.media_dir.name)
        self.settings_override.enable()
        self.company = Company.objects.create(name='Firma Segura', rnc='101999001')
        self.plan = DGIICertificationPlan.objects.create(
            company=self.company, source_filename='signing.xlsx', file_sha256='9' * 64,
        )
        self.owner = get_user_model().objects.create_user('signing-owner')
        CompanyMembership.objects.create(
            user=self.owner, company=self.company, role=CompanyMembership.ROLE_OWNER,
        )

    def tearDown(self):
        self.settings_override.disable()
        self.media_dir.cleanup()

    def _item_document(self, encf='E310000000001', *, row=1, status='generated', outcome='not_started'):
        item = DGIICertificationItem.objects.create(
            plan=self.plan, company=self.company, ecf_type='31', dgii_group=1,
            encf=encf, source_sheet='ECF', source_row=row, status=status,
        )
        xml = f'<ECF><eNCF>{encf}</eNCF></ECF>'
        submission = {}
        if outcome == 'in_flight':
            submission = {'submission_started_at': timezone.now(), 'submission_fingerprint': 'f' * 64}
        document = DGIICertificationDocument.objects.create(
            plan=self.plan, company=self.company, item=item, ecf_type='31', encf=encf,
            status=status, submission_outcome=outcome, xml_content=xml,
            xml_hash=hashlib.sha256(xml.encode()).hexdigest(), generated_at=timezone.now(),
            **submission,
        )
        if status == 'signed':
            path = default_storage.save(f'tests/{encf}-old.xml', ContentFile(b'<signed-old/>'))
            document.signed_xml_path = path
            document.signed_xml_hash = hashlib.sha256(b'<signed-old/>').hexdigest()
            document.signed_at = timezone.now()
            document.save(update_fields=['signed_xml_path', 'signed_xml_hash', 'signed_at', 'updated_at'])
        return item, document

    def _signer(self, *, barrier=None, fail=False, mutate=None):
        signer = DGIICertificationDocumentSigner()

        def prepare(snapshot):
            if barrier:
                barrier.wait(timeout=10)
            if mutate:
                mutate(snapshot)
            if fail:
                raise ECFValidationError('controlled signing failure')
            content = f'<signed>{snapshot.encf}-{threading.get_ident()}</signed>'.encode()
            digest = hashlib.sha256(content).hexdigest()
            path = default_storage.save(
                signer._signed_filename_for(snapshot=snapshot, signed_xml_hash=digest),
                ContentFile(content),
            )
            return CertificationPreparedSignature(snapshot, path, digest, 'test', ())

        signer._prepare_signature = prepare
        return signer

    def test_suite_runs_against_postgresql(self):
        self.assertEqual(connection.vendor, 'postgresql')

    def test_initial_signing_publishes_versioned_immutable_path(self):
        item, document = self._item_document()
        result = self._signer().sign_item(item=item, user=self.owner)
        self.assertEqual(result.status, 'signed')
        self.assertIn(f'signed/{item.encf}/xml-{document.xml_hash[:16]}/attempt-', result.signed_xml_path)
        self.assertTrue(default_storage.exists(result.signed_xml_path))

    def test_sign_item_rejects_signed_document(self):
        item, document = self._item_document(status='signed')
        with self.assertRaises(CertificationDocumentImmutableForSigning):
            self._signer().sign_item(item=item, user=self.owner)
        document.refresh_from_db()
        self.assertTrue(default_storage.exists(document.signed_xml_path))

    def test_two_initial_signatures_only_one_is_published(self):
        item, _document = self._item_document()
        barrier = threading.Barrier(2)

        def worker():
            close_old_connections()
            try:
                return self._signer(barrier=barrier).sign_item(item=item, user=self.owner).signed_xml_path
            except CertificationArtifactChanged:
                return 'stale'
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = [future.result(timeout=20) for future in (pool.submit(worker), pool.submit(worker))]
        self.assertEqual(results.count('stale'), 1)
        document = DGIICertificationDocument.objects.get(item=item)
        self.assertTrue(default_storage.exists(document.signed_xml_path))

    def test_resign_requires_reason_and_authorized_membership(self):
        item, _document = self._item_document(status='signed')
        with self.assertRaises(ValueError):
            self._signer().resign_item(item=item, actor=self.owner, reason='')
        outsider = get_user_model().objects.create_user('outsider')
        with self.assertRaises(CertificationResignAuthorizationError):
            self._signer().resign_item(item=item, actor=outsider, reason='rotación')

    def test_resign_endpoint_requires_reason(self):
        item, _document = self._item_document(status='signed')
        request = APIRequestFactory().post(
            f'/ecf/certification-plans/{self.plan.pk}/items/{item.pk}/resign-document/',
            {}, format='json',
        )
        request.session = {'active_company_id': self.company.pk}
        force_authenticate(request, user=self.owner)
        response = DGIICertificationPlanViewSet.as_view({'post': 'resign_item_document'})(
            request, pk=self.plan.pk, item_id=item.pk,
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('obligatoria', response.data['detail'])

    def test_resign_endpoint_returns_409_for_blocking_outcome(self):
        item, document = self._item_document(status='signed')
        document.submission_outcome = 'confirmed'
        document.save(update_fields=['submission_outcome', 'updated_at'])
        request = APIRequestFactory().post(
            f'/ecf/certification-plans/{self.plan.pk}/items/{item.pk}/resign-document/',
            {'reason': 'rotación'}, format='json',
        )
        request.session = {'active_company_id': self.company.pk}
        force_authenticate(request, user=self.owner)
        response = DGIICertificationPlanViewSet.as_view({'post': 'resign_item_document'})(
            request, pk=self.plan.pk, item_id=item.pk,
        )
        self.assertEqual(response.status_code, 409)

    def test_resign_publishes_new_path_and_preserves_previous_file(self):
        item, document = self._item_document(status='signed')
        old_path = document.signed_xml_path
        result = self._signer().resign_item(item=item, actor=self.owner, reason='rotación controlada')
        self.assertNotEqual(result.signed_xml_path, old_path)
        self.assertTrue(default_storage.exists(old_path))
        self.assertTrue(default_storage.exists(result.signed_xml_path))

    def test_two_concurrent_resigns_only_one_wins(self):
        item, document = self._item_document(status='signed')
        old_path = document.signed_xml_path
        barrier = threading.Barrier(2)

        def worker():
            close_old_connections()
            try:
                return self._signer(barrier=barrier).resign_item(
                    item=item, actor=self.owner, reason='concurrente',
                ).signed_xml_path
            except CertificationArtifactChanged:
                return 'stale'
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = [future.result(timeout=20) for future in (pool.submit(worker), pool.submit(worker))]
        self.assertEqual(results.count('stale'), 1)
        self.assertTrue(default_storage.exists(old_path))

    def test_all_blocking_outcomes_reject_before_preparation(self):
        for index, outcome in enumerate(('in_flight', 'unknown', 'confirmed', 'manual_review'), start=1):
            with self.subTest(outcome=outcome):
                item, _document = self._item_document(f'E31{index:010d}', row=index, outcome=outcome)
                with self.assertRaises(CertificationMutationBlocked):
                    self._signer().sign_item(item=item, user=self.owner)

    def test_remote_evidence_rejects_inconsistent_generated_document(self):
        for index, field in enumerate(('dgii_track_id', 'submitted_at', 'accepted_at', 'rejected_at'), start=1):
            with self.subTest(field=field):
                item, document = self._item_document(f'E32{index:010d}', row=index)
                setattr(document, field, 'TRACK' if field == 'dgii_track_id' else timezone.now())
                document.save(update_fields=[field, 'updated_at'])
                with self.assertRaises(CertificationMutationBlocked):
                    self._signer().sign_item(item=item, user=self.owner)

    def test_xml_change_during_signing_is_fenced_and_new_file_cleaned(self):
        item, document = self._item_document()
        prepared_paths = []

        def mutate(snapshot):
            DGIICertificationDocument.objects.filter(pk=snapshot.document_id).update(
                xml_content='<changed/>', xml_hash='a' * 64,
            )

        signer = self._signer(mutate=mutate)
        original_cleanup = signer._cleanup_unpublished_path
        signer._cleanup_unpublished_path = lambda path: (prepared_paths.append(path), original_cleanup(path))[-1]
        with self.assertRaises(CertificationArtifactChanged):
            signer.sign_item(item=item, user=self.owner)
        self.assertEqual(len(prepared_paths), 1)
        self.assertFalse(default_storage.exists(prepared_paths[0]))
        document.refresh_from_db()
        self.assertEqual(document.status, 'generated')

    def test_signing_concurrent_with_regeneration_is_fenced(self):
        item, _document = self._item_document()
        signing_started = threading.Event()
        regeneration_done = threading.Event()
        signer = self._signer()
        base_prepare = signer._prepare_signature

        def delayed_prepare(snapshot):
            signing_started.set()
            regeneration_done.wait(timeout=10)
            return base_prepare(snapshot)

        signer._prepare_signature = delayed_prepare

        def signing_worker():
            close_old_connections()
            try:
                with self.assertRaises(CertificationArtifactChanged):
                    signer.sign_item(item=item, user=self.owner)
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(signing_worker)
            self.assertTrue(signing_started.wait(timeout=10))

            class Builder:
                @staticmethod
                def build(payload):
                    return etree.Element('ECF-regenerated')

            class Factory:
                @staticmethod
                def get(ecf_type):
                    return Builder()

            generator = DGIICertificationDocumentGenerator(builder_factory=Factory())
            generator._resolve_issuer = lambda company: object()
            generator._build_payload = lambda **kwargs: object()
            generator.generate_item(item=item)
            regeneration_done.set()
            future.result(timeout=20)
        document = DGIICertificationDocument.objects.get(item=item)
        self.assertEqual(document.status, 'generated')
        self.assertFalse(document.signed_xml_path)

    def test_signed_snapshot_change_during_resign_is_fenced(self):
        item, document = self._item_document(status='signed')
        old_path = document.signed_xml_path

        def mutate(snapshot):
            DGIICertificationDocument.objects.filter(pk=snapshot.document_id).update(signed_xml_hash='b' * 64)

        with self.assertRaises(CertificationArtifactChanged):
            self._signer(mutate=mutate).resign_item(item=item, actor=self.owner, reason='rotación')
        self.assertTrue(default_storage.exists(old_path))

    def test_storage_failure_does_not_mutate_database(self):
        item, document = self._item_document()
        before = (document.status, document.xml_content, document.xml_hash)
        with patch.object(default_storage, 'save', side_effect=OSError('storage unavailable')):
            with self.assertRaises(OSError):
                self._signer().sign_item(item=item, user=self.owner)
        document.refresh_from_db()
        self.assertEqual((document.status, document.xml_content, document.xml_hash), before)

    def test_database_failure_after_new_file_cleans_it_and_rolls_back(self):
        item, document = self._item_document()
        paths = []
        signer = self._signer()
        original_prepare = signer._prepare_signature

        def capture(snapshot):
            result = original_prepare(snapshot)
            paths.append(result.storage_path)
            return result

        signer._prepare_signature = capture
        with patch.object(DGIICertificationEvent.objects, 'create', side_effect=RuntimeError('event failure')):
            with self.assertRaises(RuntimeError):
                signer.sign_item(item=item, user=self.owner)
        document.refresh_from_db()
        self.assertEqual(document.status, 'generated')
        self.assertFalse(default_storage.exists(paths[0]))

    def test_initial_controlled_failure_preserves_generated_xml(self):
        item, document = self._item_document()
        before = (document.xml_content, document.xml_hash, document.generated_at)
        result = self._signer(fail=True).sign_item(item=item, user=self.owner)
        result.refresh_from_db()
        self.assertEqual(result.status, 'signing_error')
        self.assertEqual((result.xml_content, result.xml_hash, result.generated_at), before)

    def test_failed_resign_preserves_previous_signature_and_records_event(self):
        item, document = self._item_document(status='signed')
        before = (document.status, document.signed_xml_path, document.signed_xml_hash, document.signed_at)
        with self.assertRaises(CertificationSigningAttemptFailed):
            self._signer(fail=True).resign_item(item=item, actor=self.owner, reason='rotación')
        document.refresh_from_db()
        self.assertEqual((document.status, document.signed_xml_path, document.signed_xml_hash, document.signed_at), before)
        self.assertTrue(DGIICertificationEvent.objects.filter(item=item, event_type='document_signing_error').exists())

    def test_cleanup_never_deletes_current_path(self):
        _item, document = self._item_document(status='signed')
        self._signer()._cleanup_unpublished_path(document.signed_xml_path)
        self.assertTrue(default_storage.exists(document.signed_xml_path))

    def test_group_keeps_shape_and_publishes_valid_while_stale_fails(self):
        first, _ = self._item_document('E310000000001', row=1)
        second, second_document = self._item_document('E310000000002', row=2)
        calls = {'count': 0}

        def mutate(snapshot):
            calls['count'] += 1
            if snapshot.item_id == second.pk:
                DGIICertificationDocument.objects.filter(pk=second_document.pk).update(
                    xml_content='<stale/>', xml_hash='c' * 64,
                )

        summary = self._signer(mutate=mutate).sign_group(plan=self.plan, group_number=1, user=self.owner)
        self.assertEqual(set(summary), {'signed', 'failed', 'errors'})
        self.assertEqual(summary['signed'], 1)
        self.assertEqual(summary['failed'], 1)
        self.assertEqual(DGIICertificationDocument.objects.get(item=first).status, 'signed')
        self.assertEqual(DGIICertificationDocument.objects.get(item=second).status, 'generated')

    def test_individual_signing_concurrent_with_group_only_publishes_once(self):
        item, _document = self._item_document()
        barrier = threading.Barrier(2)

        def individual():
            close_old_connections()
            try:
                self._signer(barrier=barrier).sign_item(item=item, user=self.owner)
                return 'signed'
            except CertificationArtifactChanged:
                return 'stale'
            finally:
                close_old_connections()

        def group():
            close_old_connections()
            try:
                summary = self._signer(barrier=barrier).sign_group(
                    plan=self.plan, group_number=1, user=self.owner,
                )
                return 'signed' if summary['signed'] == 1 else 'stale'
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = [future.result(timeout=20) for future in (pool.submit(individual), pool.submit(group))]
        self.assertEqual(results.count('signed'), 1)
        self.assertEqual(results.count('stale'), 1)
        self.assertEqual(
            DGIICertificationEvent.objects.filter(item=item, event_type='document_signed').count(),
            1,
        )
