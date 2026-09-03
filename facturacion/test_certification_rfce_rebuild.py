import hashlib
import tempfile
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import close_old_connections, connection
from django.test import TransactionTestCase, override_settings
from django.utils import timezone
from lxml import etree

from facturacion.models import (
    Company,
    DGIICertificationDocument,
    DGIICertificationItem,
    DGIICertificationPlan,
)
from facturacion.services.certification_locking import CertificationArtifactChanged
from facturacion.services.dgii_certification import (
    CertificationPreparedSignature,
    CertificationPreparedArtifactPublisher,
    DGIICertificationDocumentGenerator,
    DGIICertificationDocumentSigner,
    DGIICertificationRFCERebuilder,
    PreparedCertificationSignature,
)


class CertificationRFCERebuildSafetyTests(TransactionTestCase):
    def setUp(self):
        self.media_dir = tempfile.TemporaryDirectory()
        self.override = override_settings(MEDIA_ROOT=self.media_dir.name)
        self.override.enable()
        self.company = Company.objects.create(name='RFCE Safe Rebuild', rnc='101998002')
        self.plan = DGIICertificationPlan.objects.create(
            company=self.company, source_filename='rfce.xlsx', file_sha256='9' * 64,
        )
        self.integral_item = self._item(4, '32', 1)
        self.rfce_item = self._item(3, 'RFCE', 2)

    def tearDown(self):
        self.override.disable()
        self.media_dir.cleanup()

    def _item(self, group, ecf_type, row):
        return DGIICertificationItem.objects.create(
            plan=self.plan, company=self.company, dgii_group=group, ecf_type=ecf_type,
            encf='E320000000011', source_sheet='RFCE', source_row=row,
            raw_data={'RNCEmisor': self.company.rnc, 'MontoTotal': '100.00'},
        )

    def _document(self, item, *, signed=False, outcome='not_started', track_id=''):
        xml = '<old/>'
        uncertain = outcome in {'in_flight', 'unknown', 'claimed'}
        marker = timezone.now() if uncertain else None
        document = DGIICertificationDocument.objects.create(
            plan=self.plan, company=self.company, item=item, ecf_type=item.ecf_type,
            encf=item.encf, status='signed' if signed else 'generated',
            xml_content=xml, xml_hash=hashlib.sha256(xml.encode()).hexdigest(),
            generated_at=timezone.now(), submission_outcome=outcome,
            dgii_track_id=track_id,
            submission_started_at=marker,
            submission_dispatch_started_at=marker if outcome != 'claimed' else None,
            submission_fingerprint='f' * 64 if uncertain else '',
            submission_attempt_token=uuid.uuid4() if uncertain else None,
        )
        if signed:
            content = self._signed_bytes('OLD123-signature')
            document.signed_xml_path = default_storage.save(
                f'old/{item.pk}.xml', ContentFile(content),
            )
            document.signed_xml_hash = hashlib.sha256(content).hexdigest()
            document.signed_at = timezone.now()
            document.save(update_fields=[
                'signed_xml_path', 'signed_xml_hash', 'signed_at', 'updated_at',
            ])
        return document

    @staticmethod
    def _signed_bytes(signature_value):
        return (
            '<ECF xmlns:ds="http://www.w3.org/2000/09/xmldsig#">'
            f'<ds:Signature><ds:SignatureValue>{signature_value}</ds:SignatureValue></ds:Signature>'
            '</ECF>'
        ).encode()

    def _generator(self):
        class Builder:
            @staticmethod
            def build(payload):
                return etree.Element('PreparedIntegral')

        class Factory:
            @staticmethod
            def get(ecf_type):
                return Builder()

        generator = DGIICertificationDocumentGenerator(builder_factory=Factory())
        generator._resolve_issuer = lambda company: object()
        generator._build_payload = lambda **kwargs: object()
        return generator

    def _signer(self, *, fail_rfce=False):
        outer = self

        class Signer:
            def prepare_document(self, *, prepared_document):
                if fail_rfce and prepared_document.item_snapshot.ecf_type == 'RFCE':
                    raise ValueError('controlled RFCE signing failure')
                value = 'NEWSIG-integral' if prepared_document.item_snapshot.dgii_group == 4 else 'RFCSIG-target'
                content = outer._signed_bytes(value)
                digest = hashlib.sha256(content).hexdigest()
                path = default_storage.save(
                    f'prepared/{threading.get_ident()}-{digest}.xml', ContentFile(content),
                )
                return PreparedCertificationSignature(
                    prepared_document, path, digest, 'test', (),
                )

        return Signer()

    def _rebuilder(self, **kwargs):
        return DGIICertificationRFCERebuilder(
            generator=self._generator(), signer=kwargs.pop('signer', self._signer()), **kwargs,
        )

    def test_suite_runs_against_postgresql(self):
        self.assertEqual(connection.vendor, 'postgresql')

    def test_initial_rebuild_publishes_integral_and_rfce(self):
        result = self._rebuilder().rebuild(plan=self.plan)
        self.assertFalse(result['failed'])
        self.assertEqual(result['signed_integral']['signed'], 1)
        self.assertEqual(result['signed_rfce']['signed'], 1)
        rfce = DGIICertificationDocument.objects.get(item=self.rfce_item)
        self.assertIn('<CodigoSeguridadeCF>NEWSIG</CodigoSeguridadeCF>', rfce.xml_content)

    def test_signed_mutable_artifacts_are_replaced_without_deleting_old_blobs(self):
        integral = self._document(self.integral_item, signed=True)
        rfce = self._document(self.rfce_item, signed=True)
        old_paths = (integral.signed_xml_path, rfce.signed_xml_path)
        result = self._rebuilder().rebuild(plan=self.plan)
        self.assertFalse(result['failed'])
        integral.refresh_from_db()
        rfce.refresh_from_db()
        self.assertNotIn(integral.signed_xml_path, old_paths)
        self.assertNotIn(rfce.signed_xml_path, old_paths)
        self.assertTrue(all(default_storage.exists(path) for path in old_paths))

    def test_integral_change_during_rfce_preparation_blocks_target(self):
        outer = self

        class MutatingPublisher(CertificationPreparedArtifactPublisher):
            def publish_document_and_signature(self, **kwargs):
                prepared = kwargs['prepared_document']
                if prepared.item_snapshot.dgii_group == 3:
                    dependency = prepared.dependency_fences[0]
                    DGIICertificationDocument.objects.filter(pk=dependency.document_id).update(
                        signed_xml_hash='a' * 64,
                    )
                return super().publish_document_and_signature(**kwargs)

        result = self._rebuilder(publisher=MutatingPublisher()).rebuild(plan=self.plan)
        self.assertTrue(result['failed'])
        self.assertFalse(DGIICertificationDocument.objects.filter(item=self.rfce_item).exists())

    def test_target_change_during_rfce_preparation_blocks_publication(self):
        target = self._document(self.rfce_item)

        class MutatingPublisher(CertificationPreparedArtifactPublisher):
            def publish_document_and_signature(self, **kwargs):
                prepared = kwargs['prepared_document']
                if prepared.item_snapshot.dgii_group == 3:
                    DGIICertificationDocument.objects.filter(pk=target.pk).update(xml_hash='b' * 64)
                return super().publish_document_and_signature(**kwargs)

        result = self._rebuilder(publisher=MutatingPublisher()).rebuild(plan=self.plan)
        self.assertTrue(result['failed'])
        target.refresh_from_db()
        self.assertEqual(target.status, 'generated')

    def test_blocking_outcomes_stop_before_any_publication(self):
        for outcome in ('claimed', 'in_flight', 'unknown', 'confirmed', 'manual_review'):
            with self.subTest(outcome=outcome):
                document = self._document(self.rfce_item, outcome=outcome)
                result = self._rebuilder().rebuild(plan=self.plan)
                self.assertTrue(result['failed'])
                self.assertFalse(DGIICertificationDocument.objects.filter(item=self.integral_item).exists())
                document.delete()

    def test_dgii_evidence_stops_before_any_publication_and_is_preserved(self):
        document = self._document(self.rfce_item, track_id='TRACK-KEEP')
        result = self._rebuilder().rebuild(plan=self.plan)
        self.assertTrue(result['failed'])
        document.refresh_from_db()
        self.assertEqual(document.dgii_track_id, 'TRACK-KEEP')
        self.assertEqual(document.submission_outcome, 'not_started')

    def test_group_three_failure_keeps_safe_group_four_publication(self):
        result = self._rebuilder(signer=self._signer(fail_rfce=True)).rebuild(plan=self.plan)
        self.assertTrue(result['failed'])
        self.assertEqual(result['signed_integral']['signed'], 1)
        self.assertEqual(result['signed_rfce']['failed'], 1)
        self.assertTrue(DGIICertificationDocument.objects.filter(item=self.integral_item, status='signed').exists())
        self.assertFalse(DGIICertificationDocument.objects.filter(item=self.rfce_item).exists())

    def test_response_shape_is_backward_compatible_and_never_marks_resubmit(self):
        result = self._rebuilder().rebuild(plan=self.plan)
        self.assertEqual(set(result), {
            'generated_integral', 'signed_integral', 'generated_rfce', 'signed_rfce',
            'source_documents', 'rfce_marked_for_resubmit', 'failed',
        })
        self.assertEqual(result['rfce_marked_for_resubmit'], 0)

    def test_two_concurrent_rebuilds_only_publish_one_coherent_cycle(self):
        barrier = threading.Barrier(2)

        def worker():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return self._rebuilder().rebuild(plan=DGIICertificationPlan.objects.get(pk=self.plan.pk))
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = [future.result(timeout=30) for future in (pool.submit(worker), pool.submit(worker))]
        self.assertGreaterEqual(sum(not result['failed'] for result in results), 1)
        self.assertEqual(DGIICertificationDocument.objects.filter(plan=self.plan).count(), 2)
        rfce = DGIICertificationDocument.objects.get(item=self.rfce_item)
        self.assertIn('<CodigoSeguridadeCF>NEWSIG</CodigoSeguridadeCF>', rfce.xml_content)

    def test_rebuild_competing_with_generation_cannot_overwrite_signed_result(self):
        self._document(self.integral_item, signed=True)
        barrier = threading.Barrier(2)

        def rebuild_worker():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return self._rebuilder().rebuild(
                    plan=DGIICertificationPlan.objects.get(pk=self.plan.pk),
                )
            finally:
                close_old_connections()

        def generation_worker():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                try:
                    self._generator().generate_item(
                        item=DGIICertificationItem.objects.get(pk=self.integral_item.pk),
                    )
                    return 'generated'
                except Exception:
                    return 'blocked'
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            rebuild_future = pool.submit(rebuild_worker)
            generation_future = pool.submit(generation_worker)
            rebuild_result = rebuild_future.result(timeout=30)
            generation_result = generation_future.result(timeout=30)
        self.assertEqual(generation_result, 'blocked')
        self.assertFalse(rebuild_result['failed'])
        self.assertEqual(DGIICertificationDocument.objects.get(item=self.integral_item).status, 'signed')

    def test_rebuild_competing_with_initial_signature_remains_fenced(self):
        document = self._document(self.integral_item)
        barrier = threading.Barrier(2)
        signer = DGIICertificationDocumentSigner()

        def prepare(snapshot):
            content = self._signed_bytes('RACESIG-signature')
            digest = hashlib.sha256(content).hexdigest()
            path = default_storage.save(
                f'prepared/race-{threading.get_ident()}-{digest}.xml', ContentFile(content),
            )
            return CertificationPreparedSignature(snapshot, path, digest, 'test', ())

        signer._prepare_signature = prepare

        def rebuild_worker():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return self._rebuilder().rebuild(
                    plan=DGIICertificationPlan.objects.get(pk=self.plan.pk),
                )
            finally:
                close_old_connections()

        def signing_worker():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                try:
                    signer.sign_item(item=DGIICertificationItem.objects.get(pk=self.integral_item.pk))
                    return 'signed'
                except Exception:
                    return 'fenced'
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            rebuild_future = pool.submit(rebuild_worker)
            signing_future = pool.submit(signing_worker)
            rebuild_result = rebuild_future.result(timeout=30)
            signing_result = signing_future.result(timeout=30)
        self.assertIn(signing_result, {'signed', 'fenced'})
        # Either contender may win. A fenced rebuild is safe when the independent
        # initial signature publishes first; the invariant is the final artifact.
        if rebuild_result['failed']:
            self.assertEqual(signing_result, 'signed')
        document.refresh_from_db()
        self.assertEqual(document.status, 'signed')
        self.assertTrue(default_storage.exists(document.signed_xml_path))

    def test_legacy_resubmit_hook_never_clears_fiscal_evidence(self):
        document = self._document(self.rfce_item, outcome='unknown', track_id='TRACK-KEEP')
        document.submitted_at = timezone.now()
        document.dgii_response = {'raw': 'keep'}
        document.save(update_fields=['submitted_at', 'dgii_response', 'updated_at'])
        updated = self._rebuilder()._mark_rfce_for_resubmit(self.plan, None)
        document.refresh_from_db()
        self.assertEqual(updated, 0)
        self.assertEqual(document.dgii_track_id, 'TRACK-KEEP')
        self.assertIsNotNone(document.submitted_at)
        self.assertEqual(document.dgii_response, {'raw': 'keep'})
